"""Select code by compiler imports, pool references and declared fixture roots."""
from pathlib import Path
import json,re

def select(directory,modules):
    read=lambda name:json.loads((directory/'compiled'/name).read_text())
    symbols=read('symbols.json');owners={s['package']+'::'+s['name']:s['id'] for s in symbols if s['package']}
    byname={m['name']:m for m in modules};effective={}
    for m in modules:
        if m['function']:effective[m['function']]=m['name']
    pools=read('pools.json');objects={r['id']:r['value'] for r in pools['objects']}
    pending=[r['name'] for r in read('native.json')]+read('initializers.json')
    pending += [effective[owners[n]] for n in ('WASM32-COMPILER::READY-INITIALIZE','WASM32-COMPILER::READY-IMAGE-STATUS','CCL::FUNCALLABLE-TRAMPOLINE','CCL::%WASM-MAKE-CLASS-TABLE')]
    pending += [effective[owners['CCL::%WASM-'+n]] for n in ('MAKE-HASH-TABLE','GETHASH','PUTHASH','REMHASH','CLRHASH','MAPHASH','HASH-TABLE-COUNT','SXHASH')]
    pending.append(effective[owners['WASM32-COMPILER::NAMESPACE-TYPE-INITIALIZE']])
    pending += [effective[owners['WASM32-COMPILER::NAMESPACE-'+n]] for n in ('ROOT-CHECK','BYTE-COPY','VECTOR-ALLOCATE','TABLE-REFUSALS')]
    pending += [effective[owners['WASM32-COMPILER::NAMESPACE-'+n]] for n in
                ('METHOD-INITIALIZE','FOREIGN-INITIALIZE','FOREIGN-CASES','FOREIGN-CHECK','DATABASE-DENIED')]
    pending.append(effective[owners['CCL::%WASM-NAMESPACE-INITIALIZE']])
    pending.append(effective[owners['CCL::%WASM-NAMESPACE-SUPPORT-INITIALIZE']])
    pending += [effective[owners['CCL::%WASM-'+n]] for n in ('INTERN','FIND-SYMBOL','PACKAGE-LITERAL')]
    loadrefs=dict(read('load-bindings.json'))
    pending += [m['name'] for m in modules if m['primitive'] or m['name']=='collector_probe']
    seenobjects=set()
    def scan(value):
        if isinstance(value,list):
            for x in value:scan(x)
        elif isinstance(value,dict):
            if 'ref' in value and isinstance(value['ref'],str) and value['ref'].startswith('o'):
                ref=value['ref']
                if ref not in seenobjects:
                    seenobjects.add(ref);scan(objects[ref])
            for key,item in value.items():
                if key in ('symbol','function') and isinstance(item,str):
                    owner=owners.get(item,item)
                    if owner in effective:pending.append(effective[owner])
                    elif owner in loadrefs:pending.append(loadrefs[owner])
                elif key!='ref':scan(item)
    scan(read('native.json'))
    seen=set()
    while pending:
        name=pending.pop()
        if name in seen:continue
        m=byname[name];seen.add(name)
        for wire,owner in m['symbols']:
            if owner in effective:pending.append(effective[owner])
            elif owner in loadrefs:pending.append(loadrefs[owner])
        scan(pools['roots'][m['poolRoot']])
        text=(directory/'compiled'/(name+'.wat')).read_text()
        pending += re.findall(r'\(import "codes" "([^"]+)"',text)
    return [m for m in modules if m['name'] in seen]

def pools(directory,modules):
    """Discard unreachable compiler pools, preserving identities and sharing."""
    path=directory/'compiled/pools.json'
    graph=json.loads(path.read_text())
    layout_path=directory/'compiled/pool-layout.json'
    layout=json.loads(layout_path.read_text())
    old_roots=layout['globalRoots']+[m['poolRoot'] for m in modules]
    old_roots=list(dict.fromkeys(old_roots));indices={old:new for new,old in enumerate(old_roots)}
    roots=[graph['roots'][i] for i in old_roots]
    objects={r['id']:r['value'] for r in graph['objects']};seen=set();pending=list(roots)
    while pending:
        value=pending.pop()
        if isinstance(value,list):pending.extend(value)
        elif isinstance(value,dict):
            ref=value.get('ref')
            if isinstance(ref,str) and ref in objects and ref not in seen:
                seen.add(ref);pending.append(objects[ref])
            pending.extend(value.values())
    retained=[r for r in graph['objects'] if r['id'] in seen]
    result=dict(objects_before=len(graph['objects']),objects_after=len(retained),
                roots_before=len(graph['roots']),roots_after=len(roots))
    graph.update(objects=retained,roots=roots)
    for m in modules:m['poolRoot']=indices[m['poolRoot']]
    layout['globalRoots']=[indices[i] for i in layout['globalRoots']]
    path.write_text(json.dumps(graph,sort_keys=True)+'\n')
    layout_path.write_text(json.dumps(layout,sort_keys=True)+'\n')
    (directory/'pool-pruning.json').write_text(json.dumps(result,sort_keys=True)+'\n')
    return result
