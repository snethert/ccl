"""Connect the complete observed method population to executable dependencies.

Registry and function-cell edges remain unresolved for future contents. Each
execution has a separate namespace; the reload witnesses bridge only their
anchored read-only bodies, never their dynamic generic-function objects.
"""
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import sys
from payloads import read,save,require,capture,literal_regions,rows
import bodies
from method_graph_check import project,check_join

HERE=Path(__file__).resolve().parent


def actual_match(code,functions,records,before):
    fn=functions[code];compiled=[dict(e,function=code,before=before[e['afunc']]) for e in records if e['afunc'] in before]
    require(compiled,'METHOD_GRAPH_COMPILER_RECORD')
    m=dict(bootstrap_code=code,metadata_disposition='UNRESOLVED',compiler_records=compiled,compiled_functions=[code])
    data=[];literals=[]
    for i,value in enumerate(literal_regions(fn)[0]):
        if isinstance(value,dict) and 'function' in value:
            literals.append(dict(index=i,compiled_owner=code,bootstrap_function=value['function'],
                compiled_function=value['function'],relation='EXACT_LITERAL_IDENTITY',function_identity=True,environment_identity=False))
        elif isinstance(value,dict) and ('object' in value or 'string' in value):
            data.append(dict(index=i,disposition='UNRESOLVED',callable=False))
    if data:m['data_dependencies']=data
    if literals:m['function_literal_correspondences']=literals
    return m


def reload_match(record):
    code=record['bootstrap_code'];candidate=record['compiled_function']
    result=dict(bootstrap_code=code,metadata_disposition='UNRESOLVED',
        compiler_records=record['compiler_records'],compiled_functions=[candidate],
        data_dependencies=[dict(index='materialization',disposition='UNRESOLVED',callable=False)])
    literals=[]
    for d in record['literal_dependencies']:
        literals.append(dict(index=d['index'],compiled_owner=candidate,bootstrap_function=d['old'],compiled_function=d['new'],
            relation='EXACT_LITERAL_IDENTITY' if d['function_identity'] else 'QUALIFIED_EXECUTION_BODY',
            function_identity=d['function_identity'],environment_identity=False))
    if literals:result['function_literal_correspondences']=literals
    return result


def group_graph(name,roots,support,families,calls,deferred=()):
    namespace='method-census:'+name+':'
    anchor=namespace+'code:';evidence='method-census/'+name+'/body/'
    base=dict(nodes=[bodies.node(anchor+str(m['bootstrap_code']),evidence+str(m['bootstrap_code']),
        'Observed method code; materialization and enclosing values are separate obligations.') for m in roots],
        edges=[bodies.edge(anchor+str(m['bootstrap_code']),[],evidence+str(m['bootstrap_code']),'compile',False) for m in roots])
    delta=bodies.make(base,roots,families,calls,support,deferred,namespace,anchor,evidence)
    graph=bodies.apply(base,delta)
    require(len({n['id'] for n in graph['nodes']})==len(graph['nodes']),'METHOD_GRAPH_NODE_COLLISION')
    return graph


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    methods=read(a.methods/'method-body-joins.json.gz')
    require(len(methods)==2264 and all(m['witness'] and m['runtime_dispatch_bound'] is False for m in methods),
            'METHOD_GRAPH_POPULATION')
    fs,emissions,_,_,_=capture(a.capture/'registries.jsonl.gz')
    before={int(k):v for k,v in read(a.previous/'compiler-index.json.gz')['before'].items()}
    loader={int(k):v for k,v in read(a.previous/'loader-body-joins.json.gz')['joins'].items()}
    corr=read(a.bodies/'body-correspondences.json.gz');correspondences={m['bootstrap_code']:m for m in corr['matches']+corr['support_matches']}
    templates=read(a.previous/'accessor-templates.json');deferred=read(a.bodies/'deferred-initializers.json.gz')['placeholders']
    roots={};method_targets={}
    for m in methods:
        code=m['prototype'];w=m['witness'];kind=w['kind']
        if kind=='OBSERVED_METHOD_REPLACEMENT':
            name=w['record']['unit'];method_targets[m['method']['id']]=f'method-census:{name}:code:{code}';continue
        if kind=='EXECUTION_BODY_CORRESPONDENCE':match=correspondences[code]
        elif kind=='ACCESSOR_TEMPLATE':
            t=templates[w['record']['kind']];native=t['compiler_records']
            match=dict(bootstrap_code=code,metadata_disposition='UNRESOLVED',
                compiler_records=[dict(e,function=t['function'],before=before[e['afunc']]) for e in native],
                compiled_functions=[t['function']],data_dependencies=[dict(index=0,disposition='UNRESOLVED',callable=False)])
        else:
            require(kind in ('COMPILER_MATERIALIZATION','FASL_VERSION'),'METHOD_GRAPH_WITNESS_KIND')
            match=actual_match(code,fs,w['records'],before)
        require(code not in roots or roots[code]==match,'METHOD_GRAPH_CODE_CONFLICT');roots[code]=match
        method_targets[m['method']['id']]=f'method-census:build:code:{code}'
    support=dict(correspondences);support.update(roots)
    pending=list(roots);seen=set()
    while pending:
        code=pending.pop()
        if code in seen:continue
        seen.add(code)
        for d in support[code].get('function_literal_correspondences',[]):
            target=d['bootstrap_function']
            if target not in support and target in fs:
                records=loader.get(target,[])+emissions.get(target,[])
                if any(e['afunc'] in before for e in records):support[target]=actual_match(target,fs,records,before)
            if target in support:pending.append(target)
    extra=[support[k] for k in sorted(seen-set(roots))]
    sample=next(iter(read(a.evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))
    operators={int(k):v for k,v in sample['operators'].items()}
    print('Extracting all observed method bodies and their initializer dependencies.',flush=True)
    families,calls=bodies.extract(a.capture/'build.jsonl.gz',bodies.with_initializers(
        bodies.needed_matches(list(roots.values()),extra),deferred),operators)
    save(a.output/'build-ir.json.gz',dict(functions=families,calls=calls))
    build=group_graph('build',list(roots.values()),extra,families,calls,deferred)
    groups=[build]
    for name in ('sockets','describe','l1-io'):
        pairs=read(a.methods/name/'body-pairs.json.gz');matches=[reload_match(p) for p in pairs]
        wanted={m['prototype'] for m in methods if m['witness']['kind']=='OBSERVED_METHOD_REPLACEMENT'
                and m['witness']['record']['unit']==name}
        ir=read(a.methods/name/'ir.json.gz')
        groups.append(group_graph(name,[m for m in matches if m['bootstrap_code'] in wanted],
            [m for m in matches if m['bootstrap_code'] not in wanted],ir['functions'],ir['calls']))
    registry=read(a.previous/'registry-joins.json.gz')['registries']
    print('Connecting same-execution function-cell observations to generic-function registries.',flush=True)
    sys.path.insert(0,str(HERE.parent/'binding-versions'))
    from collect import collect as binding_stream
    facts,_=binding_stream(a.capture/'build.jsonl.gz')
    gfids={r['gf'] for r in registry};bindings=defaultdict(set)
    for b in facts['bindings']:
        v=b['value'];symbol=b['symbol']
        if b['kind']=='binding-removing' or v['role']!='function' or symbol.get('kind')!='symbol':continue
        if v['object'] in gfids:bindings[symbol['id']].add(v['object'])
    base=read(a.base)
    graph=project(base,groups,methods,registry,method_targets,bindings)
    check_join(base,graph,groups,methods,registry,bindings)
    from test_method_graph import controls
    checks=controls(base,graph,groups,methods,registry,bindings)
    connected=sum(a!=b for a,b in zip(base['edges'],graph['edges']))
    save(a.output/'groups.json.gz',groups)
    save(a.output/'census.json.gz',graph)
    save(a.output/'controls.json',checks)
    save(a.output/'observed-gf-bindings.json',{str(k):sorted(v) for k,v in bindings.items()})
    from support import load_module
    errors=load_module('method_graph_contract',HERE.parents[3]/'doc/WASM/tools/check-census.py').validate(graph)
    require(all(e.startswith(('unresolved reachable edge from ','unimplemented reachable node ')) for e in errors),'METHOD_GRAPH_STRUCTURE')
    summary=dict(status='PASS',census_status='BLOCKED',methods=len(methods),generic_functions=len(registry),
        connected_existing_cells=connected,method_bodies_attached=len(method_targets),
        controls=len(checks),future_registry_contents_qualified=False,graph_nodes=len(graph['nodes']),graph_edges=len(graph['edges']))
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','previous','bodies','methods','base','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
