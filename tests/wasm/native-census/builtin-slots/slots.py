"""Index-addressed native operations, with separate unresolved target obligations."""
from collections import Counter, defaultdict
import hashlib
import re
from urllib.parse import quote

from support import require

SCOPE = ('Original-build builtin operand slots; native source routes are interpretation '
         'witnesses only. No target lowering, function-cell identity or callable bound is qualified.')
PREFIX = 'identity:build:builtin-slot:'


def source_span(path, raw, start, end):
    return dict(path=path, byte_offset=start, byte_end=end,
                line=raw[:start].count(b'\n')+1,
                sha256=hashlib.sha256(raw[start:end]).hexdigest())


def native_routes(samples, sources):
    """Read the reviewed same-build table and the pinned U1 routing declarations.

    This is deliberately a bounded source decoder, not a Lisp evaluator or a
    native emission witness. All executable source files are separately pinned.
    """
    tables=[s['builtins'] for s in samples.values()]
    require(tables and all(t==tables[0] for t in tables), 'SNAPSHOT_TABLE_AGREEMENT')
    table={int(k):v for k,v in tables[0].items()}
    require(set(table)==set(range(23)), 'BUILTIN_SLOT_COVERAGE')
    path='xdump/xfasload.lisp'; raw=sources[path]
    match=re.search(rb'\(defparameter %builtin-functions%\s+#\((.*?)\)\s+"Symbols naming',raw,re.S)
    require(match is not None, 'U1_BUILTIN_VECTOR')
    tokens=re.sub(rb';[^\n]*', b'',match[1]).split()
    require([t.decode().upper() for t in tokens]==[table[i].rsplit('::',1)[1] for i in range(23)],
            'U1_BUILTIN_ORDER')
    vector=source_span(path,raw,match.start(),match.end())
    path='compiler/X86/X8664/x8664-arch.lisp';raw=sources[path]
    require(raw.count(b':primitive->subprims `(((0 . 23) . ,(ccl::%subprim-name->offset '\
                      b"'.SPbuiltin-plus x8664::*x8664-subprims*)))")==1,
            'U1_PRIMITIVE_RANGE')
    start=raw.index(b'(defx8664subprim .SPbuiltin-plus)')
    end=raw.index(b'(defx8664subprim .SPbreakpoint)',start)
    names=re.findall(rb'\(defx8664subprim (\.SPbuiltin-[a-z0-9]+)\)',raw[start:end])
    require(len(names)==23, 'U1_SUBPRIMITIVE_ORDER')
    declaration=source_span(path,raw,start,end)
    path='lisp-kernel/x86-spentry64.s';raw=sources[path];result=[]
    for i,sp in enumerate(names):
        entry=sp.decode().removeprefix('.SP').replace('-','_')
        begin=('_spentry('+entry+')').encode()
        require(raw.count(begin)==1, 'U1_SUBPRIMITIVE_BODY')
        start=raw.index(begin)
        following=re.search(rb'^_spentry\(',raw[start+len(begin):],re.M)
        require(following is not None, 'U1_SUBPRIMITIVE_BODY')
        end=start+len(begin)+following.start()
        result.append(dict(index=i,name=table[i],native_subprimitive=sp.decode(),
                           native_entry=entry,native_body=source_span(path,raw,start,end),
                           span_boundary='next _spentry source label; not assembled code size',
                           native_builtin_fallback_syntax=b'jump_builtin(' in raw[start:end]))
    return dict(scope='Pinned U1 source routing, not observed per-site emission or target implementation.',
                vector=vector,subprimitive_order=declaration,slots=result)


def evidence(c): return f'build-flow/call/{c["function_id"]}/{c["site_id"]}'
def owner(c): return 'identity:build:afunc:'+str(c['function_id'])
def placeholder(name): return 'identity:build:flow-binding:'+quote(name,safe='/@.-_')


def partition(calls, functions, base):
    fs={f['function_id']:f for f in functions}
    require(len(fs)==len(functions), 'FUNCTION_IDENTITIES')
    edges={e['evidence']:e for e in base['edges'] if e['evidence'].startswith('build-flow/call/')}
    keys=[evidence(c) for c in calls]
    require(len(set(keys))==len(keys) and set(keys)==edges.keys(), 'CALL_EDGE_COVERAGE')
    builtins=[];computed=[];categories=Counter();other_unresolved=[]
    for c in calls:
        ev=evidence(c);e=edges[ev];d=c['dependency'];categories[d['category']]+=1
        f=fs[c['function_id']]
        require(f['event']==c['event'] and e['from']==owner(c), 'CALL_CONTEXT')
        if d['category']=='builtin':
            require(set(d)=={'category','builtin_index','targets'} and type(d['builtin_index']) is int
                    and len(d['targets'])==1 and d['targets'][0]['kind']=='global-binding', 'BUILTIN_OPERAND')
            require(e=={'from':owner(c),'targets':[placeholder(d['targets'][0]['name'])],
                        'phase':'run','origin':'conservative','resolution':'unresolved','evidence':ev},
                    'ORIGINAL_BUILTIN_EDGE')
            builtins.append(dict(call=c,source=f['source'],source_position=f['source_position'],
                                 process=f['process'],evidence=ev))
        elif e['resolution']=='unresolved':
            if d['category'] in ('function-variable','computed-callee'):computed.append(ev)
            else:other_unresolved.append(ev)
    require(not other_unresolved, 'UNNAMED_CALL_POPULATION')
    require(len(builtins)==1500 and len(computed)==1562 and len(calls)==103393, 'REVIEWED_CALL_POPULATION')
    return builtins,computed,dict(sorted(categories.items()))


def facts(calls, functions, base, routes, obligations):
    selected,computed,categories=partition(calls,functions,base)
    table={r['index']:r for r in routes['slots']};grouped=defaultdict(list)
    for row in selected:
        c=row['call'];d=c['dependency'];index=d['builtin_index']
        require(index in table and d['targets']==[dict(kind='global-binding',name=table[index]['name'])],
                'CALL_SLOT_NAME')
        grouped[index].append(row)
    require(set(grouped)=={r['index'] for r in obligations['slots']} and
            len(obligations['slots'])==len(grouped), 'OBLIGATION_SLOT_SET')
    spec={r['index']:r for r in obligations['slots']};slots=[]
    for index,rows in sorted(grouped.items()):
        require(spec[index]['name']==table[index]['name'] and spec[index]['status']=='UNIMPLEMENTED'
                and spec[index]['required_work'], 'OBLIGATION_QUALIFICATION')
        slots.append(dict(index=index,node=PREFIX+str(index),name=table[index]['name'],
                          call_sites=sorted(rows,key=lambda r:(r['call']['function_id'],r['call']['site_id'])),
                          native_source=table[index],target=spec[index],
                          callable_identity='NOT_OBSERVED_BY_BUILTIN_TABLE',target_lowering='UNQUALIFIED'))
    return dict(version=1,scope=SCOPE,census_gate_credit=False,slots=slots,
                call_categories=categories,open_computed_evidence=sorted(computed),
                original_unresolved_call_edges=len(selected)+len(computed),
                builtin_call_sites=len(selected),open_computed_sites=len(computed),
                target_lowerings_qualified=0,native_routes=routes)


def node(slot):
    return dict(id=slot['node'],kind='operator',required=True,disposition='unresolved',implementation=None,
                reason=f'Builtin operand {slot["index"]} ({slot["name"]}); target lowering and its dependencies remain unqualified.',
                evidence='builtin-slots/slot/'+str(slot['index']),tests=['S0-LL15-b','S0-LL15-c'])


def gap(slot):
    return {'from':slot['node'],'targets':[placeholder(slot['name'])],'phase':'run',
            'origin':'conservative','resolution':'unresolved','evidence':'builtin-slots/unqualified/'+str(slot['index'])}


def delta(f):
    replacements=[]
    for s in f['slots']:
        for row in s['call_sites']:
            c=row['call']
            replacements.append({'from':owner(c),'targets':[s['node']],'phase':'run',
                                 'origin':'conservative','resolution':'complete','evidence':evidence(c)})
    return dict(version=1,scope=SCOPE,census_gate_credit=False,target_lowerings_qualified=0,
                nodes=[node(s) for s in f['slots']],edges=[gap(s) for s in f['slots']],
                replacements=sorted(replacements,key=lambda e:e['evidence']))


def apply(base, patch):
    replacements={e['evidence']:e for e in patch['replacements']}
    require(len(replacements)==len(patch['replacements']), 'REPLACEMENT_DUPLICATE')
    require(not {n['id'] for n in base['nodes']} & {n['id'] for n in patch['nodes']}, 'SLOT_NODE_COLLISION')
    require(set(replacements)<={e['evidence'] for e in base['edges']}, 'REPLACEMENT_MISSING')
    return dict(base,nodes=base['nodes']+patch['nodes'],
                edges=[replacements.get(e['evidence'],e) for e in base['edges']]+patch['edges'],
                profile=base['profile']+'; '+SCOPE)


def check(base,graph,patch,f,calls,functions,routes,obligations):
    require(f==facts(calls,functions,base,routes,obligations), 'EXACT_SLOT_FACTS')
    require(patch==delta(f), 'EXACT_SLOT_PATCH')
    # Independently derive the only permitted old-edge edits directly from the
    # retained operands. Do not rely just on the producer's patch/apply pair.
    targets={evidence(c):PREFIX+str(c['dependency']['builtin_index']) for c in calls
             if c['dependency']['category']=='builtin'}
    require(len(graph['edges'])==len(base['edges'])+len(set(targets.values())), 'EXACT_SLOT_GRAPH')
    for before,after in zip(base['edges'],graph['edges']):
        target=targets.get(before['evidence'])
        expected=dict(before,targets=[target],resolution='complete') if target else before
        require(after==expected,'EXACT_SLOT_GRAPH')
    # Full objects and multiplicity, including all old roots, nodes, gap edges,
    # initializers and descriptive implementation text, must agree exactly.
    require(graph==apply(base,patch), 'EXACT_SLOT_GRAPH')
    ids={n['id'] for n in graph['nodes']}
    require(all(e['from'] in ids and set(e['targets'])<=ids for e in patch['edges']+patch['replacements']),
            'SLOT_ENDPOINTS')
