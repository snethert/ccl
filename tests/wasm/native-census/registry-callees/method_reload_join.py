"""Qualify source-less method bodies by actual, byte-preserving replacements.

The old function is anchored to the earlier execution by its read-only inventory
and complete payload. A live replacement provides the precise registry role;
the FASL version supplies its compiler body. Every nested function literal is
checked recursively. No registry-state or caller-environment bound is borrowed.
"""
from collections import deque
from copy import deepcopy
from pathlib import Path
import hashlib
import json
from payloads import (read,save,require,rows,capture,before_functions,prefix_check,
                      dependency_body_key,literal_regions,source_key)
from loader import collect as loader_collect
from registry import replay
from bodies import extract


def replacements(events,requested):
    entered={};found=[]
    for row in events:
        if row['kind']=='mutation-enter':entered[row['sequence']]=row
        if row['kind']!='mutation-leave':continue
        first=entered[row['entry']]
        if first['operation']['symbol']!='%ADD-STANDARD-METHOD-TO-STANDARD-GF':continue
        method=first['method']
        for old in first['gf']['methods']:
            if old['id'] not in requested:continue
            if old['qualifiers']==method['qualifiers'] and old['specializers']==method['specializers']:
                require(row['completed'] is True and row['method']['id']==method['id']
                        and row['method']['owner']==old['owner']==first['gf']['gf'], 'RELOAD_REPLACEMENT_ROLE')
                found.append(dict(old=old,new=row['method'],gf=first['gf']['gf'],
                    enter=first['sequence'],leave=row['sequence'],build_event=first['build_event']))
    return found


def body_pairs(functions,loader,before,root_pairs,source):
    pending=deque(root_pairs);result={}
    while pending:
        a,b=pending.popleft()
        if (a,b) in result:continue
        require(a in functions and b in functions,'RELOAD_MISSING_FUNCTION')
        old=functions[a];new=functions[b]
        require(old['prototype']==a and new['prototype']==b,'RELOAD_CLOSURE_ENVIRONMENT')
        require(dependency_body_key(old,True)==dependency_body_key(new,True),'RELOAD_EXECUTABLE_BODY')
        provenance=[dict(function=b,**r,before=before[r['afunc']]) for r in loader.get(b,[])
                    if r['afunc'] in before and source_key(before[r['afunc']]['source'])==source]
        require(provenance,'RELOAD_COMPILER_PROVENANCE')
        dependencies=[]
        for index,(x,y) in enumerate(zip(literal_regions(old)[0],literal_regions(new)[0])):
            if isinstance(x,dict) and 'function' in x:
                require(isinstance(y,dict) and 'function' in y,'RELOAD_LITERAL_KIND')
                dependencies.append(dict(index=index,old=x['function'],new=y['function'],
                                         function_identity=x['function']==y['function'],environment_identity=False))
                if x['function']!=y['function']:pending.append((x['function'],y['function']))
        result[a,b]=dict(bootstrap_code=a,compiled_function=b,compiler_records=provenance,
                         literal_dependencies=dependencies,data_and_metadata_status='UNRESOLVED',
                         caller_environment_transferred=False)
    require(all(d['function_identity'] or (d['old'],d['new']) in result
                for r in result.values() for d in r['literal_dependencies']),'RELOAD_LITERAL_RELATION_NOT_CLOSED')
    return [result[k] for k in sorted(result)]


def controls(functions,loader,before,roots,source):
    results=[];a,b=roots[0]
    def refuse(name,fs,ld,br,rs,src,expected):
        try:body_pairs(fs,ld,br,rs,src)
        except ValueError as e:
            require(str(e)==expected,'RELOAD_CONTROL_REASON '+name)
            results.append(dict(name=name,status='REJECTED'));return
        raise ValueError('RELOAD_CONTROL_ESCAPED '+name)
    damaged=dict(functions);changed=dict(functions[b]);data=bytearray.fromhex(changed['payload_hex']);data[8]^=1
    changed['payload_hex']=data.hex();damaged[b]=changed
    refuse('changed-code',damaged,loader,before,roots,source,'RELOAD_EXECUTABLE_BODY')
    damaged=dict(functions);damaged[b]=dict(functions[b],bits=functions[b]['bits']^1)
    refuse('changed-function-bits',damaged,loader,before,roots,source,'RELOAD_EXECUTABLE_BODY')
    damaged=dict(functions);damaged[b]=dict(functions[b],prototype=a)
    refuse('borrow-closure-environment',damaged,loader,before,roots,source,'RELOAD_CLOSURE_ENVIRONMENT')
    missing=dict(loader);missing.pop(b)
    refuse('missing-loader-version',functions,missing,before,roots,source,'RELOAD_COMPILER_PROVENANCE')
    refuse('wrong-source-unit',functions,loader,before,roots,source+'-other','RELOAD_COMPILER_PROVENANCE')
    # Choose a real call-bearing pair, not a fabricated absent literal.
    for a,b in roots:
        index=next((i for i,v in enumerate(literal_regions(functions[b])[0]) if isinstance(v,dict) and 'symbol' in v),None)
        if index is None:continue
        damaged=dict(functions);changed=deepcopy(functions[b]);changed['literals'][index]['symbol']+=100000000
        damaged[b]=changed
        refuse('substitute-callable-symbol',damaged,loader,before,roots,source,'RELOAD_EXECUTABLE_BODY');break
    nested=next((d for r in body_pairs(functions,loader,before,roots,source) for d in r['literal_dependencies']
                 if not d['function_identity']),None)
    if nested:
        missing=dict(loader);missing.pop(nested['new'])
        refuse('omit-nested-body',functions,missing,before,roots,source,'RELOAD_COMPILER_PROVENANCE')
    return results


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    require(read(a.native/'native-summary.json')['status']=='PASS','RELOAD_NATIVE_RUN')
    fs,_,_,_,_=capture(a.capture/'registries.jsonl.gz')
    methods=read(a.previous/'method-body-joins.json.gz');remaining={r['prototype']:r for r in methods if r['witness'] is None}
    original={i:fs[i] for i in remaining};del fs
    joined={};summaries=[]
    operators={int(k):v for k,v in next(iter(read(a.evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))['operators'].items()}
    for name in ('sockets','describe','l1-io'):
        path=a.native/name;out=a.output/name;out.mkdir()
        source_record=read(path/'source.json');unit=source_record['source'];source_bytes=(a.source/unit).read_bytes()
        require(hashlib.sha256(source_bytes).hexdigest()==source_record['sha256'],'RELOAD_SOURCE_IDENTITY')
        actual_source=unit
        if source_record['selection']=='three-conditional-methods':
            excerpt=source_record['prefix'].encode()+source_bytes[source_record['start']:source_record['end']]
            require(excerpt==(path/'ccl/printer-methods.lisp').read_bytes()
                    and hashlib.sha256(excerpt).hexdigest()==source_record['excerpt_sha256'],'RELOAD_SOURCE_FRAGMENT')
            actual_source='printer-methods.lisp'
        require((path/'reference.dx64fsl').read_bytes()==(path/'observed.dx64fsl').read_bytes(),'RELOAD_FASL_OBSERVATION_DIFFERENCE')
        prefix_check(path/'build.jsonl.gz',a.evidence/'2026-09-14-resident-bodies-r1/first-prefix.jsonl.gz')
        functions,emissions,_,_,_=capture(path/'registries.jsonl.gz');before=before_functions(path/'build.jsonl.gz',emissions)
        loader,unjoined=loader_collect(path/'build.jsonl.gz',emissions,before)
        require(not unjoined,'RELOAD_UNJOINED_FASL_READS')
        registry,reg_summary=replay(rows(path/'registries.jsonl.gz'),functions,emissions,before,loader)
        require(not registry['state_gaps'],'RELOAD_UNEXPLAINED_REGISTRY_MUTATION')
        source_rows=read(path/'method-sources.json');requested={r['method']:r for r in source_rows}
        require(len(requested)==len(source_rows),'RELOAD_SOURCE_POPULATION')
        for r in source_rows:
            old=original[r['function']];current=functions[r['function']]
            require(old['payload_hex']==current['payload_hex'] and old['bits']==current['bits']
                    and old['prototype']==current['prototype'],'RELOAD_ANCHORED_PAYLOAD')
            require(r['sources'] and all(source_key(s['file'])==unit for s in r['sources']),'RELOAD_DEFINITION_SOURCE')
        changes=replacements(rows(path/'registries.jsonl.gz'),requested)
        require({r['old']['id'] for r in changes}==set(requested) and len(changes)==len(requested),
                'RELOAD_REPLACEMENT_COVERAGE')
        roots=[(r['old']['function'],r['new']['function']) for r in changes]
        pairs=body_pairs(functions,loader,before,roots,actual_source)
        for r in changes:
            code=r['old']['function'];require(code not in joined,'RELOAD_REPEATED_ORIGINAL_METHOD')
            record=next(p for p in pairs if p['bootstrap_code']==code and p['compiled_function']==r['new']['function'])
            require(all(e['event']<r['build_event'] for e in record['compiler_records']),'RELOAD_INSTALLATION_ORDER')
            joined[code]=dict(unit=name,replacement=r,body=record,source=requested[r['old']['id']],
                              initial_payload_sha256=hashlib.sha256(bytes.fromhex(functions[code]['payload_hex'])).hexdigest())
        tests=controls(functions,loader,before,roots,actual_source)
        families,calls=extract(path/'build.jsonl.gz',pairs,operators)
        save(out/'body-pairs.json.gz',pairs);save(out/'replacements.json',changes);save(out/'controls.json',tests)
        save(out/'ir.json.gz',dict(functions=families,calls=calls))
        summary=dict(unit=name,methods=len(changes),body_pairs=len(pairs),controls=len(tests),
            loader_reads=sum(map(len,loader.values())),registry_operations=reg_summary['operations'])
        summaries.append(summary);print(summary,flush=True)
    require(set(joined)==set(remaining),'RELOAD_ORIGINAL_POPULATION')
    for row in methods:
        if row['prototype'] in joined:
            require(row['witness'] is None,'RELOAD_PREVIOUS_WITNESS_CHANGED')
            row['witness']=dict(kind='OBSERVED_METHOD_REPLACEMENT',record=joined[row['prototype']])
            row['body_status']='QUALIFIED_DEPENDENCIES'
    require(all(r['witness'] and r['runtime_dispatch_bound'] is False for r in methods),'RELOAD_METHOD_BOUND_PROMOTION')
    save(a.output/'method-body-joins.json.gz',methods)
    summary=dict(status='PASS',methods=len(methods),new_method_bodies=len(joined),unresolved_method_bodies=0,
        units=summaries,runtime_dispatch_bound=False,body_identity_bridge='complete anchored read-only payload')
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native','capture','previous','source','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=Path(__file__).resolve().parents[5]/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
