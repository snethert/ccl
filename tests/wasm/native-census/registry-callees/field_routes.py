"""Group typed structure reads by native field without claiming its contents.

This supplies the receiver/field join needed by the writer analysis. It does
not infer a closed registry from observed values or turn an open field into a
finite callee bound. Native indexes are not Wasm/D1 offsets.
"""
from collections import Counter
from copy import deepcopy
from functools import partial
from pathlib import Path
import gzip,json,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'finite-callees'))
from run import read,save,convert,require,load_module,ROOT
from constructors import Resolver as ConstructorResolver


class Resolver(ConstructorResolver):
    def __init__(self,capture,constructor):
        super().__init__(capture,constructor);self.fields={}

    def resolve(self,value,owner,site,stack=()):
        g=self.graph;n=g.node(value)
        if n and n.get('operator')=='CCL::STRUCT-REF':
            args=g.items(n['operands']);require(len(args)==2,'FIELD_READ_ARITY')
            receiver=g.node(args[0]);index=g.node(args[1])
            seen=set()
            while index and index.get('operator') in ('CCL::TYPED-FORM','CCL::TYPE-ASSERTED-FORM'):
                require(index['id'] not in seen,'FIELD_INDEX_CYCLE');seen.add(index['id'])
                index=g.node(g.items(index['operands'])[1])
            if receiver and receiver.get('operator') in ('CCL::TYPED-FORM','CCL::TYPE-ASSERTED-FORM'):
                typed=g.items(receiver['operands']);typ=typed[0]
                if isinstance(typ,dict) and set(typ)=={'symbol','identity'} and index and index.get('operator')=='COMMON-LISP::FIXNUM':
                    ix=g.items(index['operands']);require(len(ix)==1,'FIELD_INDEX_ARITY')
                    if type(ix[0]) is int and ix[0]>=0:
                        key=str(typ['identity'])+':'+str(ix[0])
                        spec=dict(type_symbol=typ,index=ix[0],index_space='native-structure-slot')
                        require(key not in self.fields or self.fields[key]==spec,'FIELD_IDENTITY_CONFLICT')
                        self.fields[key]=spec
                        return {('field',key,'unbounded-field-value')},[dict(node=n['id'],operator=n['operator'],
                            receiver=args[0],field=key,value_bound=False)]
        return super().resolve(value,owner,site,stack)


def collect(cache,remaining,operators,constructor):
    wanted={(r['function_id'],r['site_id']):r for r in remaining};seen=set();routes=[];fields={}
    with gzip.open(cache,'rt') as src:
        for line in src:
            row=json.loads(line);resolver=Resolver(convert(row['payload'],operators),constructor)
            for result in resolver.calls():
                key=(result['function_id'],result['site_id'])
                if key not in wanted:continue
                require(key not in seen and wanted[key]['event']==row['sequence'],'FIELD_CALL_IDENTITY');seen.add(key)
                ts=result['targets']
                # Mixed expression alternatives stay on the original worklist.
                if not ts or not all(t['kind']=='field' for t in ts):continue
                routes.append(dict(function=key[0],site=key[1],event=row['sequence'],
                    fields=sorted({t['id'] for t in ts}),trace=result['steps'],status='FIELD_SELECTION_ONLY'))
                for t in ts:
                    spec=resolver.fields[t['id']]
                    require(t['id'] not in fields or fields[t['id']]==spec,'FIELD_GLOBAL_IDENTITY')
                    fields[t['id']]=spec
    require(seen==wanted.keys(),'FIELD_CALL_COVERAGE')
    return dict(routes=routes,fields=fields)


def writer_join(facts,writes):
    result={k:[] for k in facts['fields']}
    for w in writes:
        typ=w['receiver_type'];slot=w['slot']
        if typ is None or slot is None:continue
        key=str(typ['identity'])+':'+str(slot)
        if key not in result:continue
        require(typ==facts['fields'][key]['type_symbol'],'FIELD_WRITER_TYPE_IDENTITY')
        result[key].append(w)
    # Unknown receivers and constructor defaults remain obligations, even
    # where every typed write listed here has a finite RHS.
    return result


def project(base,facts,writes):
    joined=writer_join(facts,writes);nodes=[];edges=[];replacements=[];ids={n['id'] for n in base['nodes']}
    for key,spec in sorted(facts['fields'].items()):
        ident='field-values:'+key
        nodes.append(dict(id=ident,kind='function',required=True,disposition='unresolved',implementation=None,
            evidence='field-values/'+key,tests=['S0-LL15-b','S0-LL15-c'],
            reason='Native field '+spec['type_symbol']['symbol']+'['+str(spec['index'])+'] across receivers. '
                   'Constructor values, aliases, writes and target layout remain unqualified.'))
        edges.append({'from':ident,'targets':[],'phase':'run','origin':'conservative','resolution':'unresolved',
                      'evidence':'field-values/contents/'+key})
        for w in joined[key]:
            target='identity:build:afunc:'+str(w['function_id'])
            require(target in ids,'FIELD_WRITER_NOT_ATTACHED')
            edges.append({'from':ident,'targets':[target],'phase':'run','origin':'conservative','resolution':'complete',
                'evidence':f'field-values/writer/{key}/{w["function_id"]}/{w["site_id"]}'})
    for r in facts['routes']:
        require(r['status']=='FIELD_SELECTION_ONLY','FIELD_CALLEE_PROMOTION')
        replacements.append({'from':'identity:build:afunc:'+str(r['function']),
            'targets':['field-values:'+k for k in r['fields']], 'phase':'run','origin':'conservative','resolution':'complete',
            'evidence':f'build-flow/call/{r["function"]}/{r["site"]}'})
    return dict(nodes=nodes,edges=edges,replacements=replacements,typed_writes=joined)


def apply(base,delta):
    changes={e['evidence']:e for e in delta['replacements']};old=[e for e in base['edges'] if e['evidence'] in changes]
    require(len(old)==len(changes)==len(delta['replacements']) and all(e['resolution']=='unresolved' and not e['targets'] for e in old),
            'FIELD_ORIGINAL_CALLS')
    require(not {n['id'] for n in base['nodes']}&{n['id'] for n in delta['nodes']},'FIELD_NODE_COLLISION')
    return dict(base,nodes=base['nodes']+delta['nodes'],edges=[changes.get(e['evidence'],e) for e in base['edges']]+delta['edges'])


def check(base,graph,delta,facts,writes):
    require(delta==project(base,facts,writes),'FIELD_EXACT_PROJECTION')
    require(graph==apply(base,delta),'FIELD_EXACT_GRAPH')


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    ops={int(k):v for k,v in next(iter(read(a.evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))['operators'].items()}
    remaining=read(a.calls/'remaining-calls.json.gz');facts=collect(a.cache,remaining,ops,read(a.calls/'constructor.json'))
    writes=read(a.writes);base=read(a.base);delta=project(base,facts,writes);graph=apply(base,delta)
    check(base,graph,delta,facts,writes);tests=[]
    for name,mutate in [
        ('omit-call-route',lambda d:d['replacements'].pop()),
        ('substitute-field',lambda d:d['replacements'][0].update(targets=[])),
        ('claim-closed-field',lambda d:d['edges'][0].update(resolution='complete')),
        ('discard-typed-writer',lambda d:next(v for v in d['typed_writes'].values() if v).pop()),
        ('claim-implemented-field',lambda d:d['nodes'][0].update(disposition='implemented'))]:
        d=deepcopy(delta);mutate(d)
        try:check(base,graph,d,facts,writes)
        except ValueError as e:require(str(e)=='FIELD_EXACT_PROJECTION','FIELD_CONTROL_REASON')
        else:raise ValueError('FIELD_CONTROL_ESCAPED '+name)
        tests.append(dict(name=name,status='REJECTED'))
    errors=load_module('field_contract',ROOT/'doc/WASM/tools/check-census.py').validate(graph)
    require(all(e.startswith(('unresolved reachable edge from ','unimplemented reachable node ')) for e in errors),'FIELD_GRAPH_STRUCTURE')
    for name,value in [('routes.json.gz',facts),('delta.json.gz',delta),('census.json.gz',graph),('controls.json',tests)]:save(a.output/name,value)
    summary=dict(status='PASS',census_status='BLOCKED',routed_calls=len(facts['routes']),field_families=len(facts['fields']),
        typed_writes=sum(map(len,delta['typed_writes'].values())),by_type=dict(Counter(v['type_symbol']['symbol'] for v in facts['fields'].values())),
        new_callee_bounds=0,unbounded_original_calls=len(remaining),controls=len(tests))
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('cache','calls','writes','base','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
