"""Compile one probe file against a hash-bound retained CCL session."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import sys
import tarfile
import os
import shutil
import tempfile
import time
import common as c


def probe(base,source,inputs,out,cache,mode='class',workers=4):
    base,source,inputs,out=map(lambda p:Path(p).resolve(),(base,source,inputs,out))
    # Check the complete cached session, not an unbound image from /tmp.
    invocation=c.read(base/'build-invocation.json');key=invocation['key']
    from build import environment
    if c.digest(environment())!=key:raise ValueError('compiler environment changed; rebuild session')
    unit='tests/wasm/stage1/registration/unit.py'
    c.verify_files(c.ROOT,{unit:c.read(c.PARENT/'source-pins.json')[unit]})
    entry=c.cache_read(cache,'session',key)
    if entry is None:raise ValueError('retained compiler session is missing')
    pinned=c.read(entry/'cache-manifest.json')['files']
    c.verify_files(base,{n:h for n,h in pinned.items()
                        if n.startswith(('compiled/','driver/'))})
    out.mkdir()
    generated=out/'probe-output';generated.mkdir()
    submitted=out/'submitted';submitted.mkdir()
    for original,name in ((source,'probes.lisp'),(inputs,'inputs.lisp'),(c.HERE/'probe.lisp','driver.lisp')):
        shutil.copyfile(original,submitted/name)
    source,inputs=submitted/'probes.lisp',submitted/'inputs.lisp'
    driver=submitted/'driver.lisp' 
    # Complete oracle owner numbering without changing identities already
    # present at the pre-execution checkpoint.
    def quote(x):return 'nil' if x is None else '"'+x.replace('\\','\\\\').replace('"','\\"')+'"'
    owners=c.read(base/'compiled/symbols.json')
    (generated/'owners.lisp').write_text('('+''.join('('+quote(x['name'])+' '+quote(x['package'])+' '+quote(x['id'])+')' for x in owners)+')\n')
    modules=c.read(base/'compiled/modules.json')
    # Printed names do not identify CCL's uninterned SETF function symbols.
    # Bind each retained wire to the actual symbol in the saved module record.
    uninterned={row['id'] for row in owners if row['package'] is None}
    bindings=[]
    for module in modules:
        imports=[(wire,owner) for wire,owner in module['symbols'] if owner in uninterned]
        function=module['function'] if module['function'] in uninterned else None
        if imports or function:
            bindings.append('('+quote(module['name'])+' '+quote(function)+' ('+
                            ''.join('('+quote(wire)+' '+quote(owner)+')' for wire,owner in imports)+'))')
    (generated/'bindings.lisp').write_text('('+''.join(bindings)+')\n')
    (generated/'base.lisp').write_text('('+str(len(modules))+' '+str(len(c.read(base/'compiled/pools.json')['roots']))+' ('+
        ' '.join(quote(m['function']) for m in modules if m['function'])+'))\n')
    with tempfile.TemporaryDirectory(prefix='u1-', dir=out) as tmp:
        work=Path(tmp);src=work/'ccl';src.mkdir()
        for name in ('source.tar','bootstrap.tar.gz'):
            with tarfile.open(c.STORE/'macos-u1-inputs'/name) as archive:
                archive.extractall(src,filter='data')
        c.save(work/'stage1-disposable.json',{'source':str(src)})
        shutil.copyfile(c.KERNEL,src/'dx86cl64');(src/'dx86cl64').chmod(0o755)
        sys.path.insert(0,str(c.ROOT/'tests/wasm/stage1/registration'))
        from unit import Unit
        env=dict(PATH='/usr/local/bin:/usr/bin:/bin',LANG='C',LC_ALL='C',
            CCL_DEFAULT_DIRECTORY=str(src),PROBE_SOURCE=str(source),PROBE_INPUTS=str(inputs),
            PROBE_OUTPUT=str(generated)+'/',PROBE_MODE=mode)
        with Unit(src,entry/'compiled/proposal'):
            seconds=c.command([src/'dx86cl64','-I',entry/'compiled/compiler.image','--no-init','--batch',
                               '--load',driver],out/'probe.log',env,cwd=src,timeout=120)
    if 'VALIDATION-PROBES-PASS' not in (out/'probe.log').read_text():raise ValueError('incomplete probe')
    # Refused probe compiles need only their inputs/log, not a corpus copy.
    shutil.copytree(base,out,dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('compiler.image','probe.log'))
    modules=c.read(base/'compiled/modules.json');new=c.read(generated/'probe-modules.json')
    if {m['name'] for m in modules}&{m['name'] for m in new}:raise ValueError('probe module collision')
    old_symbols=c.read(base/'compiled/symbols.json');symbols=c.read(generated/'symbols.json')
    if symbols[:len(old_symbols)]!=old_symbols:raise ValueError('symbol identities changed')
    old_pools=c.read(base/'compiled/pools.json');pools=c.read(generated/'probe-pools.json')
    offset=len(old_pools['objects'])
    def relocate(value):
        if isinstance(value,list):return [relocate(x) for x in value]
        if isinstance(value,dict):
            return {k:('o'+str(int(v[1:])+offset) if k in ('ref','id') else relocate(v)) for k,v in value.items()}
        return value
    addition=relocate(pools)
    pools=dict(version=1,objects=old_pools['objects']+addition['objects'],
               roots=old_pools['roots']+addition['roots'])
    c.save(out/'compiled/modules.json',modules+new)
    c.save(out/'compiled/symbols.json',symbols);c.save(out/'compiled/pools.json',pools)
    c.save(out/'compiled/pool-layout.json',dict(globalRoots=[len(modules),len(modules)+1]))
    old_rows=c.read(base/'compiled/native.json');rows=c.read(generated/'probe-native.json')
    controls=[next(r for r in old_rows if r['definition']=='CORE-CONDITION-TABLE-GROW' and r['values'][1]==1500),
              next(r for r in old_rows if r['definition']=='CORE-GENERIC-READER-DISPATCH'),
              next(r for r in old_rows if r['definition']=='%ROUND-NEAREST-DOUBLE-FLOAT->FIXNUM'),
              next(r for r in old_rows if r['definition']=='%TRUNCATE-DOUBLE-FLOAT->FIXNUM')]
    (out/'compiled/native.json').write_bytes(c.canonical(rows+controls)+b'\n')
    callers=c.read(base/'compiled/condition-callers.json')
    if mode=='class':callers+=c.read(generated/'probe-callers.json')
    c.save(out/'compiled/condition-callers.json',callers)
    paths=[]
    for p in generated.glob('*.wat'):
        q=out/'compiled'/p.name;shutil.copyfile(p,q);paths.append(q)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        assembly=list(pool.map(lambda p:c.assemble(p,cache),sorted(paths)))
    report=dict(status='PASS',compiler_processes=1,base_compiler_rebuilt=False,
        compiled_modules=len(paths),new_cases=len(rows),indices=list(range(len(rows))),
        session_key=key,compiler_image=c.sha(entry/'compiled/compiler.image'),
        source=c.sha(source),inputs=c.sha(inputs),driver=c.sha(driver),mode=mode,
        seconds=seconds,assembly=assembly,wabt_jobs=workers,
        wabt_processes=sum(row['rebuilt'] for row in assembly),
        wabt_cache_hits=sum(not row['rebuilt'] for row in assembly))
    c.save(out/'probe-completion.json',report)
    return report
