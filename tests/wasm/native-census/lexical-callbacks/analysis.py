"""Resolve immutable local callback bindings from observed, unmodified CCL acode."""
from copy import deepcopy
from collections import Counter
import gzip
import importlib.util
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]; CONTROLS={}
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
previous=module('lexical_setf_analysis',HERE.parent/'target-setf/analysis.py')
def require(x,reason):
    if not x:raise ValueError(reason)
def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def items(x,path=()):
    result=[]
    while x is not None:
        require(isinstance(x,dict) and set(x)=={'cons'} and isinstance(x['cons'],list) and len(x['cons'])==2,'IR_LIST')
        result.append((x['cons'][0],path+('cons',0)));x=x['cons'][1];path+=('cons',1)
    return result
def values(x):return [v for v,p in items(x)]
def functions(f):
    yield f
    for child in f['children']:yield from functions(child)
def observations(f):
    yield f
    for child in f['inner_functions']:yield from observations(child)
def walk(x,path=()):
    yield x,path
    if isinstance(x,dict):
        for k,v in x.items():yield from walk(v,path+(k,))
    elif isinstance(x,list):
        for i,v in enumerate(x):yield from walk(v,path+(i,))
def get(x,path):
    for k in path:x=x[k]
    return x
def put(x,path,value):get(x,path[:-1])[path[-1]]=value
def plist(*xs):
    x=None
    for v in reversed(xs):x={'cons':[v,x]}
    return x
def prefix(a,b):return b[:len(a)]==a
class Unbounded(Exception):pass

def analyze(flow,observation):
    fs=list(functions(flow));obs=list(observations(observation))
    require(len({f['function_id'] for f in fs})==len(fs),'FUNCTION_IDS')
    require([f['function_id'] for f in fs]==[f['function_id'] for f in obs],'FUNCTION_JOIN')
    by_id={f['function_id']:f for f in fs}
    parents={c['function_id']:f['function_id'] for f in fs for c in f['children']}
    for f,o in zip(fs,obs):require(f['name']==o['name'] and parents.get(f['function_id'])==o['parent_id'],'FUNCTION_PARENT')
    nodes={};bindings={};uses={};roles={};calls=[];variables={};operator_names={}
    for f,o in zip(fs,obs):
        owner=f['function_id'];local=[];histogram=Counter()
        for node,path in walk(f['ir']):
            if not isinstance(node,dict):continue
            if 'variable' in node:
                require(set(node)=={'variable','name','assigned'} and type(node['variable'])is int and type(node['assigned'])is bool,'VARIABLE_RECORD')
                require(variables.setdefault(node['variable'],node)==node,'VARIABLE_IDENTITY')
                uses.setdefault(node['variable'],[]).append((owner,path))
            if 'node' not in node:continue
            require(set(node)=={'node','operator','operator_id','operands'} and type(node['node'])is int and type(node['operator_id'])is int,'NODE_RECORD')
            require(operator_names.setdefault(node['operator_id'],node['operator'])==node['operator'],'OPERATOR_IDENTITY')
            histogram[node['operator_id']]+=1
            require(node['node'] not in nodes,'NODE_IDS');nodes[node['node']]=(owner,node,path)
            op=node['operator']
            if isinstance(node['operands'],dict) and node['operands'].get('literal')is True:
                require(node['operands']=={'literal':True} and op in ('CCL::IMMEDIATE','COMMON-LISP::FIXNUM','NIL','COMMON-LISP::T'),'LITERAL_SCOPE');continue
            args=items(node['operands'],path+('operands',))
            if op in ('COMMON-LISP::LET','COMMON-LISP::LET*','COMMON-LISP::FLET'):
                require(len(args)==4,'BINDING_SHAPE');vs=items(*args[0]);initializers=items(*args[1])
                require(len(vs)==len(initializers),'BINDING_ARITY')
                for (var,vp),(init,ip) in zip(vs,initializers):
                    if not isinstance(var,dict) or 'variable' not in var:continue
                    roles[(owner,vp)]='binding'
                    bindings.setdefault(var['variable'],[]).append(dict(owner=owner,node=node['node'],operator=op,variable=var['variable'],initializer=init,initializer_path=ip,body_path=args[2][1]))
            if op in ('CCL::LEXICAL-REFERENCE','CCL::INHERITED-ARG','CCL::SETQ-LEXICAL'):
                require(len(args)==(2 if op=='CCL::SETQ-LEXICAL' else 1),'VARIABLE_SHAPE')
                if isinstance(args[0][0],dict) and 'variable' in args[0][0]:roles[(owner,args[0][1])]='write' if op=='CCL::SETQ-LEXICAL' else 'read'
            if op in ('CCL::CALL','CCL::BUILTIN-CALL','CCL::LEXICAL-FUNCTION-CALL','CCL::SELF-CALL'):local.append(node['node'])
        require(local==[c['site_id'] for c in o['calls']],'CALL_SITE_JOIN')
        require([dict(id=k,count=v) for k,v in sorted(histogram.items())]==o['operators'],'OPERATOR_CENSUS_JOIN')
        calls.extend((owner,c) for c in o['calls'])
    def resolve(expr,owner,use_path,seen=()):
        if not isinstance(expr,dict):raise Unbounded('non-function-initializer')
        op=expr.get('operator')
        if op in ('CCL::TYPED-FORM','CCL::TYPE-ASSERTED-FORM'):
            a=items(expr['operands'],use_path+('operands',))
            if len(a) not in (2,3):raise Unbounded('unsupported-type-wrapper')
            return resolve(a[1][0],owner,a[1][1],seen)
        if op in ('CCL::SIMPLE-FUNCTION','CCL::CLOSED-FUNCTION'):
            a=values(expr['operands'])
            if len(a)!=1 or not isinstance(a[0],dict) or set(a[0])!={'function'}:raise Unbounded('function-shape')
            target=a[0]['function']
            if target not in by_id or parents.get(target)!=owner:raise Unbounded('function-outside-owner')
            return target,[]
        if op not in ('CCL::LEXICAL-REFERENCE','CCL::INHERITED-ARG'):raise Unbounded('non-lexical-initializer')
        a=values(expr['operands'])
        if len(a)!=1 or not isinstance(a[0],dict) or 'variable' not in a[0]:raise Unbounded('variable-shape')
        var=a[0]['variable']
        if var in seen:raise Unbounded('binding-cycle')
        definitions=bindings.get(var,[])
        if len(definitions)!=1:raise Unbounded('nonunique-or-absent-binding')
        b=definitions[0]
        if b['owner']!=owner or not prefix(b['body_path'],use_path):raise Unbounded('outside-binding-body')
        # Scan the entire lexical family, including captured writes in children.
        rs=[roles.get(pos,'unknown') for pos in uses[var]]
        if variables[var]['assigned'] or 'write' in rs:raise Unbounded('assigned-variable')
        if 'unknown' in rs:raise Unbounded('unclassified-variable-use')
        if b['operator']=='COMMON-LISP::FLET':
            init=b['initializer']
            if not isinstance(init,dict) or set(init)!={'function'}:raise Unbounded('flet-initializer')
            target=init['function'];chain=[]
            if target not in by_id or parents.get(target)!=owner:raise Unbounded('function-outside-owner')
        else:target,chain=resolve(b['initializer'],owner,b['initializer_path'],seen+(var,))
        return target,[dict(variable_id=var,binding_node=b['node'],operator=b['operator'])]+chain
    result=[]
    for owner,call in calls:
        if call['dependency']['category']!='function-variable':continue
        _,node,path=nodes[call['site_id']];args=items(node['operands'],path+('operands',))
        require(node['operator']=='CCL::CALL' and len(args)==3,'COMPUTED_CALL_SHAPE')
        expr,ep=args[0];ref=expr
        while ref.get('operator') in ('CCL::TYPED-FORM','CCL::TYPE-ASSERTED-FORM'):ref=values(ref['operands'])[1]
        require(ref.get('operator') in ('CCL::LEXICAL-REFERENCE','CCL::INHERITED-ARG') and values(ref['operands'])[0]['variable']==call['dependency']['variable_id'],'CALLEE_VARIABLE_JOIN')
        row=dict(function_id=owner,call_site=call['site_id'],variable_id=call['dependency']['variable_id'])
        try:
            target,chain=resolve(expr,owner,ep);row.update(disposition='BOUNDED_LEXICAL_PROTOTYPE',targets=[target],bindings=chain)
        except Unbounded as e:row.update(disposition='UNRESOLVED',targets=[],reason=str(e))
        result.append(row)
    return result

SOURCES=[('compiler/nx-basic.lisp:26548','COMMON-LISP::DECLAIM',4,'NIL',1),('compiler/optimizers.lisp:13586','COMMON-LISP::APPLY',135,'CCL::QUOTIFY',2)]
PROBES={'literal':True,'flet':True,'parameter':False,'assigned':False,'captured-write':False,'shadowed':True,'closed':True,'sequential-scope':False}
def check(c,t):
    previous.check(c['setf'],t)
    flow=c['flow'];require(flow['version']==1 and flow['observer_restored']is True and flow['nonlocal_observer_restored']is True and flow['ir_modified']is False and flow['global_definitions_changed']is False,'SCOPE')
    require([r['source'] for r in flow['records']]==[s[0] for s in SOURCES],'SOURCE_RECORD_BOUND')
    for r,(source,op,event,name,depth) in zip(flow['records'],SOURCES):
        src=r['source_record'];text=(ROOT/src['path']).read_text()
        require(src['key']==source and source==src['path']+':'+str(src['start']) and
                text[src['start']:src['end']]==src['text'] and previous.previous.form_end(text,src['start'])==src['end'],'SOURCE_SPAN')
        previous.traversal.base.context(src['reader'])
        actual=c['setf']['events'][event]
        require(actual['operator']==op and actual['source']==source and actual['selected_id']==r['native_function_id'],'EXPANDER_IDENTITY_JOIN')
        rows=analyze(r['flow'],r['observation'])
        require(len(rows)==1 and rows[0]['disposition']=='BOUNDED_LEXICAL_PROTOTYPE','SOURCE_CALLBACK_UNBOUNDED')
        row=rows[0];target=next(f for f in functions(r['flow']) if f['function_id']==row['targets'][0])
        require(target['name']==name and len(row['bindings'])==depth,'SOURCE_BINDING_CHAIN')
    require([p['name'] for p in flow['probes']]==list(PROBES),'PROBE_BOUND')
    for p in flow['probes']:
        rows=analyze(p['flow'],p['observation'])
        require(len(rows)==1 and (rows[0]['disposition']=='BOUNDED_LEXICAL_PROTOTYPE')==PROBES[p['name']],'PROBE_DISPOSITION '+p['name'])
    return dict(source_callbacks_bound=2,lexical_binding_steps=3,native_probe_cases=len(PROBES),bounded_probes=sum(PROBES.values()),unresolved_probes=len(PROBES)-sum(PROBES.values()),graph_edges_replaced=0,macro_environment_qualified=False)
def joins(c):return [dict(source=r['source'],bounds=analyze(r['flow'],r['observation'])) for r in c['flow']['records']]
def controls(c,t):
    results=[]
    def trial(name,edit,reason,rehist=False):
        changed=deepcopy(c);edit(changed)
        if rehist:
            # As with rebinding a damaged payload hash, update the auxiliary
            # histogram so these cases exercise the semantic bound itself.
            for r in changed['flow']['records']:
                for f,o in zip(functions(r['flow']),observations(r['observation'])):
                    hist=Counter(v['operator_id'] for v,p in walk(f['ir']) if isinstance(v,dict) and 'node'in v)
                    o['operators']=[dict(id=k,count=v) for k,v in sorted(hist.items())]
        try:check(changed,t)
        except ValueError as e:require(str(e)==reason,'CONTROL_REASON '+name+': '+str(e))
        else:raise ValueError('CONTROL_ESCAPED '+name)
        results.append(dict(name=name,status='REJECTED',reason=reason,histogram_rebound=rehist))
    def rec(x,i=0):return x['flow']['records'][i]
    def node(r,ident):return next(v for v,p in walk(r['flow']) if isinstance(v,dict) and v.get('node')==ident)
    first=joins(c)[0]['bounds'][0];second=joins(c)[1]['bounds'][0]
    def binder(x,i=0,step=0):
        row=first if i==0 else second
        return node(rec(x,i),row['bindings'][step]['binding_node'])
    def flag(x):
        for v,p in walk(rec(x)['flow']):
            if isinstance(v,dict) and v.get('variable')==first['variable_id']:v['assigned']=True
    def shift_scope(x):
        b=binder(x);a=items(b['operands']);vs=items(a[0][0]);inits=items(a[1][0],a[1][1])
        i=next(i for i,(v,p) in enumerate(vs) if v['variable']==first['variable_id'])
        body,bp=a[2];init,ip=inits[i]
        put(b['operands'],ip,body);put(b['operands'],bp,init)
    def alias_external(x):
        b=binder(x,1);a=values(b['operands']);vs=values(a[0]);inits=values(a[1]);i=next(i for i,v in enumerate(vs) if v['variable']==second['variable_id'])
        ref=values(inits[i]['operands'])[0];ref.update(variable=999999,name='#::EXTERNAL',assigned=False)
    def target_outside(x):
        b=binder(x,1,1);target=values(values(b['operands'])[1])[0];target['function']=rec(x,1)['flow']['function_id']
    def extra_binding(x):
        b=binder(x);vs=values(values(b['operands'])[0]);chosen=next(v for v in vs if v['variable']==first['variable_id']);vs[0].clear();vs[0].update(chosen)
    def hidden_use(x):
        r=rec(x);b=binder(x);a=values(b['operands']);init=values(a[1])[0]
        # CONS's operand now carries a raw var instead of an expression.
        init['operands']['cons'][0]=deepcopy(next(v for v in values(a[0]) if v['variable']==first['variable_id']))
    def write_without_flag(x,nested=False):
        r=rec(x);b=binder(x);var=deepcopy(next(v for v in values(values(b['operands'])[0]) if v['variable']==first['variable_id']))
        writes=[v for v,p in walk(r['flow']['ir']) if isinstance(v,dict) and v.get('operator')=='CCL::SETQ-LEXICAL']
        if nested:
            dest=next(v for v,p in walk(r['flow']['children'][0]['ir']) if isinstance(v,dict) and v.get('operator')=='COMMON-LISP::LIST')
            body=values(values(dest['operands'])[0])[-1]
            dest['operands']=plist(var,body)
            dest['operator']='CCL::SETQ-LEXICAL';dest['operator_id']=writes[0]['operator_id']
        else:dest=writes[0]
        dest['operands']['cons'][0]=var
    trial('missing-source-record',lambda x:x['flow']['records'].pop(),'SOURCE_RECORD_BOUND')
    trial('surplus-source-record',lambda x:x['flow']['records'].append(deepcopy(rec(x))),'SOURCE_RECORD_BOUND')
    trial('wrong-source-span',lambda x:rec(x)['source_record'].__setitem__('end',1),'SOURCE_SPAN')
    trial('wrong-expander-identity',lambda x:rec(x).__setitem__('native_function_id',0),'EXPANDER_IDENTITY_JOIN')
    trial('function-identity',lambda x:rec(x)['flow'].__setitem__('function_id',0),'FUNCTION_JOIN')
    trial('function-parent',lambda x:rec(x)['observation']['inner_functions'][0].__setitem__('parent_id',0),'FUNCTION_PARENT')
    trial('missing-call',lambda x:rec(x)['observation']['calls'].pop(),'CALL_SITE_JOIN')
    trial('callee-variable',lambda x:rec(x)['observation']['calls'][-1]['dependency'].__setitem__('variable_id',0),'CALLEE_VARIABLE_JOIN')
    trial('histogram',lambda x:rec(x)['observation']['operators'][0].__setitem__('count',0),'OPERATOR_CENSUS_JOIN')
    trial('compiler-assignment-flag',flag,'SOURCE_CALLBACK_UNBOUNDED')
    trial('outside-binding-body',shift_scope,'SOURCE_CALLBACK_UNBOUNDED')
    trial('unbound-alias',alias_external,'SOURCE_CALLBACK_UNBOUNDED')
    trial('wrong-function-owner',target_outside,'SOURCE_CALLBACK_UNBOUNDED')
    trial('duplicate-binding',extra_binding,'SOURCE_CALLBACK_UNBOUNDED')
    trial('unclassified-variable-use',hidden_use,'SOURCE_CALLBACK_UNBOUNDED',True)
    trial('write-with-clear-compiler-flag',write_without_flag,'SOURCE_CALLBACK_UNBOUNDED')
    trial('nested-write-with-clear-compiler-flag',lambda x:write_without_flag(x,True),'SOURCE_CALLBACK_UNBOUNDED',True)
    trial('missing-probe',lambda x:x['flow']['probes'].pop(),'PROBE_BOUND')
    trial('false-restoration',lambda x:x['flow'].__setitem__('observer_restored',False),'SCOPE')
    trial('false-nonlocal-restoration',lambda x:x['flow'].__setitem__('nonlocal_observer_restored',False),'SCOPE')
    trial('ir-edit-claim',lambda x:x['flow'].__setitem__('ir_modified',True),'SCOPE')
    return results
