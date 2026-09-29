"""Qualify the single-Worker FOREIGN owner and its ordinary loaded Lisp witness."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT/'tests/wasm/stage1/bootstrap-validation'))
import common as c
import storage

SCALAR = HERE.parent/'foreign-scalar'
RUNTIME = ['collector-owner.mjs', 'layout.mjs', 'foreign-module.mjs', 'foreign-binary.mjs', 'bytes.mjs', 'sha256.mjs']
MUTANTS = [
 ('entry-state', 'Atomics.load(words,state)===2', 'true', 'owner-refusal-state'),
 ('lifetime', 'this.#t(8)>0', 'true', 'owner-refusal-lifetime'),
 ('next-worker', 'this.#t(12)===0', 'true', 'owner-refusal-next-worker'),
 ('previous-worker', 'this.#t(16)===0', 'true', 'owner-refusal-previous-worker'),
 ('descriptor-admission', 'this.#t(144)===0&&Atomics.load', 'true&&Atomics.load', 'owner-refusal-descriptor'),
 ('active-request', 'Atomics.load(words,(this.tcr+152)/4)===0', 'true', 'owner-refusal-active-request'),
 ('root-alignment', 'head%8===0', 'true', 'owner-refusal-root-alignment'),
 ('argument-root', 'head+16===this.#t(64)', 'true', 'owner-refusal-argument-head'),
 ('root-count', 'count>=2', 'true', 'owner-refusal-root-count'),
 ('root-capacity', 'contains(v,head,8+4*count)', 'true', 'owner-refusal-root-capacity'),
 ('publish-descriptor', 'this.#set(this.tcr+144,head);', ';', 'owner-return-0'),
 ('publish-foreign', 'Atomics.store(words,state,3);', ';', 'owner-return-0'),
 ('restore-descriptor', 'this.#set(this.tcr+144,0);', ';', 'owner-return-0'),
 ('readmit', 'Atomics.store(words,(this.tcr+32)/4,2);', ';', 'owner-return-0'),
 ('token', 'token===frame.token', 'true', 'owner-refusal-token'),
 ('return-state', 'Atomics.load(words,(this.tcr+32)/4)===3', 'true', 'owner-refusal-return-state'),
 ('return-descriptor', 'this.#t(144)===frame.head', 'true', 'owner-refusal-return-descriptor'),
 ('checkpoint', 'frame.offsets.every((o,i)=>this.#t(o)===frame.values[i])', 'true', 'owner-refusal-return-checkpoint'),
 ('live-entry', "this.#validateLive();\n   // B publishes", ";\n   // B publishes", 'owner-refusal-live-entry'),
 ('live-return', "this.#validateLive();\n   // Allocation bounds", ";\n   // Allocation bounds", 'owner-refusal-live-return'),
 ('collection-state', 'Atomics.load(new Int32Array(this.#memory.buffer),(this.tcr+32)/4)===3', 'true', 'owner-refusal-collection-state'),
]
# Each checkpoint word has its own semantic refusal, including O-165's 17 gaps.
for offset in [8,12,16,64,76,88,116,120,124,128,132,140,148,152,156,160,164]:
    MUTANTS.append(('checkpoint-'+str(offset),
        'frame.offsets.every((o,i)=>this.#t(o)===frame.values[i])',
        'frame.offsets.every((o,i)=>o=='+str(offset)+'||this.#t(o)===frame.values[i])',
        'owner-refusal-checkpoint-'+str(offset)))



def command(args, out, log, check=True, timeout=180, env=None):
    with (out/log).open('w') as stream:
        status = subprocess.run([str(x) for x in args], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                timeout=timeout, env={**os.environ, 'TMPDIR':str(out), **(env or {})}).returncode
    if check and status:
        raise RuntimeError(log+': '+(out/log).read_text()[-4500:])
    return status


def compare(native, report):
    reference = Path(native).read_text()
    text = ''.join(r['text'] for r in report['outputEvents'] if r['channel']==1)
    rows = lambda text: [line for line in text.splitlines() if line.startswith('FR-ROW ')]
    assert report['ready'] and report['targetLoadedFiles']==82, 'ordinary boot/LOAD'
    assert report['postReadyLoads']==[dict(path='/ccl/bin/loader-benchmark.w32fsl',readyBefore=True,value=True)], 'post-READY LOAD'
    assert not report['openFiles'] and not report['abandonedSessions']
    assert reference.count('FR-PASS')==text.count('FR-PASS')==1, 'completion marker'
    assert rows(reference)==rows(text) and len(rows(text))==12, 'Lisp observations'
    result = report['hostExtension']['result']
    assert result['status']=='PASS' and len(result['entries'])==20, 'entry brackets'
    assert len(result['collections'])==13, 'collection count'
    assert all(r['after']==r['before']+1 and r['source']!=r['destination'] and
               r['poisonedBytes']>0 and r['state']==3 for r in result['collections']), 'moving active-FOREIGN collection'
    assert result['failures']==[dict(mode=mode,kind=kind,retired=kind=='trap') for mode,kind in
                               [(2,'exception'),(3,'trap'),(4,'trap'),(5,'host')]], 'failure kinds'
    return dict(status='PASS',native_matched_rows=12,foreign_entries=20,moving_collections=13,
                rows=rows(text),scope='Lisp semantics against native reference; foreign answers/failure policy from fixture declaration')


def run(args):
    out=args.output.resolve()
    with storage.lease([out]):
        storage.reset_run(out)
        (out/'runtime').mkdir()
        sources = ([ROOT/'runtime/wasm32'/name for name in RUNTIME]+
                   [ROOT/'runtime/wasm32/collector.c',ROOT/'runtime/wasm32/host-call-adapter.wat']+
                   sorted(p for p in HERE.iterdir() if p.suffix in ('.mjs','.py','.wat','.lisp'))+
                   [SCALAR/name for name in ('node.mjs','worker.mjs','browser.mjs')]+
                   [ROOT/'tests/wasm/stage1/loader-target'/name for name in ('boot0.mjs','build.py','source-compile.lisp')]+
                   [ROOT/'tests/wasm/stage1/bootstrap-validation'/name for name in ('common.py','storage.py')])
        hashes={str(p.relative_to(ROOT)):c.sha(p) for p in sources}
        c.save(out/'sources.json',hashes)
        for name in RUNTIME: shutil.copy2(ROOT/'runtime/wasm32'/name,out/'runtime'/name)
        shutil.copy2(HERE/'owner-check.mjs',out/'check.mjs')
        for name in ('node.mjs','worker.mjs'):shutil.copy2(SCALAR/name,out/name)
        shutil.copy2(args.boot/'runtime-binaries/collector.wasm',out/'collector.wasm')
        parent=c.read(args.checks/'postimage-parent.json')
        assert parent['source_sha256']==c.sha(HERE/'checks.lisp'), 'compiled fixture source changed'
        assert parent['manifest']==c.sha(args.boot/'boot/artifacts/manifest.json'), 'compiled fixture parent changed'
        c.save(out/'inputs.json',dict(boot=str(args.boot),level1=str(args.level1),checks=str(args.checks),
            manifests={str(p):c.sha(p) for p in [args.boot/'boot/artifacts/manifest.json',args.boot/'sources.json',
             args.level1/'bundle-manifest.json',args.level1/'sources.json',args.checks/'bundle-manifest.json',
             args.checks/'sources.json',args.checks/'benchmark.dx64fsl',c.IMAGE]},
            recipes={str(p):c.read(p) for p in [args.boot/'build-recipe.json',args.level1/'build-recipe.json',args.checks/'build-recipe.json']}))
        try:
            command([c.WABT,HERE/'library.wat','--enable-all','-o',out/'library.wasm'],out,'assembly.log')
            c.save(out/'binaries.json',['collector','library'])
            c.save(out/'artifacts.json',{name:dict(sha256=c.sha(out/(name+'.wasm')),bytes=(out/(name+'.wasm')).stat().st_size)
                                        for name in ('collector','library')})
            c.save(out/'tools.json',{name:dict(path=str(p),sha256=c.sha(p)) for name,p in
                                    [('node',c.NODE),('wat2wasm',c.WABT),('python',Path(sys.executable)),('native-kernel',c.KERNEL)]})
            command([c.NODE,out/'node.mjs',out/'node.json'],out,'node.log')
            original=(out/'runtime/collector-owner.mjs').read_text();controls=[]
            try:
                for name,before,after,case in MUTANTS:
                    assert original.count(before)==1,name
                    (out/'runtime/collector-owner.mjs').write_text(original.replace(before,after))
                    status=command([c.NODE,out/'node.mjs',out/'mutant.json',case],out,'mutant.log',check=False)
                    result=c.read(out/'mutant.json')
                    assert status!=0 and result['status']=='FAIL' and result['error'].startswith('Error: '+case+':'), name
                    assert 'wrong refusal' not in result['error'], 'only changed refusal reason: '+name
                    controls.append(dict(name=name,case=case,status='KILLED',error=result['error'],source_sha256=c.sha(out/'runtime/collector-owner.mjs')))
            finally:
                (out/'runtime/collector-owner.mjs').write_text(original);c.save(out/'mutants.json',controls)
            if args.playwright:
                command([c.NODE,SCALAR/'browser.mjs',out,args.playwright]+([args.browser_config] if args.browser_config else []),out,'browser.log')
                for row in c.read(out/'browser.json')['results']:assert row['rows']==c.read(out/'node.json')['rows'],row['engine']
            command([args.checks/'dx86cl64','-I',c.IMAGE,'--no-init','--batch','--load',args.checks/'benchmark.dx64fsl','--eval','(ccl:quit)'],
                    out,'native.log',env={'CCL_DEFAULT_DIRECTORY':str(ROOT)+'/'})
            command([c.NODE,ROOT/'tests/wasm/stage1/loader-target/boot0.mjs',args.boot,args.boot/'runtime-binaries',
                '--bundles='+str(args.level1),'--bundles='+str(args.checks),
                '--post-ready-load=/ccl/bin/loader-benchmark.w32fsl','--expect-ready',
                '--host-extension='+str(HERE/'extension.mjs'),
                '--extension-config='+json.dumps(dict(library=str(out/'library.wasm'))),
                '--layout='+json.dumps(dict(freeTarget=0)),'--report='+str(out/'lisp.json')],out,'lisp.log')
            c.save(out/'lisp-check.json',compare(out/'native.log',c.read(out/'lisp.json')))
            # Direct dependency: existing owner APIs are unchanged in behavior.
            command([c.NODE,ROOT/'tests/wasm/stage1/loader-target/owner-check.mjs',out/'collector.wasm',out/'owner-regression.json'],out,'owner-regression.log')
            for relative,digest in hashes.items():assert c.sha(ROOT/relative)==digest,relative
            summary=dict(status='PASS',owner_checks=c.read(out/'node.json')['checks'],owner_mutants=len(controls),
                lisp=c.read(out/'lisp-check.json'),browsers=[r['engine'] for r in c.read(out/'browser.json')['results']] if args.playwright else [],
                skips=['compiler corpus deferred until whole FFI layer is complete',
                       'generated Lisp execution in browser providers', 'multi-Worker D5 admission and callback reentry']+
                       ([] if args.playwright else ['owner browser engines not requested']),
                review='NOT_REVIEWED',criterion_credit=False,product_lisp_lines_changed=0)
            c.save(out/'summary.json',summary)
            for p in out.glob('*.wasm'):p.unlink()
            for name in ('mutant.json','mutant.log','assembly.log'):(out/name).unlink(missing_ok=True)
            c.save(out/'.run.json',dict(status='PASS'));print(json.dumps(summary))
        except Exception as error:
            c.save(out/'failure.json',dict(status='FAIL',error=str(error)))
            c.save(out/'failure-inputs.json',[str(p.relative_to(out)) for p in out.glob('*.wasm')])
            c.save(out/'.run.json',dict(status='FAIL'));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('boot','level1','checks'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('/private/tmp/ccl-work/codex/foreign-runtime/run'))
    parser.add_argument('--playwright',type=Path)
    parser.add_argument('--browser-config',type=Path)
    run(parser.parse_args())
