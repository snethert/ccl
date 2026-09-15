"""Trace named callback keywords through the recorded stream-construction calls.

Known direct call sites supply value dependencies. They do not establish the
absence of indirect callers, and an APPLY relay retains its list-aliasing and
function-cell-version obligations.
"""
from collections import Counter
from pathlib import Path
import gzip,json,sys
from field_inputs import Resolver as FieldResolver,read,save,require,convert,Raw,ROOT,Unbounded


class Resolver(FieldResolver):
    def resolve(self,value,owner,site,stack=()):
        n=self.graph.node(value)
        if n and n.get('operator')=='NIL':
            require(not self.graph.items(n['operands']),'KEYWORD_NIL_ARGS')
            return {('literal','nil','literal-value')},[dict(node=n['id'],literal='nil')]
        return super().resolve(value,owner,site,stack)


def arguments(g,site):
    n=g.nodes[site];require(n['operator']=='CCL::CALL','KEYWORD_CALL_OPERATOR')
    args=g.items(n['operands']);require(len(args)==3,'KEYWORD_CALL_SHAPE')
    parts=g.items(args[1]);require(len(parts)==2,'KEYWORD_ARGUMENT_PARTS')
    actual=g.items(parts[0])+list(reversed(g.items(parts[1])))
    cn=g.node(args[0]);require(cn and cn['operator']=='CCL::IMMEDIATE','KEYWORD_DIRECT_CALLEE')
    name=g.items(cn['operands']);require(len(name)==1 and isinstance(name[0],dict) and
        set(name[0])=={'identity','symbol'},'KEYWORD_CALLEE_SYMBOL')
    return name[0],actual,args[2]


def bind(g,actual,required,keywords):
    require(len(actual)>=required and (len(actual)-required)%2==0,'KEYWORD_CALL_ARITY')
    result={};seen=set()
    for k,v in zip(actual[required::2],actual[required+1::2]):
        n=g.node(k)
        require(n and n['operator']=='CCL::IMMEDIATE','KEYWORD_DYNAMIC_KEY')
        xs=g.items(n['operands']);require(len(xs)==1 and isinstance(xs[0],dict) and
            set(xs[0])=={'identity','symbol'},'KEYWORD_KEY_SYMBOL')
        ident=xs[0]['identity']
        # Common Lisp takes the leftmost occurrence. Values at later
        # occurrences are still evaluated; their ordinary call edges remain.
        if ident in seen:continue
        seen.add(ident)
        if ident in keywords:result[ident]=v
    return result


def collect(ir_rows,init_ir,inputs,calls,operators,constructor):
    rg=Raw(init_ir['payload']['ir']);root=rg.node(rg.root);init_symbol=rg.node(root['name'])
    init=Resolver(convert(init_ir['payload'],operators),constructor,init_ir['payload']['ir']);g=init.graph
    wanted={int(k.split(':')[1]):v for k,v in inputs.items()}
    require(all(v['function']==root['id'] and v['kind']=='keyword' for v in wanted.values()),'KEYWORD_INPUT_OWNER')
    kw={v['keyword']['id']:v for v in wanted.values()}
    rows={r['sequence']:r for r in ir_rows}
    direct=[c for c in calls if c.get('global_symbol',{}).get('id')==init_symbol['id']]
    require(len(direct)==1,'KEYWORD_RELAY_POPULATION')
    d=direct[0];raw=rows[d['event']];relay=Resolver(convert(raw['payload'],operators),constructor,raw['payload']['ir'])
    name,args,spread=arguments(relay.graph,d['site_id'])
    require(name['identity']==init_symbol['id'] and spread and spread.get('symbol')=='COMMON-LISP::T' and len(args)==2,
            'KEYWORD_RELAY_APPLY')
    lam=relay.graph.node(relay.graph.nodes[d['function_id']]['body']);la=relay.graph.items(lam['operands'])
    require(lam['operator']=='CCL::LAMBDA-LIST' and len(la) in (7,8) and len(relay.graph.items(la[0]))==1 and
            la[1] is None,'KEYWORD_RELAY_SIGNATURE')
    rest=relay.graph.node(la[2]);tail=relay.graph.node(args[-1])
    require(rest and rest['kind']=='variable' and tail and tail['operator']=='CCL::LEXICAL-REFERENCE' and
            relay.graph.node(relay.graph.items(tail['operands'])[0])['root']==rest['root'],'KEYWORD_RELAY_TAIL')
    rraw=Raw(raw['payload']['ir']);relay_symbol=rraw.node(rraw.node(rraw.root)['name'])
    # Names are display only; global call symbol IDs select the callers.
    incoming=[c for c in calls if c.get('global_symbol',{}).get('id')==relay_symbol['id']]
    require(incoming,'KEYWORD_INCOMING_CALLS');result=[];returns={};parameters={};symbols={}
    for c in incoming:
        r=rows[c['event']];res=Resolver(convert(r['payload'],operators),constructor,r['payload']['ir']);g=res.graph
        syms={n['id']:n for n in r['payload']['ir']['objects'] if n['kind']=='symbol'}
        name,actual,spread=arguments(g,c['site_id'])
        require(name['identity']==relay_symbol['id'] and spread is None,'KEYWORD_INCOMING_DIRECT')
        bound=bind(g,actual,1,kw)
        for key,spec in sorted(kw.items()):
            if key not in bound:
                dn=init.graph.node(spec['default']);require(dn['operator']=='NIL','KEYWORD_DEFAULT_NOT_NIL')
                ts={('literal','nil','literal-value')};steps=[dict(default=spec['default'])];value=None
            else:
                value=bound[key];ts,steps=res.resolve(value,c['function_id'],c['site_id'])
            targets=[]
            for kind,ident,mode in sorted(ts):
                targets.append(dict(kind=kind,id=ident,mode=mode))
                if kind=='return':returns[ident]=res.returns[ident]
                elif kind=='input':parameters[ident]=res.inputs[ident]
                elif kind=='symbol':symbols[ident]=syms[ident]
                else:require(kind=='literal','KEYWORD_VALUE_KIND')
            result.append(dict(input=f'{root["id"]}:{spec["variable"]}',keyword=spec['keyword'],
                caller=c['function_id'],site=c['site_id'],event=c['event'],value=value,targets=targets,steps=steps))
    return dict(relay=dict(function=d['function_id'],site=d['site_id'],symbol=relay_symbol,callee=init_symbol,
        rest_variable=rest['root'],event=d['event'],cell_version_bound=False,rest_alias_bound=False),
        paths=result,returns=returns,parameters=parameters,symbols=symbols,incoming_population=incoming)


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    ops={int(k):v for k,v in next(iter(read(a.evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))['operators'].items()}
    with gzip.open(a.cache,'rt') as src:irs=[json.loads(line) for line in src]
    facts=collect(irs,read(a.init_ir),read(a.inputs/'write-values.json.gz')['inputs'],
                  read(a.evidence/'2026-09-14-build-flow-r1/calls.json.gz'),ops,read(a.constructor))
    save(a.output/'keyword-paths.json.gz',facts)
    summary=dict(status='PASS',known_direct_callers=len(facts['incoming_population']),keyword_paths=len(facts['paths']),
        symbol_values=len(facts['symbols']),call_results=len(facts['returns']),external_parameters=len(facts['parameters']),
        closed_runtime_parameter_bounds=0,relay_version_and_aliasing='OPEN')
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('cache','init-ir','inputs','constructor','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():
            (a.output/'failure.txt').write_text(traceback.format_exc())
            (a.output/'executed-source.py').write_bytes(Path(__file__).read_bytes())
        raise
