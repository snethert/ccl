"""Decode native wrapper witnesses and add their exact dependencies."""
from collections import Counter
from copy import deepcopy
import hashlib
import json

DISPATCH_WORD = 0xc9cd0000000000  # raw target word in pinned U1 xdump/xx8664-fasload.lisp
DISPATCH_VALUE = DISPATCH_WORD >> 3  # xload-set stores raw bits; Lisp reads a tagged fixnum
TESTS = ['S0-LL15-b', 'S0-LL15-c']
SCOPE = 'Native wrapper contents and current front-end handler identities; no historical handler execution or complete callable-body closure.'


def canonical(x): return json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
def key(i): return 'boot:object:' + str(i)
def require(ok, reason):
    if not ok: raise ValueError(reason)


def validate_capture(data, legacy, limit):
    require(set(data) == {'version','legacy_identity_limit','identity_limit','descriptor_time','dispatch_value','handler_table','wrappers','oracle','objects','raw_dispatch_word','fixnum_shift'}, 'CAPTURE_FIELDS')
    require(data['version']==1 and data['legacy_identity_limit']==limit, 'LEGACY_IDENTITY_LIMIT')
    require(data['descriptor_time']=='Retained image after boot handoff; no historical mutation or handler-execution claim.', 'DESCRIPTOR_TIME')
    require(data['dispatch_value']==DISPATCH_VALUE and data['raw_dispatch_word']==DISPATCH_WORD and data['fixnum_shift']==3, 'DISPATCH_WORD')
    require(type(data['identity_limit']) is int and data['identity_limit']>=limit, 'IDENTITY_LIMIT')
    objects={r['id']:r for r in data['objects']}; original={r['id']:r for r in legacy['objects']}
    values={r[k] for r in legacy['bindings'] for k in ('old','new')}
    opaque={i for i in values if original[i]['kind']=='opaque'}
    require(len(objects)==len(data['objects']), 'DUPLICATE_OBJECT')
    wrappers={r['id']:r for r in data['wrappers']}; oracle={r['wrapper']:r for r in data['oracle']}
    require(set(wrappers)==opaque and len(wrappers)==len(data['wrappers']), 'WRAPPER_COVERAGE')
    require(set(oracle)==opaque and len(oracle)==len(data['oracle']), 'ORACLE_COVERAGE')
    require(type(data['handler_table']) is int and limit<data['handler_table']<=data['identity_limit'] and data['handler_table'] not in objects, 'HANDLER_TABLE_ID')
    referenced=set()
    for i,r in wrappers.items():
        require(set(r)=={'id','kind','dispatch_value','payload','handler'}, 'WRAPPER_FIELDS')
        require(original[i]['type']=='(COMMON-LISP:SIMPLE-VECTOR 2)', 'LEGACY_WRAPPER_LAYOUT')
        require(r['kind'] in ('macro-wrapper','special-wrapper'), 'WRAPPER_KIND')
        require(r['dispatch_value']==DISPATCH_VALUE, 'WRAPPER_DISPATCH')
        ismacro=r['kind']=='macro-wrapper'
        expected={'wrapper':i,'slot0':r['dispatch_value'],'slot1':r['payload'],
                  'slot1_kind':'function' if ismacro else 'symbol','handler':r['handler']}
        require(oracle[i]==expected, 'SLOT_ORACLE')
        require(r['payload'] in objects and objects[r['payload']]['kind']==expected['slot1_kind'], 'PAYLOAD_OBJECT')
        referenced.add(r['payload'])
        if ismacro: require(r['handler'] is None, 'MACRO_HANDLER')
        else:
            require(r['handler'] in objects and objects[r['handler']]['kind']=='function', 'SPECIAL_HANDLER')
            referenced.add(r['handler'])
    require(set(objects)==referenced, 'OBJECT_COVERAGE')
    for i,r in objects.items():
        require(type(i) is int and 0<i<=data['identity_limit'], 'OBJECT_ID')
        if i in original: require(r==original[i], 'LEGACY_OBJECT_IDENTITY')
        if r['kind']=='function':
            require(set(r)=={'id','kind','code','name','source','position'}, 'FUNCTION_FIELDS')
            require(type(r['code']) is int and 0<r['code']<=data['identity_limit'], 'FUNCTION_CODE_ID')
            require(isinstance(r['name'],str) and (r['source'] is None or isinstance(r['source'],str)) and
                    (r['position'] is None or type(r['position']) is int), 'FUNCTION_METADATA')
        else:
            require(set(r)=={'id','kind','name','package'} and r['kind']=='symbol' and isinstance(r['name'],str) and
                    (r['package'] is None or isinstance(r['package'],str)), 'SYMBOL_FIELDS')
    return {'wrappers':len(wrappers),'macro_wrappers':sum(r['kind']=='macro-wrapper' for r in wrappers.values()),
            'special_wrappers':sum(r['kind']=='special-wrapper' for r in wrappers.values()),
            'function_identities':sum(r['kind']=='function' for r in objects.values()),
            'new_function_descriptions':sum(r['kind']=='function' and i not in original for i,r in objects.items()),
            'remaining_opaque_wrappers':0}


def record(i, kind, impl, evidence, reason):
    return dict(id=i,kind=kind,disposition='implemented',required=True,implementation=impl,
                evidence=evidence,reason=reason,tests=TESTS)


def relation(source,target,phase,label):
    return {'from':source,'targets':[target],'phase':phase,'origin':'observed','resolution':'complete','evidence':'boot/wrappers/'+label}


def project(base,data,binding):
    prior={r['id']:r for r in base['nodes']};nodes={};replacements=[];edges=[]
    trap='boot:wrapper-dispatch';table='boot:wrapper-handler-table:'+str(data['handler_table'])
    nodes[trap]=record(trap,'trap','Recorded native macro/special application trap','boot/wrappers/dispatch',str(DISPATCH_WORD))
    nodes[table]=record(table,'store','Observed *nx1-alphatizers* table identity','boot/wrappers/handler-table',str(data['handler_table']))
    for r in data['objects']:
        i=key(r['id']) if r['kind']=='function' else 'boot:special-operator:'+str(r['id'])
        n=record(i,'function' if r['kind']=='function' else 'operator',
                 'Recorded native function identity' if r['kind']=='function' else 'Recorded native special-operator marker',
                 'boot/objects/'+str(r['id']) if r['kind']=='function' else 'boot/wrappers/symbol/'+str(r['id']),canonical(r))
        if i in prior: require(prior[i]==n,'EXISTING_FUNCTION_RECORD')
        else:nodes[i]=n
    for r in data['wrappers']:
        i=key(r['id']);before=prior[i]
        require(before['disposition']=='unresolved' and before['kind']=='store' and before['implementation'] is None,'WRAPPER_BASE_STATE')
        after={**before,'disposition':'implemented','implementation':'Recorded native '+r['kind']+' identity',
               'evidence':'boot/wrappers/value/'+str(r['id']),'reason':canonical(r)}
        replacements.append({'before':before,'after':after})
        edges.append(relation(i,trap,'run','dispatch/'+str(r['id'])))
        if r['kind']=='macro-wrapper':edges.append(relation(i,key(r['payload']),'macroexpand','expander/'+str(r['id'])))
        else:
            symbol='boot:special-operator:'+str(r['payload'])
            edges += [relation(i,symbol,'compile','marker/'+str(r['id'])),
                      relation(symbol,key(r['handler']),'compile','handler/'+str(r['id'])),
                      relation(symbol,table,'compile','handler-table/'+str(r['id']))]
    gap=prior['boot:gap:closure'];updated={**gap,'reason':'Full target traversal, callable bodies and Wasm dispositions remain unqualified.'}
    replacements.append({'before':gap,'after':updated})
    return {'version':1,'scope':SCOPE,'input_binding':binding,'nodes':[nodes[i] for i in sorted(nodes)],
            'replacements':replacements,'edges':edges}


def apply(base,patch):
    changes={r['before']['id']:r for r in patch['replacements']}
    require(len(changes)==len(patch['replacements']),'DUPLICATE_REPLACEMENT')
    result=dict(base);result['nodes']=[]
    for n in base['nodes']:
        change=changes.get(n['id'])
        if change:require(change['before']==n,'REPLACEMENT_PRECONDITION')
        result['nodes'].append(change['after'] if change else n)
    result['nodes']+=patch['nodes'];result['edges']=base['edges']+patch['edges']
    result['profile']+='; decoded native macro/special wrappers'
    result['inputs_sha256']=hashlib.sha256(canonical({'base':base['inputs_sha256'],'wrapper_binding':patch['input_binding']}).encode()).hexdigest()
    return result
