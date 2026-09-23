"""Materialize immutable execution inputs; no compiler or runtime rebuild."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tarfile
import common as c

HARNESS=('worker.mjs','parallel.mjs','install.mjs')
SERVICES=('collector.wasm','integer.wasm','float.wasm','hash.wasm',
          'hash-adapter.wasm','detector.wasm','eql.wasm','stub.wasm')
HELPERS=('graph.mjs','gf-check.mjs','installer-check.mjs','metadata-check.mjs','bignum-check.mjs')


def driver_inputs(out):
    declared=c.read(out/'driver-manifest.json')
    drivers={name:digest for name,digest in declared.items()
             if name!='development.json' and 'development' not in Path(name).parts}
    c.verify_files(out/'driver',drivers)
    unexpected={str(p.relative_to(out/'driver')) for p in c.files(out/'driver')
                if p.suffix=='.py' and 'development' not in p.relative_to(out/'driver').parts}-set(drivers)
    if unexpected:raise ValueError('undeclared driver source: '+str(sorted(unexpected)))
    return {'driver-manifest.json':c.sha(out/'driver-manifest.json'),
            **{'driver/'+name:digest for name,digest in drivers.items()}}


def prepare(out):
    out=Path(out)
    for name in HARNESS:shutil.copyfile(c.HERE/name,out/name)
    # Parent artifacts were bound at session creation. Verify the actual raw
    # collection hook before reusing its instrumented counterpart.
    expected=c.read(c.PARENT/'deterministic.json')
    assert c.sha(out/'compiled/collector_probe.wat')==expected['compiled/collector_probe.wat']
    needed={'compiled/collector_probe_hook.wasm','compiled/collector_probe_hook.wat'}
    needed.update('owner-check/'+n for n in ('check.mjs','owner.mjs'))
    needed.update(n for n in expected if n.startswith('owner-check/') and n.endswith('.mjs'))
    needed.update(('istruct-check.mjs','population-check.mjs'))
    with tarfile.open(c.PARENT/'execution.tar.gz') as archive:
        for name in sorted(needed):
            data=archive.extractfile(name).read()
            assert hashlib.sha256(data).hexdigest()==expected[name]
            p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    for name in SERVICES+HELPERS:
        assert c.sha(out/name)==expected[name],name
    sys.path.insert(0,str(out/'driver'))
    from pool import compile_pool
    import encode
    encode.Encoder.__init__.__defaults__=(c.ROOT/'doc/WASM/contracts/wasm32-layout.v1.json',16*1024*1024)
    owners=c.read(out/'compiled/symbols.json')
    layout_path=c.ROOT/'doc/WASM/contracts/wasm32-layout.v1.json'
    pins=c.read(c.PARENT/'source-pins.json')
    assert c.sha(layout_path)==pins['doc/WASM/contracts/wasm32-layout.v1.json']
    pool=compile_pool(c.read(out/'compiled/pools.json'),{x['id']:7000006+32*i for i,x in enumerate(owners)})
    mat=pool.at(2097152)
    modules=c.read(out/'compiled/modules.json')
    # Conservative reservation, before any target memory or service exists.
    # The final allowance covers the fixed condition registry and its names.
    names_bytes=sum(8*((4+4*len(x['name'])+7)//8) for x in owners)
    if len(modules)+8>4096 or 2097152+len(mat.image)+32*(len(modules)+8)+names_bytes+65536>4194304:
        raise ValueError('probe installation capacity')
    if 7000000+32*len(owners)>8388608:raise ValueError('symbol capacity')
    layout=out/'compiled/pool-layout.json' 
    globals_=c.read(layout)['globalRoots'] if layout.exists() else [len(modules),len(modules)+1]
    c.save(out/'compiled/materialized.json',dict(image=mat.image.hex(),roots=mat.roots,globalRoots=globals_))
    # The parent deliberately keeps all literal vectors pinned (budget zero).
    # Preserve that contract instead of claiming a new pool-movement test.
    c.save(out/'compiled/moving-pools.json',{str(b):dict(image='',roots=mat.roots) for b in (8388608,2146500608)})
    rows=c.read(out/'compiled/native.json');counts={};ids=[]
    for row in rows:
        key=c.digest(row);ordinal=counts.get(key,0);counts[key]=ordinal+1
        ids.append(key+':'+str(ordinal))
    c.save(out/'case-ids.json',ids)
    manifest={str(p.relative_to(out)):c.sha(p) for p in c.files(out/'runtime')}
    for name in HARNESS+SERVICES+HELPERS:manifest[name]=c.sha(out/name)
    # Use the declared session inputs, never incidental logs or review files.
    manifest.update(driver_inputs(out))
    for p in c.files(out/'owner-check'): 
        if p.suffix=='.mjs':manifest[str(p.relative_to(out))]=c.sha(p)
    for name in ('istruct-check.mjs','population-check.mjs'):manifest[name]=c.sha(out/name)
    for name in ('modules.json','symbols.json','pools.json','materialized.json','moving-pools.json',
                 'condition-callers.json','native-condition-classes.json'):
        manifest['compiled/'+name]=c.sha(out/'compiled'/name)
    for row in modules:
        name='compiled/'+('collector_probe_hook' if row['name']=='collector_probe' else row['name'])+'.wasm'
        manifest[name]=c.sha(out/name)
    c.save(out/'execution-environment.json',dict(version=1,files=manifest,
        engine=dict(path=str(c.NODE),sha256=c.sha(c.NODE)),
        tooling={n:c.sha(c.HERE/n) for n in ('prepare.py','execute.py','common.py')},
        placements=[8388608,2146500608],movement=[False,True],fp_control=7,
        layout=c.sha(layout_path),
        reset='complete declared mutable regions; fresh owner/numeric services per case',
        compiler_environment=c.read(out/'environment.json')))
    return len(rows)
