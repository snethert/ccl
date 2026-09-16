"""Join address-taking sites from complete compiler IR, separately from calls."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
from payloads import read,save,require
from bodies import selected_rows
from flow import convert,functions
from analysis import Graph

HERE=Path(__file__).resolve().parent
OPS={'CCL::SIMPLE-FUNCTION','CCL::CLOSED-FUNCTION','CCL::%FUNCTION'}


def extract(stream,recorded,operators):
    wanted={f['function_id']:f for f in recorded if f['function_references']}
    events={f['event'] for f in wanted.values()};found={};seen=set()
    for event in selected_rows(stream,events):
        require(event['sequence'] not in seen and event['kind']=='before-pass2','VALUE_IR_EVENT')
        seen.add(event['sequence']);cap=convert(event['payload'],operators);g=Graph(cap['flow'])
        raw={n['id']:n for n in event['payload']['ir']['objects']}
        for f in functions(cap['function']):
            sites=[n for n in g.body(f['function_id']) if n['operator'] in OPS]
            require([n['id'] for n in sites]==[r['site_id'] for r in f['function_references']],
                    'VALUE_IR_SITE_COVERAGE')
            if not sites:continue
            require(f['function_id'] in wanted,'VALUE_UNRECORDED_FUNCTION')
            old=wanted[f['function_id']]
            require(old['event']==event['sequence'] and old['function_references']==f['function_references'],
                    'VALUE_RECORDED_FUNCTION')
            for n,ref in zip(sites,f['function_references']):
                args=g.items(n['operands']);require(len(args)==1,'VALUE_OPERAND_ARITY')
                dep=ref['dependency'];row=dict(function=f['function_id'],site=n['id'],event=event['sequence'],operator=n['operator'])
                if n['operator']=='CCL::%FUNCTION':
                    value=args[0]
                    require(isinstance(value,dict) and set(value)=={'symbol','identity'},'VALUE_SYMBOL_OPERAND')
                    symbol=raw[value['identity']]
                    require(symbol['kind']=='symbol' and dep==dict(category='global-binding',
                        targets=[dict(kind='global-binding',name=value['symbol'])]),'VALUE_SYMBOL_DESCRIPTOR')
                    row.update(kind='symbol',symbol=symbol,value_time='captured-at-evaluation')
                else:
                    target=g.node(args[0])
                    require(target and target['kind']=='function' and dep==dict(category='lexical-function-value',
                        targets=[dict(kind='function',id=target['id'],name=target['name'])]),'VALUE_LEXICAL_TARGET')
                    row.update(kind='lexical',target=target['id'],environment_bound=False)
                key=(row['function'],row['site']);require(key not in found,'VALUE_DUPLICATE_SITE');found[key]=row
    require(seen==events and set(found)=={(f['function_id'],r['site_id']) for f in wanted.values() for r in f['function_references']},
            'VALUE_POPULATION_COVERAGE')
    return [found[k] for k in sorted(found)]


def project(base,records,histories):
    ids={n['id'] for n in base['nodes']};cells={};edges=[];hs={h['symbol_id']:h for h in histories}
    for r in records:
        owner='identity:build:afunc:'+str(r['function'])
        require(owner in ids,'VALUE_OWNER_NOT_ATTACHED')
        if r['kind']=='lexical':
            target='identity:build:afunc:'+str(r['target'])
            require(target in ids and r['environment_bound'] is False,'VALUE_LEXICAL_NOT_ATTACHED')
        else:
            symbol=r['symbol'];i=symbol['id'];target='identity:build:binding-cell:'+str(i)
            require(r['kind']=='symbol' and symbol['kind']=='symbol' and r['value_time']=='captured-at-evaluation',
                    'VALUE_CAPTURE_SCOPE')
            if i in hs:require(symbol in hs[i]['descriptors'],'VALUE_BINDING_IDENTITY')
            if target not in ids:
                cells[target]=dict(id=target,kind='function',required=True,disposition='unresolved',implementation=None,
                    evidence=f'function-values/cell/{i}',tests=['S0-LL15-b','S0-LL15-c'],
                    reason='Exact symbol cell read by a function-value expression; callable contents and versions remain unbounded.')
        edges.append({'from':owner,'targets':[target],'phase':'run','origin':'conservative','resolution':'complete',
                      'evidence':f'function-values/site/{r["function"]}/{r["site"]}'})
    for ident in sorted(cells):
        edges.append({'from':ident,'targets':[],'phase':'run','origin':'conservative','resolution':'unresolved',
                      'evidence':'function-values/open/'+ident.rsplit(':',1)[1]})
    return dict(nodes=[cells[i] for i in sorted(cells)],edges=edges)


def apply(base,delta):
    require(not ({e['evidence'] for e in base['edges']}&{e['evidence'] for e in delta['edges']}),'VALUE_EDGE_COLLISION')
    return dict(base,nodes=base['nodes']+delta['nodes'],edges=base['edges']+delta['edges'])


def check(base,graph,delta,records,histories):
    require(delta==project(base,records,histories),'VALUE_EXACT_DELTA')
    require(graph==apply(base,delta),'VALUE_EXACT_GRAPH')


def controls(base,graph,delta,records,histories):
    result=[]
    for name,mutate in [
        ('omit-reference',lambda d:d['edges'].pop(0)),
        ('duplicate-reference',lambda d:d['edges'].append(d['edges'][0])),
        ('wrong-lexical-target',lambda d:d['edges'][0].update(targets=[d['edges'][0]['from']])),
        ('promote-cell-value',lambda d:next(e for e in d['edges'] if e['resolution']=='unresolved').update(resolution='complete')),
        ('substitute-phase',lambda d:d['edges'][0].update(phase='compile'))]:
        d=deepcopy(delta);mutate(d)
        try:check(base,graph,d,records,histories)
        except ValueError as e:require(str(e)=='VALUE_EXACT_DELTA','VALUE_CONTROL_REASON')
        else:raise ValueError('VALUE_CONTROL_ESCAPED '+name)
        result.append(dict(name=name,status='REJECTED'))
    return result


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    fs=read(a.evidence/'2026-09-14-build-flow-r1/functions.json.gz')
    ops={int(k):v for k,v in next(iter(read(a.evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))['operators'].items()}
    records=extract(a.stream,fs,ops);save(a.output/'references.json.gz',records)
    base=read(a.base);histories=read(a.evidence/'2026-09-14-binding-versions-r1/histories.json.gz')
    delta=project(base,records,histories);graph=apply(base,delta);check(base,graph,delta,records,histories)
    tests=controls(base,graph,delta,records,histories)
    from support import load_module
    errors=load_module('value_contract',HERE.parents[3]/'doc/WASM/tools/check-census.py').validate(graph)
    require(all(e.startswith(('unresolved reachable edge from ','unimplemented reachable node ')) for e in errors),
            'VALUE_GRAPH_STRUCTURE')
    for name,value in [('delta.json.gz',delta),('census.json.gz',graph),('controls.json',tests)]:save(a.output/name,value)
    summary=dict(status='PASS',census_status='BLOCKED',references=len(records),kinds=dict(Counter(r['kind'] for r in records)),
                 new_cells=len(delta['nodes']),controls=len(tests),cell_value_bounds=False,closure_environment_bounds=False)
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('stream','base','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
