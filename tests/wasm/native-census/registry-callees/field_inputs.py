"""Connect every typed callback write to its value dependencies.

An input, a field copy or a call result is a named open dependency, never an
observed value promoted to an exhaustive callable set.
"""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import gzip,json,sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'finite-callees'))
from run import read,save,convert,require,load_module,ROOT
from finite import Unbounded
from field_routes import Resolver as FieldResolver
from scan import receiver_type,expression
from structure_values import Raw


class Resolver(FieldResolver):
    def __init__(self,capture,constructor,raw):
        super().__init__(capture,constructor);self.inputs={};self.input_variables={}
        self.returns={};g=self.graph;rg=Raw(raw)
        for owner in self.family:
            lam=g.node(g.nodes[owner]['body'])
            if not lam or lam.get('operator')!='CCL::LAMBDA-LIST':continue
            args=g.items(lam['operands'])
            require(len(args) in (7,8),'FIELD_INPUT_LAMBDA')
            # Required parameters use the already-checked lexical resolver.
            for ix,v in enumerate(g.items(args[0])):
                self.add_input(owner,v,dict(kind='required',ordinal=ix))
            if args[3] is not None:
                keyargs=g.items(args[3]);require(len(keyargs)==5,'FIELD_INPUT_KEY_SHAPE')
                vs=self.cells(keyargs[1]);ds=g.items(keyargs[3]);kv=rg.node(keyargs[4])
                require(kv.get('kind')=='simple-vector' and kv['expanded'] and
                        kv['length']==len(kv['elements'])==len(vs)==len(ds),'FIELD_INPUT_KEY_VECTOR')
                for cell,d,k in zip(vs,ds,kv['elements']):
                    self.roles[owner,cell['id'],'car']='parameter'
                    self.add_input(owner,cell['car'],dict(kind='keyword',keyword=rg.node(k),default=d,
                                                        allow_other_keys=keyargs[0]))

    def add_input(self,owner,value,spec):
        var=self.graph.node(value)
        require(var and var['kind']=='variable','FIELD_INPUT_VARIABLE')
        ident=f'{owner}:{var["root"]}'
        require(var['root'] not in self.input_variables,'FIELD_INPUT_DUPLICATE')
        self.input_variables[var['root']]=ident
        self.inputs[ident]=dict(function=owner,variable=var['root'],name=var['name'],**spec)

    def resolve(self,value,owner,site,stack=()):
        g=self.graph;n=g.node(value)
        if n and n.get('operator') in ('CCL::LEXICAL-REFERENCE','CCL::INHERITED-ARG'):
            xs=g.items(n['operands']);var=g.node(xs[0]) if len(xs)==1 else None
            if var and var['kind']=='variable' and not self.bindings[var['root']] and var['root'] in self.input_variables:
                ident=self.input_variables[var['root']];spec=self.inputs[ident]
                self.immutable(var['root'])
                if spec['function']==owner:
                    return {('input',ident,'caller-values-unbounded')},[dict(node=n['id'],input=ident)]
        if n and n.get('operator') in ('CCL::CALL','CCL::%ERR-DISP'):
            # Preserve the call's own dependency and the fact that its return
            # value is not bounded. In particular %ERR-DISP is not discarded
            # by guessing that every error path is nonreturning.
            ident=f'{owner}:{n["id"]}';xs=g.items(n['operands'])
            if n['operator']=='CCL::CALL':
                call=next((c for c in self.family[owner]['calls'] if c['site_id']==n['id']),None)
                require(call is not None,'FIELD_RETURN_CALL_JOIN')
            else:call=None
            self.returns[ident]=dict(function=owner,site=n['id'],operator=n['operator'],call=call,
                                    expression=expression(g,value))
            return {('return',ident,'return-values-unbounded')},[dict(node=n['id'],return_value=ident)]
        return super().resolve(value,owner,site,stack)


def collect(cache,field_delta,operators,constructor):
    wanted={};result=[];inputs={};returns={};fields={}
    for key,ws in field_delta['typed_writes'].items():
        for w in ws:
            ident=(w['function_id'],w['site_id'])
            require(ident not in wanted,'FIELD_WRITE_DUPLICATE');wanted[ident]=(key,w)
    seen=set();events={w['event'] for _,w in wanted.values()}
    with gzip.open(cache,'rt') as src:
        for line in src:
            r=json.loads(line)
            if r['sequence'] not in events:continue
            cap=convert(r['payload'],operators);resolver=Resolver(cap,constructor,r['payload']['ir']);g=resolver.graph
            syms={n['id']:n for n in r['payload']['ir']['objects'] if n['kind']=='symbol'}
            for owner in resolver.family:
                for node in g.body(owner):
                    ident=(owner,node['id'])
                    if ident not in wanted:continue
                    key,w=wanted[ident];require(ident not in seen and w['event']==r['sequence'],'FIELD_WRITE_EVENT');seen.add(ident)
                    args=g.items(node['operands'])
                    require(node['operator']==w['operator'] and len(args)==3 and
                            receiver_type(g,args[0])==w['receiver_type'] and expression(g,args[-1])==w['value'],
                            'FIELD_WRITE_INPUT')
                    try:targets,trace=resolver.resolve(args[-1],owner,node['id'])
                    except Unbounded as e:raise ValueError(f'FIELD_WRITE_UNRESOLVED {ident}: {e}') from e
                    ts=[]
                    for k,i,m in sorted(targets):
                        t=dict(kind=k,id=i,mode=m)
                        if k=='symbol':t['descriptor']=syms[i]
                        elif k=='input':inputs[i]=resolver.inputs[i]
                        elif k=='return':returns[i]=resolver.returns[i]
                        elif k=='field':fields[i]=resolver.fields[i]
                        else:require(k=='afunc','FIELD_VALUE_KIND')
                        ts.append(t)
                    if w['status']=='FINITE_VALUE':require(ts==w['targets'],'FIELD_OLD_BOUND_CHANGED')
                    result.append(dict(field=key,function=owner,site=node['id'],event=r['sequence'],targets=ts,steps=trace,
                                       finite=all(t['kind'] in ('symbol','afunc') for t in ts)))
    require(seen==wanted.keys(),'FIELD_WRITE_COVERAGE')
    return dict(writes=sorted(result,key=lambda r:(r['function'],r['site'])),inputs=inputs,returns=returns,fields=fields)


def project(base,facts):
    ids={n['id'] for n in base['nodes']};nodes=[];edges=[]
    def edge(owner,targets,ev,resolution='complete'):
        edges.append({'from':owner,'targets':targets,'phase':'run','origin':'conservative','resolution':resolution,'evidence':ev})
    def unresolved(ident,reason,ev):
        if ident in ids:return
        ids.add(ident);nodes.append(dict(id=ident,kind='function',required=True,disposition='unresolved',implementation=None,
            reason=reason,evidence=ev,tests=['S0-LL15-b','S0-LL15-c']))
        edge(ident,[],ev+'/values','unresolved')
    for key,spec in facts['inputs'].items():
        ident='field-input:'+key
        unresolved(ident,'Caller-supplied '+spec['kind']+' input '+spec['name']+'; incoming values remain open.','field-input/'+key)
        target='identity:build:afunc:'+str(spec['function']);require(target in ids,'FIELD_INPUT_OWNER')
        edge(ident,[target],'field-input/'+key+'/owner')
    for key,spec in facts['returns'].items():
        ident='field-return:'+key
        unresolved(ident,'Value returned from '+spec['operator']+'; no return-value bound is assumed.','field-return/'+key)
        if spec['call']:
            ev=f'build-flow/call/{spec["function"]}/{spec["site"]}'
            old=[e for e in base['edges'] if e['evidence']==ev];require(len(old)==1,'FIELD_RETURN_DEPENDENCY')
            edge(ident,old[0]['targets'],'field-return/'+key+'/callee',old[0]['resolution'])
        else:
            edge(ident,['identity:build:afunc:'+str(spec['function'])],'field-return/'+key+'/owner')
    for r in facts['writes']:
        targets=[]
        for t in r['targets']:
            k=t['kind'];i=t['id']
            if k=='symbol':
                ident='identity:build:binding-cell:'+str(i)
                unresolved(ident,'Symbol-cell values of '+t['descriptor']['name']+' remain open.','field-write/symbol/'+str(i))
            elif k=='afunc':ident='identity:build:afunc:'+str(i)
            else:ident={'input':'field-input:','return':'field-return:','field':'field-values:'}[k]+i
            require(ident in ids,'FIELD_VALUE_ENDPOINT');targets.append(ident)
        edge('field-values:'+r['field'],sorted(set(targets)),f'field-write/value/{r["function"]}/{r["site"]}')
    return dict(nodes=nodes,edges=edges)


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    ops={int(k):v for k,v in next(iter(read(a.evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))['operators'].items()}
    facts=collect(a.cache,read(a.fields/'delta.json.gz'),ops,read(a.constructor));base=read(a.base);delta=project(base,facts)
    graph=dict(base,nodes=base['nodes']+delta['nodes'],edges=base['edges']+delta['edges'])
    errors=load_module('field_input_contract',ROOT/'doc/WASM/tools/check-census.py').validate(graph)
    require(all(e.startswith(('unresolved reachable edge from ','unimplemented reachable node ')) for e in errors),'FIELD_INPUT_GRAPH')
    for name,value in [('write-values.json.gz',facts),('delta.json.gz',delta),('census.json.gz',graph)]:save(a.output/name,value)
    summary=dict(status='PASS',typed_writes=len(facts['writes']),finite_write_values=sum(r['finite'] for r in facts['writes']),
        parameter_dependencies=len(facts['inputs']),call_result_dependencies=len(facts['returns']),
        copied_field_dependencies=len(facts['fields']),field_contents_closed=0,census_status='BLOCKED')
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('cache','fields','constructor','base','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():
            (a.output/'failure.txt').write_text(traceback.format_exc())
            (a.output/'executed-source.py').write_bytes(Path(__file__).read_bytes())
        raise
