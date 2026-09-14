"""Focused refusals on retained IR, callback probes and actual graph records."""
from copy import deepcopy
from flow import convert, extract, functions, require, analyze
from links import make, check, key


def old_format(record):
    """Quarantined format conversion: deliberately cannot carry assignment bits."""
    family={f['function_id']:f for f in functions(record['function'])}
    source=record['flow']; nodes={}; names={}; next_id=max(n['id'] for n in source['objects'])+100000
    def symbol(label,ident=None):
        nonlocal next_id
        if ident is None:
            if label in names:return {'ref':names[label]}
            ident=next_id;next_id+=1;names[label]=ident
        package,name=label.split('::',1)
        nodes[ident]=dict(id=ident,kind='symbol',package=package,name=name,setter_of=None)
        return {'ref':ident}
    def ref(x):
        if x is None:return {'atom':'nil'}
        if isinstance(x,int):return {'integer':x}
        if isinstance(x,str):return {'string':x}
        if 'ref' in x:return x
        return symbol(x['symbol'],x['identity'])
    operators={}
    for n in source['objects']:
        i=n['id'];kind=n['kind']
        if kind=='function':
            nodes[i]=dict(id=i,kind='afunc',name={'string':n['name']},parent=family[i]['parent_id'],
                          body=ref(n['body']),children=n['children'],function=None)
        elif kind=='acode':
            operators[n['operator_id']]=n['operator']
            nodes[i]=dict(id=i,kind=kind,operator=n['operator_id'],operator_id=n['operator_id'],
                          operands=ref(n['operands']),expanded=True)
        elif kind=='cons':nodes[i]=dict(id=i,kind=kind,car=ref(n['car']),cdr=ref(n['cdr']),expanded=True)
        elif kind=='variable':nodes[i]=dict(id=i,kind=kind,name=symbol(n['name']),root=n['root'])
        elif kind in ('native-function','capture-guard'):
            nodes[i]=dict(id=i,kind='function',code=n['function_id'],description={'name':n['name']})
        else:nodes[i]=dict(id=i,kind='opaque',type=n['type'])
    return dict(function=record['function'],ir=dict(root={'ref':source['root']},objects=list(nodes.values()))),operators


def run(samples, callback_capture, base, fs, calls, base_sha):
    rows=[]
    def trial(name,value,mutate,checker,reason):
        changed=deepcopy(value);mutate(changed)
        try:checker(changed)
        except ValueError as e:require(str(e)==reason,'CONTROL_REASON '+name+': '+str(e))
        else:raise ValueError('CONTROL_ESCAPED '+name)
        rows.append(dict(name=name,status='REJECTED',reason=reason))
    samples={k:dict(v,operators={int(i):n for i,n in v['operators'].items()},
                    builtins={int(i):n for i,n in v['builtins'].items()}) for k,v in samples.items()}
    def rawcheck(s):return extract(s['row']['payload'],s['operators'],s['builtins'])
    for label,s in samples.items():
        _,cs=rawcheck(s)
        if label.startswith('COMMON-LISP::'):
            require(any(c.get('lexical_bound',{}).get('targets') for c in cs),'SAMPLE_BOUND')
        else:require(any(c.get('lexical_bound',{}).get('reason')==label for c in cs),'SAMPLE_REFUSAL')
    s=samples['COMMON-LISP::LET*']
    def objects(s):return s['row']['payload']['ir']['objects']
    trial('duplicate-ir-object',s,lambda s:objects(s).append(deepcopy(objects(s)[0])),rawcheck,'RICH_DUPLICATE_NODE')
    trial('surplus-ir-object',s,lambda s:objects(s).append(dict(id=-1,kind='symbol',name='EXTRA',package='KEYWORD',setter_of=None)),rawcheck,'RICH_SURPLUS_NODE')
    trial('omit-ir-root',s,lambda s:objects(s).pop(0),rawcheck,'RICH_DANGLING')
    trial('substitute-root',s,lambda s:s['row']['payload']['ir'].__setitem__('root',{'ref':-1}),rawcheck,'RICH_ROOT')
    trial('shallow-executable',s,lambda s:next(n for n in objects(s)if n['kind']=='acode').__setitem__('expanded',False),rawcheck,'RICH_SHALLOW_EXECUTABLE')
    trial('encoded-operator-mismatch',s,lambda s:next(n for n in objects(s)if n['kind']=='acode').__setitem__('operator',-1),rawcheck,'RICH_OPERATOR')
    trial('wrong-parent',s,lambda s:objects(s)[0].__setitem__('parent',-1),rawcheck,'RICH_PARENT')
    def observation_calls(s):
        return [c for f in functions(s['row']['payload']['function'])for c in f['calls']]
    lexical=next(s for s in samples.values() if any(c['dependency']['category'] in ('lexical','self') for c in observation_calls(s)))
    def wrong_lexical(s):
        c=next(c for c in observation_calls(s)if c['dependency']['category'] in ('lexical','self'))
        c['dependency']['targets'][0]['id']=-1
    trial('wrong-direct-callee',lexical,wrong_lexical,rawcheck,'DIRECT_FUNCTION_ID')
    builtin=next(s for s in samples.values() if any(c['dependency']['category']=='builtin' for c in observation_calls(s)))
    def wrong_builtin(s):
        c=next(c for c in observation_calls(s)if c['dependency']['category']=='builtin')
        c['dependency']['targets'][0]['name']='WRONG'
    trial('wrong-builtin-binding',builtin,wrong_builtin,rawcheck,'BUILTIN_BINDING')
    # Reuse the reviewed eight native-capture probes. Only the serialization is
    # changed here, and assignment bits are absent in every converted record.
    expected={'CENSUS-LITERAL':True,'CENSUS-FLET':True,'CENSUS-PARAMETER':False,'CENSUS-ASSIGNED':False,
              'CENSUS-CAPTURED-WRITE':False,'CENSUS-SHADOWED':True,'CENSUS-CLOSED':True,'CENSUS-SEQUENTIAL-SCOPE':False}
    probes=[]
    for r in callback_capture['captures']:
        payload,operators=old_format(r); converted=convert(payload,operators)
        got=analyze(converted);original=analyze(r)
        require(got==original,'CALLBACK_CONVERSION_CHANGED_BOUND')
        family={f['function_id']:f['name'] for f in functions(r['function'])}
        for b in got:
            name=family[b['function_id']].removeprefix('COMMON-LISP-USER::')
            require(name in expected and bool(b['targets'])==expected.pop(name),'CALLBACK_EXPECTATION '+name)
            probes.append(dict(name=name,disposition=b['disposition'],targets=b['targets']))
    require(not expected and len(probes)==8,'CALLBACK_POPULATION')
    # A small quarantine projection of genuine rows covers the integration
    # controls. The full graph is checked once by project(), not copied 14 times.
    selected=[]
    for pred in (lambda c:bool(c.get('lexical_bound',{}).get('targets')),
                 lambda c:c['dependency']['category']=='self',
                 lambda c:c['dependency']['category']=='global-binding',
                 lambda c:c['dependency']['category']=='computed-callee'):
        selected.append(next(c for c in calls if pred(c)))
    ids={c['function_id'] for c in selected}
    for c in selected:
        ids.update(t['id'] for t in c['dependency']['targets']if t['kind']=='function')
        ids.update(c.get('lexical_bound',{}).get('targets',[]))
    bypass=next(f for f in fs if f['basis']=='frontend'); ids.add(bypass['function_id'])
    smallfs=[f for f in fs if f['function_id'] in ids]
    keep={key('afunc',i) for i in ids}|{key('code',c['code'])for f in smallfs for c in f['emitted']}
    smallbase={'nodes':[n for n in base['nodes']if n['id'] in keep],
               'seeds':[key('afunc',i)for i in sorted(ids)]}
    delta=make(smallbase,smallfs,selected,base_sha)
    checker=lambda d:check(d,smallbase,smallfs,selected,base_sha)
    checker(delta)
    def call_edge(d):return next(e for e in d['edges']if e['evidence'].startswith('build-flow/call/') and e['resolution']=='complete')
    trial('drop-call-edge',delta,lambda d:d['edges'].remove(call_edge(d)),checker,'FRAGMENT_EDGE_RECORDS')
    trial('duplicate-call-edge',delta,lambda d:d['edges'].append(deepcopy(call_edge(d))),checker,'FRAGMENT_EDGE_RECORDS')
    trial('cross-process-target',delta,lambda d:call_edge(d).__setitem__('targets',['compiled:1']),checker,'CROSS_PROCESS_EDGE')
    trial('invent-complete-global-bound',delta,lambda d:next(e for e in d['edges']if e['resolution']=='unresolved').__setitem__('resolution','complete'),checker,'FRAGMENT_EDGE_RECORDS')
    trial('invent-implemented-function',delta,lambda d:d['nodes'].append(dict(d['nodes'][0],id='identity:build:afunc:invented')),checker,'FRAGMENT_NODE_RECORDS')
    trial('alter-node-description',delta,lambda d:d['nodes'][0].__setitem__('reason','complete'),checker,'FRAGMENT_NODE_RECORDS')
    trial('erase-assembly-gap',delta,lambda d:d['nodes'].remove(next(n for n in d['nodes']if ':flow-assembly:' in n['id'])),checker,'FRAGMENT_NODE_RECORDS')
    trial('wrong-materialized-edge',delta,lambda d:next(e for e in d['edges']if e['evidence'].startswith('build-flow/materialized/')).__setitem__('targets',[]),checker,'FRAGMENT_EDGE_RECORDS')
    trial('wrong-edge-phase',delta,lambda d:call_edge(d).__setitem__('phase','load'),checker,'FRAGMENT_EDGE_RECORDS')
    trial('claim-gate-credit',delta,lambda d:d.__setitem__('census_gate_credit',True),checker,'FRAGMENT_SCOPE')
    trial('change-base-identity',delta,lambda d:d.__setitem__('base_sha256','0'*64),checker,'FRAGMENT_SCOPE')
    trial('duplicate-target',delta,lambda d:call_edge(d)['targets'].append(call_edge(d)['targets'][0]),checker,'FRAGMENT_TARGET_SET')
    trial('conceal-unattached-function',delta,lambda d:d['unattached_functions'].append(-1),checker,'UNATTACHED_FUNCTION_SET')
    return dict(controls=rows,controls_rejected=len(rows),callback_probes=probes,
                native_capture_reused=True,assignment_bits_carried=False)
