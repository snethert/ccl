"""Audit-174 controls using the exact R12 compiler session, no corpus rebuild."""
from pathlib import Path
import importlib.util
import json
import shutil
import sys
HERE=Path(__file__).resolve().parent
READY=HERE.parent/'ready'
sys.path.insert(0,str(READY))
import run as ready
c=ready.c
PARENT=c.STORE/'2026-09-24-stage1-ready-join-r12'

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def prepare_probe(out):
    ready.execution_prepare(out)
    module('class_image_prepare',HERE.parent/'class-image/prepare.py').prepare(out)
    # Byte-exact reviewed runtime and drivers. Integration changes their homes,
    # not the execution contract of this focused qualification.
    for name in ('worker.mjs','bindings.mjs','bindings.json','process.mjs'):
        target={'worker.mjs':'ready-worker.mjs','bindings.mjs':'ready-bindings.mjs',
                'bindings.json':'ready-bindings.json'}.get(name,name)
        shutil.copyfile(PARENT/'source'/name,out/target)
    shutil.copyfile(PARENT/'runtime-proposal/runtime/heap-image.mjs',out/'runtime/heap-image.mjs')
    shutil.copyfile(c.ROOT/'runtime/wasm32/initialization-owner.mjs',out/'runtime/initialization-owner.mjs')
    code=c.read(out/'class-image-code.json')
    for name in ('runtime/heap-image.mjs','collector.wasm','runtime/initialization-owner.mjs',
                 'process.mjs','ready-worker.mjs','ready-bindings.mjs','ready-bindings.json'):
        code[name]=c.sha(out/name)
    (out/'class-image-code.json').write_bytes(c.canonical(code))
    (out/'class-image-code.sha256').write_text(c.sha(out/'class-image-code.json')+'\n')


def guards(out):
    source=(PARENT/'proposal/compiler/WASM32/wasm32-backend.lisp').read_text()
    section=source.split("((eq name 'ccl::%wasm-lock-owner-token)",1)[1]
    expression=section.split(':text',1)[1].split('"',2)[1]
    assert '(block (result i32)' in expression and '(throw $call_error' in expression
    fragments={'zero':'(i32.eqz (global.get $tcr))',
       'alignment':'(i32.and (global.get $tcr) (i32.const 15))',
       'positive':'(i32.ge_u (global.get $tcr) (i32.const 2147483648))'}
    out.mkdir()
    for name,omit in [('real',None),*fragments.items()]:
        text=expression
        if omit:
            assert text.count(omit)==1;text=text.replace(omit,'(i32.const 0)')
        wat=out/(name+'.wat')
        wat.write_text('(module (import "env" "tcr" (global $tcr i32))\n'
            '(tag $call_error (export "call_error") (param i32))\n'
            '(func (export "token") (result i32)\n'+text+'))\n')
        c.assemble(wat,c.DEFAULT_CACHE)
    c.command([c.NODE,HERE/'guards.mjs',out,out/'results.json'],out/'run.log',timeout=60)
    c.save(out/'source.json',dict(backend_sha256=c.sha(PARENT/'proposal/compiler/WASM32/wasm32-backend.lisp'),expression=expression,
      contract='READY passes immutable env.tcr=1024. The zero/alignment/positive checks are defense in depth; this local test isolates each emitted clause without entering a frame with an invalid TCR.'))

def run(out):
    out.mkdir(exist_ok=True)
    assert c.sha(PARENT/'packet.json')=='e36a8d881fe2df73cc2ce34829165a7fa13654e3cc05157eda8c053506a21d9c'
    files=c.read(PARENT/'packet.json')['files']
    inputs=['pins.json','build-identity.json','source/startup.lisp','source/inputs.lisp',
            'source/worker.mjs','source/bindings.mjs','source/bindings.json','source/process.mjs',
            'runtime-proposal/runtime/heap-image.mjs','proposal/compiler/WASM32/wasm32-backend.lisp']
    c.verify_files(PARENT,{name:files[name] for name in inputs})
    pins=c.read(PARENT/'pins.json')
    used={name:digest for name,digest in pins.items()
          if name.startswith(('tests/wasm/stage1/bootstrap-validation/',
                              'tests/wasm/stage1/class-image/'))
          or name in ('tests/wasm/stage1/ready/compiler.py','tests/wasm/stage1/ready/run.py',
                      'tests/wasm/stage1/ready/run.mjs','runtime/wasm32/initialization-owner.mjs')}
    c.verify_files(c.ROOT,used)
    if not (out/'guards/results.json').exists():guards(out/'guards')
    # A pinned cache session preserves whole-file macro environments and all
    # installed symbol/module/pool identities. A miss is never cold-built with
    # the current shared compiler, which may already be the integrated R12.
    import build
    environment=c.read(PARENT/'build-identity.json')['environment']
    key=c.digest(environment)
    assert c.cache_read(c.DEFAULT_CACHE,'session',key), 'Run R12 at f8180b52 first to populate its cache session'
    build.environment=lambda:environment
    if not (out/'base').exists():build.build(out/'base',c.DEFAULT_CACHE)
    source=(PARENT/'source/startup.lisp').read_text()
    anchor='     (ccl::recursive-lock-p lock)'
    assert source.count(anchor)==1
    source=source.replace(anchor,anchor+'\n'+(HERE/'lock-classes.lisp').read_text())
    submitted=out/'probes.lisp';submitted.write_text(source)
    shutil.copyfile(PARENT/'source/inputs.lisp',out/'inputs.lisp')
    # Prepare the reviewed proposal services, never a newly generated backend.
    build.environment=lambda:environment
    from probe import probe
    for name,body in [('positive',source),('wrong-class',source.replace("(ccl::recursive-lock 'ccl::recursive-lock)","(ccl::recursive-lock 'ccl:lock)",1))]:
        path=out/(name+'.lisp');path.write_text(body)
        probe(out/'base',path,out/'inputs.lisp',out/name,c.DEFAULT_CACHE,'class',4)
        prepare_probe(out/name)
        try:
            c.command([c.NODE,READY/'run.mjs',out/name,'write',out/(name+'-images'),out/(name+'.json')],out/(name+'.log'),timeout=600)
        except Exception:
            if name!='wrong-class':raise
            assert 'READY-RECURSIVE-LOCKS native result' in (out/(name+'.log')).read_text()
        else:
            assert name=='positive', 'wrong-class mutant survived'
        if name=='positive':
            c.command([c.NODE,READY/'run.mjs',out/name,'read',out/(name+'-images'),out/'reader.json'],out/'reader.log',timeout=600)
        retained=out/(name+'-inputs');retained.mkdir()
        for f in ('probe-completion.json','submitted/probes.lisp','submitted/inputs.lisp','probe-output/probe-native.json','probe.log'):
            dest=retained/Path(f).name;shutil.copyfile(out/name/f,dest)
        c.save(retained/'modules.json',{str(p.relative_to(out/name)):c.sha(p) for p in (out/name/'probe-output').glob('*.wasm')})
        shutil.copyfile(out/name/'class-image-code.json',retained/'class-image-code.json')
        shutil.rmtree(out/name)
        shutil.rmtree(out/(name+'-images'),ignore_errors=True)
    c.save(out/'summary.json',dict(status='PASS',new_original_credit=0,full_corpus_reexecuted=False,
        class_kinds=['recursive-lock','read-write-lock','other'],collection_variants=2,cold_boots=4,
        wrong_class_mutant_refused=True,token_checks=20))
    shutil.rmtree(out/'base')
    return c.read(out/'summary.json')

if __name__=='__main__':
    out=Path(sys.argv[1]);ready.storage.gc()
    with ready.storage.lease([out]):print(json.dumps(run(out)))
