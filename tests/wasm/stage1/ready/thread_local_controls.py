"""Arity refusals and an execution control for global-vs-thread lookup."""
from pathlib import Path
import shutil
import os
import common as c
HERE=Path(__file__).resolve().parent

def check(out):
    log=out/'thread-local-arity.log'
    kernel=out/'control-dx86cl64'
    shutil.copyfile(c.KERNEL,kernel);kernel.chmod(0o755)
    c.command([kernel,'-I',out/'base/compiled/compiler.image','--no-init','--batch',
               '--load',HERE/'thread-local-controls.lisp'],log,dict(os.environ,VALIDATION_PROBE_DRIVER=str(HERE.parent/'bootstrap-validation/probe.lisp')),timeout=60)
    kernel.unlink()
    assert 'READY-IMAGE-CALLEE-CONTROLS-PASS' in log.read_text()
    assert 'THREAD-LOCAL-ARITY-PASS' in log.read_text()
    root=out/'compiled'
    rows=c.read(root/'probe-output/probe-native.json')
    row=next(r for r in rows if r['definition']=='READY-THREAD-VALUE')
    wat=root/'compiled'/(row['name']+'.wat');wasm=wat.with_suffix('.wasm')
    original=wat.read_text();binary=wasm.read_bytes()
    # The actual compiled module has one use of the helper. Let the global
    # fallback through: the unbound and post-unwind observations must change.
    import re
    pattern=r'\(then \(i32.const 77825\)\)\s*\(else \(i32.load (\(local.get [^)]+\))\)\)'
    assert len(re.findall(pattern,original))==1
    changed=re.sub(pattern,lambda m:'(then (i32.load '+m[1]+')) (else (i32.load '+m[1]+'))',original)
    dev=out/'development/thread-local';dev.mkdir(parents=True,exist_ok=True)
    mutant=dev/'global-fallback.wat';mutant.write_text(changed)
    c.assemble(mutant,c.DEFAULT_CACHE)
    manifest=root/'class-image-code.json';digest=root/'class-image-code.sha256'
    saved=manifest.read_bytes();saved_digest=digest.read_bytes()
    try:
        shutil.copyfile(mutant.with_suffix('.wasm'),wasm)
        code=c.read(manifest);code[str(wasm.relative_to(root))]=c.sha(wasm)
        manifest.write_bytes(c.canonical(code));digest.write_text(c.sha(manifest)+'\n')
        try:
            c.command([c.NODE,HERE/'run.mjs',root,'write',dev/'images',dev/'writer.json'],dev/'run.log',timeout=120)
        except Exception:
            assert 'READY-THREAD-VALUES native result' in (dev/'run.log').read_text()
        else:raise AssertionError('global fallback survived')
    finally:
        wasm.write_bytes(binary);manifest.write_bytes(saved);digest.write_bytes(saved_digest)
    c.save(out/'thread-local-controls.json',dict(status='PASS',arity_refusals=2,image_callee_checks=5,
        global_fallback_refused=True,module=row['name'],original_wasm=c.sha(wasm),mutant_wasm=c.sha(mutant.with_suffix('.wasm'))))
    shutil.rmtree(dev/'images',ignore_errors=True)
    return c.read(out/'thread-local-controls.json')
