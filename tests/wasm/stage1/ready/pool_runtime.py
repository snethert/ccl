"""Native one-cell recycling pools: clear on collection, not strong retention."""
from pathlib import Path
import common as c
HERE=Path(__file__).resolve().parent

def source():
    text=(c.ROOT/'runtime/wasm32/collector.c').read_text()
    old='   else if(tag==50){if(n!=4)return reject(s,BAD_OBJECT);scan=n;size=4+(W)n*4;}'
    assert text.count(old)==1
    text=text.replace(old,old+'\n   else if(tag==82){if(n!=1)return reject(s,BAD_OBJECT);scan=0;size=8;}')
    old='  scan=o->scan;p=o->moved;'
    assert text.count(old)==1
    return text.replace(old,old+'\n  /* Native pools discard recyclable contents at every collection.\n   * Clear only the destination; source/root publication remains atomic. */\n  if(LOAD(p)==338)STORE(p+4,NIL);')

def prepare(out):
    path=out/'runtime/collector.c'
    path.write_text(source())
    # Service compilation is independent of the unchanged Lisp session.
    key=c.digest(dict(source=c.sha(path),clang=c.sha(Path('/usr/local/opt/llvm/bin/clang'))))
    old=out/'pool-runtime.json'
    if not old.exists() or c.read(old)['key']!=key or c.sha(out/'collector.wasm')!=c.read(old)['binary']:
        c.command(['/usr/local/opt/llvm/bin/clang','--target=wasm32','-O2','-nostdlib','-fno-builtin','-matomics','-mbulk-memory',
          '-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,--shared-memory',
          '-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer',
          path,'-o',out/'collector.wasm'],out/'pool-collector.log')
        c.save(old,dict(key=key,source=c.sha(path),binary=c.sha(out/'collector.wasm')))
    env=c.read(out/'execution-environment.json')
    env['files']['collector.wasm']=c.sha(out/'collector.wasm')
    env['tooling']['ready/pool_runtime.py']=c.sha(Path(__file__))
    c.save(out/'execution-environment.json',env)

def reset_parent(out):
    """Restore the pinned parent's service inputs before its preparer validates."""
    record=c.read(out/'ready-runtime.json')
    original=c.ROOT/'runtime/wasm32/collector.c'
    assert c.sha(original)==record['source']
    path=out/'runtime/collector.c'
    import hashlib
    assert c.sha(path) in (record['source'],hashlib.sha256(source().encode()).hexdigest())
    path.write_bytes(original.read_bytes())
    expected=c.read(c.PARENT/'deterministic.json')['collector.wasm']
    key=c.read(out/'build-invocation.json')['key']
    parent=c.DEFAULT_CACHE/'session'/key/'collector.wasm'
    assert c.sha(parent)==expected
    known={expected,record['collector.wasm']}
    if (out/'pool-runtime.json').exists():known.add(c.read(out/'pool-runtime.json')['binary'])
    assert c.sha(out/'collector.wasm') in known
    import shutil
    shutil.copyfile(parent,out/'collector.wasm')
