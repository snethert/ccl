"""Attach qualified resident execution bodies without importing caller bounds.

Each bridge compares the anchored old code with a newly compiled LFUN. All
computed calls in the borrowed IR remain open: a different caller or closure
environment never inherits the new compilation's argument-flow conclusions.
"""
from collections import Counter,defaultdict,deque
from pathlib import Path
import gzip
import json
import re
import sys
from payloads import rows,require,read,save

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'build-flow'))
from flow import convert,functions

PREFIX='correlated-build:'
QUAL=PREFIX+'qualification'
HEADER=re.compile(rb'^\{\s*(?:"version"\s*:\s*\d+\s*,\s*)?"sequence"\s*:\s*(\d+)\s*,')


def selected_rows(path,events):
    # The complete stream/mapping was checked when producing MATCHES. Decode
    # only its selected IR records here, instead of parsing a gigabyte again.
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rb') as src:
        for line in src:
            header=HEADER.match(line);require(header is not None,'BODY_STREAM_HEADER')
            if int(header[1]) in events:yield json.loads(line)


def node(ident,evidence,reason,unresolved=False):
    return dict(id=ident,kind='function',required=True,
        disposition='unresolved' if unresolved else 'implemented',
        implementation=None if unresolved else 'Observed native execution-body dependency',
        reason=reason,evidence=evidence,tests=['S0-LL15-b','S0-LL15-c'])


def edge(owner,targets,evidence,phase='run',complete=True):
    return {'from':owner,'targets':sorted(set(targets)),'origin':'conservative','phase':phase,
            'resolution':'complete' if complete else 'unresolved','evidence':evidence}


def extract(build,matches,operators):
    events={e['before']['event'] for m in matches for e in m['compiler_records']}
    families=[];seen=set();calls=[]
    for row in selected_rows(build,events):
        require(row['kind']=='before-pass2' and row['sequence'] not in seen,'BODY_IR_EVENT')
        seen.add(row['sequence']);cap=convert(row['payload'],operators)
        from analysis import Graph
        graph=Graph(cap['flow']);raw={n['id']:n for n in row['payload']['ir']['objects']}
        for fn in functions(cap['function']):
            families.append(dict(function=fn['function_id'],parent=fn['parent_id'],event=row['sequence'],name=fn['name']))
            for c in fn['calls']:
                result=dict(function=fn['function_id'],site=c['site_id'],event=row['sequence'],dependency=c['dependency'])
                if c['dependency']['category']=='global-binding':
                    callee=graph.node(graph.items(graph.nodes[c['site_id']]['operands'])[0]);visited=set()
                    while callee and callee.get('operator') in ('CCL::TYPED-FORM','CCL::TYPE-ASSERTED-FORM'):
                        require(callee['id'] not in visited,'BODY_CALLEE_CYCLE');visited.add(callee['id'])
                        callee=graph.node(graph.items(callee['operands'])[1])
                    require(callee and callee['operator'] in ('CCL::IMMEDIATE','CCL::%FUNCTION'),'BODY_GLOBAL_OPERATOR')
                    value=graph.items(callee['operands'])[0]
                    require(isinstance(value,dict) and 'identity' in value,'BODY_GLOBAL_SYMBOL')
                    symbol=raw[value['identity']];require(symbol['kind']=='symbol','BODY_GLOBAL_IDENTITY')
                    result['symbol']=symbol
                calls.append(result)
    require(seen==events,'BODY_IR_COVERAGE')
    require(len({f['function'] for f in families})==len(families),'BODY_FAMILY_DUPLICATE')
    return families,calls


def with_initializers(matches,deferred):
    selected=list(matches);events={e['before']['event'] for m in selected for e in m['compiler_records']}
    records={};changed=True
    while changed:
        changed=False
        for r in deferred:
            if r['event'] not in events:continue
            for e in r['compiler_records']:
                key=(e['afunc'],e['event'])
                if key not in records:
                    records[key]=e;changed=True;events.add(e['before']['event'])
    if records:selected.append(dict(compiler_records=list(records.values())))
    return selected


def needed_matches(matches,support_matches=()):
    all_matches={m['bootstrap_code']:m for m in [*matches,*support_matches]}
    require(len(all_matches)==len(matches)+len(support_matches),'BODY_MATCH_POPULATION')
    needed={m['bootstrap_code'] for m in matches};pending=deque(needed)
    while pending:
        for d in all_matches[pending.popleft()].get('function_literal_correspondences',[]):
            target=d['bootstrap_function']
            if target in all_matches and target not in needed:needed.add(target);pending.append(target)
    return [all_matches[i] for i in sorted(needed)]


def make(base,matches,families,calls,support_matches=(),deferred=(),
         namespace=PREFIX,anchor_prefix='identity:build:code:',anchor_evidence='binding-versions/body/',references=()):
    PREFIX=namespace;QUAL=namespace+'qualification'
    old={n['id'] for n in base['nodes']};ns={};es=[];replace={};roots=set();afuncs={f['function'] for f in families}
    root_codes={m['bootstrap_code'] for m in matches}
    qualified=needed_matches(matches,support_matches);by_code={m['bootstrap_code']:m for m in qualified}
    deferred_index={(r['event'],r['object']):r for r in deferred}
    require(len(deferred_index)==len(deferred),'DEFERRED_DUPLICATE_OBSERVATION')
    def add(n):
        require(n['id'] not in old and (n['id'] not in ns or ns[n['id']]==n),'BODY_NODE_CONFLICT');ns[n['id']]=n
    def afunc(i):return PREFIX+'afunc:'+str(i)
    def literal_code(i):return PREFIX+'literal-code:'+str(i)
    add(node(QUAL,'correlated-build/scope',
        'Native code/body correspondence only. Target lowering, metadata materialization, binding-value coverage and caller environments remain separate obligations.',True))
    for f in families:
        ident=afunc(f['function']);add(node(ident,f'correlated-build/ir/{f["event"]}/{f["function"]}',
            'Actual pass-2 input. Its incoming arguments and enclosing environment have no borrowed bounds.'))
        es.append(edge(ident,[QUAL],f'correlated-build/qualification/{f["function"]}','compile'))
    for r in deferred:
        owners=set(r['owners'])&afuncs
        if not owners:continue
        require(r['result_status']==r['effects_status']=='UNRESOLVED','DEFERRED_RESULT_PROMOTION')
        targets={e['afunc'] for e in r['compiler_records']}
        require(targets and targets<=afuncs,'DEFERRED_INITIALIZER_BODY_MISSING')
        ident=PREFIX+f'deferred:{r["event"]}:{r["object"]}'
        add(node(ident,f'correlated-build/deferred/{r["event"]}/{r["object"]}',
            'Recorded load-time initializer function; its result, effects and target materialization remain unresolved.',True))
        es.append(edge(ident,[afunc(i) for i in targets],f'correlated-build/deferred-body/{r["event"]}/{r["object"]}','load'))
        for owner in owners:
            es.append(edge(afunc(owner),[ident],f'correlated-build/deferred-use/{owner}/{r["object"]}','load'))
    for m in qualified:
        require(not m.get('candidate_only'),'UNQUALIFIED_BODY_CANDIDATES')
        code=m['bootstrap_code'];source=anchor_prefix+str(code)
        require((source in old or code not in root_codes) and m['metadata_disposition']=='UNRESOLVED','BODY_ANCHOR')
        target={e['afunc'] for e in m['compiler_records']};require(target and target<=afuncs,'BODY_MATCH_AFUNCS')
        if code in root_codes:roots.update(afunc(i) for i in target)
        for data in m.get('data_dependencies',[]):
            require(data['disposition']=='UNRESOLVED' and data['callable'] is False,
                    'BODY_DATA_DISPOSITION')
            for candidate,records in data.get('deferred_initializers',{}).items():
                owners={e['afunc'] for e in m['compiler_records'] if e['function']==int(candidate)}
                require(records and owners,'BODY_DEFERRED_CANDIDATE')
                for record in records:
                    require(deferred_index.get((record['event'],record['object']))==record
                            and owners & set(record['owners']),'BODY_DEFERRED_WITNESS_MISSING')
            ident=PREFIX+f'data:{code}:{data["index"]}'
            add(node(ident,f'correlated-build/data/{code}/{data["index"]}',
                'Noncallable constant contents/identity are not transferred from the new compilation. Materialization and operations reading this data remain obligations.',True))
            for i in target:es.append(edge(afunc(i),[ident],f'correlated-build/body-data/{code}/{data["index"]}/{i}','compile'))
        if code in root_codes:
            evidence=anchor_evidence+str(code)
            require(evidence not in replace,'BODY_MATCH_DUPLICATE')
            replace[evidence]=edge(source,[afunc(i) for i in target],evidence,'compile')
        for d in m.get('function_literal_correspondences',[]):
            actual=d['bootstrap_function'];compiled=d['compiled_function'];ident=literal_code(actual)
            require(d['environment_identity'] is False,'BORROWED_LITERAL_ENVIRONMENT')
            if d['relation']=='EXACT_LITERAL_IDENTITY':
                require(actual==compiled and d['function_identity'] is True,'LITERAL_IDENTITY')
            else:
                require(d['relation']=='QUALIFIED_EXECUTION_BODY' and d['function_identity'] is False
                        and actual in by_code and compiled in by_code[actual]['compiled_functions'],
                        'LITERAL_BODY_PAIR')
            if ident not in ns:
                add(node(ident,f'correlated-build/function-literal/{actual}',
                    'Actual function constant. Any body correspondence preserves no caller or enclosing-environment bounds.',
                    actual not in by_code))
                if actual in by_code:
                    ts={afunc(e['afunc']) for e in by_code[actual]['compiler_records']}
                    es.append(edge(ident,ts,f'correlated-build/literal-body/{actual}','compile'))
                else:es.append(edge(ident,[],f'correlated-build/literal-body/{actual}','compile',False))
            owners={e['afunc'] for e in m['compiler_records'] if e['function']==d['compiled_owner']}
            require(owners,'LITERAL_COMPILED_OWNER')
            for i in owners:
                es.append(edge(afunc(i),[ident],f'correlated-build/literal/{code}/{d["index"]}/{i}','compile'))
    for c in calls:
        owner=afunc(c['function']);d=c['dependency'];targets=[];complete=False
        if d['targets'] and all(t['kind']=='function' for t in d['targets']):
            require(all(t['id'] in afuncs for t in d['targets']),'BODY_LEXICAL_TARGET')
            targets=[afunc(t['id']) for t in d['targets']];complete=True
        elif d['category']=='global-binding':
            s=c['symbol'];ident=PREFIX+'binding:'+str(s['id']);targets=[ident];complete=True
            if ident not in ns:
                add(node(ident,'correlated-build/binding/'+str(s['id']),
                    'Exact symbol cell in the correlated execution; its runtime callable values remain unbounded.',True))
                es.append(edge(ident,[],f'correlated-build/binding-values/{s["id"]}',complete=False))
        elif d['category']=='builtin':
            ident=PREFIX+'builtin:'+str(d['builtin_index']);targets=[ident];complete=True
            if ident not in ns:
                add(node(ident,'correlated-build/builtin/'+str(d['builtin_index']),
                    'Observed native builtin slot; target lowering is still required.',True))
                es.append(edge(ident,[],f'correlated-build/builtin-lowering/{d["builtin_index"]}',complete=False))
        es.append(edge(owner,targets,f'correlated-build/call/{c["function"]}/{c["site"]}',complete=complete))
    for ref in references:
        owner=afunc(ref['function']);require(ref['function'] in afuncs,'BODY_VALUE_OWNER')
        if ref['kind']=='lexical':
            require(ref['target'] in afuncs and ref['environment_bound'] is False,'BODY_VALUE_LEXICAL')
            target=afunc(ref['target'])
        else:
            require(ref['kind']=='symbol' and ref['value_time']=='captured-at-evaluation','BODY_VALUE_SYMBOL')
            symbol=ref['symbol'];target=PREFIX+'binding:'+str(symbol['id'])
            if target not in ns:
                add(node(target,'correlated-build/binding/'+str(symbol['id']),
                    'Exact function-cell capture; values and later versions remain unbounded.',True))
                es.append(edge(target,[],f'correlated-build/binding-values/{symbol["id"]}',complete=False))
        es.append(edge(owner,[target],f'correlated-build/function-value/{ref["function"]}/{ref["site"]}'))
    # Attaching a source family does not make every sibling reachable. Follow
    # only the actual call references from the qualified entry bodies.
    outgoing=defaultdict(set)
    for e in es:outgoing[e['from']].update(e['targets'])
    reached=set(roots);pending=deque(roots)
    while pending:
        for t in outgoing[pending.popleft()]-reached:reached.add(t);pending.append(t)
    # A compiler LFUN and its later loaded instance can witness the same
    # AFUNC/literal dependency. Keep the semantic edge once, with both native
    # alternatives still explicit in the correspondence records.
    selected={json.dumps(e,sort_keys=True):e for e in es if e['from'] in reached}
    result=dict(nodes=[ns[i] for i in sorted(reached)],edges=list(selected.values()),
                replacements=[replace[k] for k in sorted(replace)],
                unrelated_family_functions=sorted(afuncs-{int(i.rsplit(':',1)[1]) for i in reached if i.startswith(PREFIX+'afunc:')}))
    if namespace!='correlated-build:':
        for row in result['nodes']+result['edges']:
            row['evidence']=row['evidence'].replace('correlated-build/',namespace.rstrip(':')+'/',1)
    return result


def apply(base,delta):
    replace={e['evidence']:e for e in delta['replacements']}
    original=[e for e in base['edges'] if e['evidence'] in replace]
    require(len(original)==len(replace) and all(e['resolution']=='unresolved' and not e['targets'] for e in original),
            'BODY_ORIGINAL_GAPS')
    return dict(base,nodes=base['nodes']+delta['nodes'],
                edges=[replace.get(e['evidence'],e) for e in base['edges']]+delta['edges'])


def run(output,base_path,evidence):
    matches=read(output/'body-correspondences.json')['matches']
    sample=next(iter(read(evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))
    operators={int(k):v for k,v in sample['operators'].items()}
    families,calls=extract(output/'build.jsonl.gz',matches,operators)
    base=read(base_path);delta=make(base,matches,families,calls);graph=apply(base,delta)
    require(graph==apply(base,make(base,matches,families,calls)),'BODY_EXACT_PROJECTION')
    save(output/'resident-ir.json.gz',dict(functions=families,calls=calls))
    save(output/'resident-body-delta.json.gz',delta);save(output/'census.json.gz',graph)
    report=dict(body_gaps_joined=len(matches),compiler_family_functions=len(families),
        attached_functions=sum(n['id'].startswith(PREFIX+'afunc:') for n in delta['nodes']),
        calls=dict(Counter(c['dependency']['category'] for c in calls)),
        untouched_original_computed_calls=True,borrowed_caller_bounds=0)
    save(output/'body-integration-summary.json',report);print(report)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    p.add_argument('--base',type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence');a=p.parse_args()
    run(a.output,a.base,a.evidence)
