"""Compile and link namespace consumers against a hash-bound compiler session."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import os,sys,shutil,tarfile,tempfile,json,importlib.util,hashlib
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage
import proposal
import graph
KEY='f5942d1c328b4b74c66c2f1ec529956b952e93ad4fc3fef3c6e70ca5a757b271'

def run(out, compiler_key=KEY):
    out.mkdir(parents=True,exist_ok=True)
    entry=c.cache_read(c.DEFAULT_CACHE,'session',compiler_key)
    assert entry
    kernel=out/'namespace-compiler'
    if not kernel.exists() or c.sha(kernel)!=c.sha(c.KERNEL):
        shutil.copyfile(c.KERNEL,kernel);kernel.chmod(0o755)
    generated=out/'extension';generated.mkdir(exist_ok=True)
    (generated/'symbols.json').unlink(missing_ok=True)
    if (out/'extension.log').exists():
        history=out/'development';history.mkdir(exist_ok=True)
        shutil.copyfile(out/'extension.log',history/(c.sha(out/'extension.log')+'.log'))
    owners=c.read(entry/'compiled/symbols.json')
    q=lambda x:'nil' if x is None else '"'+x.replace('\\','\\\\').replace('"','\\"')+'"'
    (generated/'owners.lisp').write_text('('+''.join('('+q(x['name'])+' '+q(x['package'])+' '+q(x['id'])+')' for x in owners)+')\n')
    modules=c.read(entry/'compiled/modules.json');uninterned={r['id'] for r in owners if r['package'] is None};bindings=[]
    for m in modules:
        imports=[(w,o) for w,o in m['symbols'] if o in uninterned]
        fn=m['function'] if m['function'] in uninterned else None
        if imports or fn:bindings.append('('+q(m['name'])+' '+q(fn)+' ('+''.join('('+q(w)+' '+q(o)+')' for w,o in imports)+'))')
    (generated/'bindings.lisp').write_text('('+''.join(bindings)+')')
    (generated/'restore.lisp').write_text((c.HERE/'probe.lisp').read_text().split('(defvar *validation-base-count*)')[0])
    protocol=(entry/'driver/cpl-inputs.lisp').read_text()
    protocol='(in-package :wasm32-compiler)\n'+protocol[protocol.index('(defun condition-system-protocol'):protocol.index('(defun condition-system-image')]
    protocol=protocol.replace("(mapcar #'find-class classes)", "(mapcar (lambda (s) (if (symbolp s) (find-class s) s)) classes)")
    (generated/'protocol.lisp').write_text(protocol)
    (generated/'graph.lisp').write_text(graph.source())
    frontend=(c.HERE/'driver/whole-file.lisp').read_text()
    old='(list :wasm-module wire outcome)'
    assert frontend.count(old)==1
    frontend=frontend.replace(old,"""(if result
                        (let ((cell (gensym "FILE-CODE-")))
                          (push (list cell wire) *namespace-load-references*)
                          (make-wasm32-function-reference cell))
                        (list :wasm-module wire outcome))""")
    (generated/'whole-file.lisp').write_text('(in-package :wasm32-compiler)\n(defvar *namespace-load-references* nil)\n'+frontend)

    with tempfile.TemporaryDirectory(prefix='u1-',dir=out) as temp:
        src=Path(temp)
        for name in ('source.tar','bootstrap.tar.gz'):
            with tarfile.open(c.STORE/'macos-u1-inputs'/name) as archive:archive.extractall(src,filter='data')
        for p in c.files(entry/'compiled/proposal/files'):
            dst=src/p.relative_to(entry/'compiled/proposal/files');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
        for name,body in proposal.sources().items():
            p=src/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body)
        env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(src)+'/',PROBE_OUTPUT=str(generated)+'/',NAMESPACE_SOURCE=str(HERE)+'/',POOL_OUTPUT=str(generated)+'/')
        core_inputs={'compiler_key':compiler_key,**{str(p):c.sha(p) for p in [HERE/'core-build.lisp',
            generated/'restore.lisp',generated/'protocol.lisp',generated/'graph.lisp',generated/'whole-file.lisp']}}
        core_inputs.update({name:hashlib.sha256(body.encode()).hexdigest() for name,body in proposal.sources().items()
                            if name not in ('lib/foreign-types.lisp','level-1/l1-dcode.lisp','level-1/l1-aprims.lisp')})
        core=generated/'core.image';stamp=generated/'core-cache.json'
        valid=core.exists() and stamp.exists() and c.read(stamp)['inputs']==core_inputs and c.read(stamp)['image']==c.sha(core)
        if not valid:
            core.unlink(missing_ok=True)
            argv=[kernel,'-I',entry/'compiled/compiler.image','--no-init','--batch','--load',generated/'restore.lisp','--load',generated/'protocol.lisp','--load',generated/'graph.lisp','--load',HERE/'core-build.lisp']
            c.command(argv,out/'core-build.log',env,cwd=src,timeout=240)
            c.save(stamp,dict(inputs=core_inputs,image=c.sha(core)))
        argv=[kernel,'-I',core,'--no-init','--batch','--load',HERE/'extension.lisp']
        c.command(argv,out/'extension.log',env,cwd=src,timeout=240)
    assert 'NAMESPACE-EXTENSION-PASS' in (out/'extension.log').read_text()
    image=c.read(generated/'native.json')[0]['args'][0]['graph']
    nodes=image['nodes'];classes=nodes[image['root']['ref']]['fields'][11];count=0
    while 'ref' in classes:
        node=nodes[classes['ref']];assert node['tag']==1
        count+=1;classes=node['fields'][1]
    generics=sum('generic' in node for node in nodes)
    assert (count,generics)==(612,53),'native projection extended'
    c.save(out/'projection.json',dict(status='PASS',classes=count,generic_functions=generics,
        graph_source=c.sha(HERE.parent/'ready/graph.lisp'),compiler_key=compiler_key,
        new_native_objects_projected=False))
    target=out/'target'
    if not target.exists():shutil.copytree(entry,target,ignore=shutil.ignore_patterns('compiler.image','*.wat','*.log'))
    new=c.read(generated/'modules.json');replaced={r[0] for r in c.read(generated/'public-definitions.json')}
    # A later whole-file definition supersedes every older version at its cell.
    keep=[dict(r,poolRoot=i) for i,r in enumerate(modules) if r['function'] not in replaced]
    basepools=c.read(entry/'compiled/pools.json');extra=c.read(generated/'pools.json');offset=len(basepools['objects'])
    def relocate(x):
        if isinstance(x,list):return [relocate(v) for v in x]
        if isinstance(x,dict):return {k:('o'+str(int(v[1:])+offset) if k in ('ref','id') else relocate(v)) for k,v in x.items()}
        return x
    extra=relocate(extra)
    allmods=keep+[dict(r,poolRoot=len(basepools['roots'])+i) for i,r in enumerate(new)]
    # Drop older named implementations shadowed by the admitted class-mode one.
    classnames={r['function'] for r in allmods if r['cplMode'] and r['function']}
    allmods=[r for r in allmods if r['cplMode'] or not r['function'] or r['function'] not in classnames]
    c.save(target/'compiled/modules.json',allmods)
    c.save(target/'compiled/pools.json',dict(version=1,objects=basepools['objects']+extra['objects'],roots=basepools['roots']+extra['roots']))
    c.save(target/'compiled/pool-layout.json',dict(globalRoots=[len(modules),len(modules)+1]))
    for name in ('symbols.json','native.json','initializers.json','load-bindings.json','public-definitions.json','setf-bindings.json'):
        shutil.copyfile(generated/name,target/'compiled'/name)
    c.save(target/'compiled/condition-callers.json',['NAMESPACE-CHECK'])
    for m in allmods:
        name=m['name']+'.wat';p=generated/name
        if not p.exists():p=entry/'compiled'/name
        shutil.copyfile(p,target/'compiled'/name)
    import prune
    allmods=prune.select(target,allmods)
    prune.pools(target,allmods)
    c.save(target/'compiled/modules.json',allmods)
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda m:c.assemble(target/'compiled'/(m['name']+'.wat'),c.DEFAULT_CACHE),allmods))
    # Preserve the expected source of the parent's collection hook.
    shutil.copyfile(entry/'compiled/collector_probe.wat',target/'compiled/collector_probe.wat')
    finish(out,entry,allmods,new)
    return target

def finish(out,entry,allmods,new):
    target=out/'target'
    shutil.copytree(entry/'driver',target/'driver',dirs_exist_ok=True)
    from prepare import prepare, SERVICES
    for name in SERVICES:shutil.copyfile(entry/name,target/name)
    prepare(target)
    (target/'runtime/collector.c').write_text(proposal.collector())
    c.command(['/usr/local/opt/llvm/bin/clang','--target=wasm32','-O2','-nostdlib','-fno-builtin','-matomics','-mbulk-memory',
      '-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,--shared-memory',
      '-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer',
      target/'runtime/collector.c','-o',target/'collector.wasm'],out/'collector.log')
    for name in ('client.mjs','protocol.mjs','host.mjs'):
        shutil.copyfile(HERE.parent/'namespace-primitives'/name,target/name)
    c.command([c.WABT,HERE.parent/'namespace-primitives/adapter.wat','--enable-all','-o',target/'file-adapter.wasm'],out/'adapter.log')
    shutil.copyfile(HERE.parent/'namespace/namespace.mjs',target/'runtime/namespace.mjs')
    shutil.copyfile(HERE.parent/'ready/bindings.json',target/'ready-bindings.json')
    import symbols
    (target/'runtime/symbols.c').write_text(symbols.source())
    c.command(['/usr/local/opt/llvm/bin/clang','--target=wasm32','-O2','-nostdlib','-fno-builtin',
      '-Wl,--no-entry','-Wl,--export-all','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,--shared-memory',
      '-matomics','-mbulk-memory','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536',
      target/'runtime/symbols.c','-o',target/'symbols.wasm'],out/'symbols.log')
    c.command([c.WABT,c.ROOT/'runtime/wasm32/symbol-adapter.wat','--enable-all','-o',target/'symbol-adapter.wasm'],out/'symbol-adapter.log')
    shutil.copyfile(HERE/'packages.mjs',target/'packages.mjs')
    shutil.copyfile(HERE/'controls.mjs',target/'namespace-controls.mjs')
    (target/'runtime/collector-owner.mjs').write_text(proposal.runtime_sources()['runtime/wasm32/collector-owner.mjs'])
    print('PREPARED',len(allmods),len(new),flush=True)
    return target

if __name__=='__main__':
    storage.gc()
    with storage.lease([Path(sys.argv[1])]):
        out=Path(sys.argv[1]).resolve()
        if '--prepare' in sys.argv:finish(out,c.DEFAULT_CACHE/'session'/c.read(out/'projection.json')['compiler_key'],c.read(out/'target/compiled/modules.json'),c.read(out/'extension/modules.json'))
        else:run(out,sys.argv[sys.argv.index('--compiler-cache')+1] if '--compiler-cache' in sys.argv else KEY)
