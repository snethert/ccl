"""Named foreign libraries and the product Lisp API, on verified RAM storage."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT/'tests/wasm/stage1/bootstrap-validation'))
import common as c
import storage
spec = importlib.util.spec_from_file_location('foreign_runtime', HERE.parent/'foreign-runtime/run.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
command = runtime.command
SCALAR = HERE.parent/'foreign-scalar'
RUNTIME = runtime.RUNTIME + ['namespace.mjs', 'foreign-libraries.mjs', 'foreign-service.mjs']
MUTANTS = [
 ('foreign-service.mjs','string-limit','n<=4096','true','service-string-limit'),
 ('foreign-service.mjs','integer-empty','n>0&&','', 'service-integer-empty'),
 ('foreign-service.mjs','vector-arity',"o.n===n",'true','service-refuse-request-extra'),
 ('foreign-service.mjs','token-configuration','maximumTokens>0','true','service-token-configuration-0'),
 ('foreign-service.mjs','request-reload','const op=fix(get(args+4)),payload=()=>get(args+8)', 'const old=get(args+8),op=fix(get(args+4)),payload=()=>old','service-scalars-moving-0'),
 ('foreign-service.mjs','character-surrogate','(ch<0xd800||ch>0xdfff)','true','service-character'),
 ('foreign-service.mjs','float-shape',"n===(type==='f32'?1:3)",'true','service-float-shape'),
 ('foreign-service.mjs','reentry','if(busy) return -4;',';','service-reentry'),
 ('foreign-libraries.mjs','once',"if(row.library){need(row.library.state==='ready','RETIRED');return row.library;}",';','namespace-once'),
 ('foreign-libraries.mjs','snapshot','structuredClone(entry.declaration)','entry.declaration','namespace-snapshot'),
 ('foreign-libraries.mjs','path-alias','!paths.has(path)','true','namespace-duplicate-path'),
 ('foreign-libraries.mjs','size','stat.size<=maximumBytes','true','namespace-size'),
 ('foreign-libraries.mjs','close','session.close(fd);',';','namespace-descriptor-close'),
 ('foreign-libraries.mjs','failed',"row.state!=='failed'&&",'','namespace-initialization-failure'),
 ('foreign-libraries.mjs','closed',"row.state!=='closed'",'true','namespace-close-unopened'),
 ('foreign-service.mjs','signed-integer','value=BigInt.asIntN(n*32,value);',';','service-scalars-moving-0'),
 ('foreign-service.mjs','negative-zero',"v.setFloat32(4,value,true)","v.setFloat32(4,value||0,true)",'service-scalars-moving-0'),
 ('foreign-service.mjs','range-token-limit',"offset=fix(field(1));capacity();","offset=fix(field(1));",'service-range-token-limit'),
 ('foreign-service.mjs','buffer-token-limit',"size=fix(field(1));capacity();","size=fix(field(1));",'service-token-limit'),
 ('foreign-service.mjs','copy-out',"bytes.set(t.library.read(t.handle,offset,n))","t.library.read(t.handle,offset,n)",'service-buffer-moving'),
 ('foreign-service.mjs','close-library',"libraries.close(t.name);",';','service-close'),
]

spec = importlib.util.spec_from_file_location('finalizer_mutants', HERE.parent/'foreign-finalizers/mutants.py')
finalizers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(finalizers)
MUTANTS += finalizers.MUTANTS
spec = importlib.util.spec_from_file_location("string_mutants", HERE.parent/"foreign-strings/mutants.py")
strings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strings)
MUTANTS += strings.MUTANTS

spec = importlib.util.spec_from_file_location('lisp_callback_mutants', HERE.parent/'foreign-lisp-callbacks/mutants.py')
callbacks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(callbacks)
MUTANTS += callbacks.MUTANTS

def compile_collector(path, out):
    command(['/usr/local/opt/llvm/bin/clang', '--target=wasm32', '-O2', '-nostdlib', '-fno-builtin',
        '-matomics', '-mbulk-memory', '-Wl,--no-entry', '-Wl,--import-memory', '-Wl,--shared-memory',
        '-Wl,--max-memory=2147549184', '-Wl,--global-base=1048576', '-Wl,-z,stack-size=65536',
        '-Wl,--export=collect', '-Wl,--export=weak_forward', '-Wl,--export=__stack_pointer',
        path, '-o', out/'collector.wasm'],out,'collector-build.log')


def compare(native, report):
    text=''.join(r['text'] for r in report['outputEvents'] if r['channel']==1)
    rows=lambda s:[line for line in s.splitlines() if line.startswith('FA-ROW ')]
    reference=Path(native).read_text()
    assert report['ready'] and report['targetLoadedFiles']==82
    assert report['postReadyLoads']==[dict(path='/ccl/bin/loader-benchmark.w32fsl',readyBefore=True,value=True)]
    assert not report['openFiles'] and not report['abandonedSessions']
    assert text.count('FA-PASS')==reference.count('FA-PASS')==1
    assert rows(text)==rows(reference) and len(rows(text))==20, (rows(text),rows(reference))
    r=report['hostExtension']['result']
    assert r['events'].count(1)==7, r['events']
    assert all(c['source']!=c['destination'] and c['state']==3 for c in r['collections'])
    assert len(r['collections'])>=25
    final_rows=lambda s:[line for line in s.splitlines() if line.startswith('FF-ROW ')]
    assert final_rows(text)==final_rows(reference) and len(final_rows(text))==10, (final_rows(text),final_rows(reference))
    assert text.count('FF-PASS')==reference.count('FF-PASS')==1
    string_rows=lambda s:[line for line in s.splitlines() if line.startswith('FS-ROW ')]
    assert string_rows(text)==string_rows(reference) and len(string_rows(text))==15, (string_rows(text),string_rows(reference))
    assert text.count('FS-PASS')==reference.count('FS-PASS')==1
    callback_rows=lambda s:[line for line in s.splitlines() if line.startswith('FC-ROW ')]
    expected_callbacks = [
        'FC-ROW CLOSURE 42', 'FC-ROW MOVED 44', 'FC-ROW TWICE 45',
        'FC-ROW DEREGISTER (T NIL)', 'FC-ROW STALE :CAUGHT', 'FC-ROW SAVED -1',
        'FC-ROW SCALARS (-2147483648 -9223372036854775808 T T)',
        'FC-ROW ERROR :CAUGHT', 'FC-ROW ERROR-CLEANUP (1 1 :OUTSIDE)',
        'FC-ROW AFTER-ERROR 4', 'FC-ROW THROW :CONTAINED', 'FC-ROW THROW-CLEANUP 1',
        'FC-ROW RETURN-FROM :CONTAINED', 'FC-ROW VOID (NIL 1)',
        'FC-ROW NOT-FUNCTION :CAUGHT', 'FC-ROW REGISTRATION-ONLY-ROOT 307']
    assert callback_rows(text)==callback_rows(reference)==expected_callbacks, (callback_rows(text),callback_rows(reference))
    assert text.count('FC-PASS')==reference.count('FC-PASS')==1
    assert len(r['callbackCollections'])==9 and all(c['source']!=c['destination'] for c in r['callbackCollections'])
    return dict(status='PASS',callback_rows=callback_rows(text),string_rows=string_rows(text),native_matched_rows=len(rows(text))+len(final_rows(text))+len(string_rows(text))+len(callback_rows(text)),finalizer_rows=final_rows(text),foreign_entries=len(r['entries']),callback_collections=len(r['callbackCollections']),
                moving_collections=len(r['collections']),initializations=r['events'].count(1),releases=r['events'].count(2),rows=rows(text),
                scope='Product Lisp API and service; native oracle models fixture library operations')


def run(args):
    out=args.output.resolve()
    with storage.lease([out]):
        storage.reset_run(out)
        (out/'runtime').mkdir()
        sources=([ROOT/'runtime/wasm32'/name for name in RUNTIME+['foreign-api.lisp','process-service.mjs','collector.c']]+
                 sorted(p for p in HERE.iterdir() if p.suffix in ('.mjs','.py','.wat','.lisp'))+
                 [SCALAR/name for name in ('node.mjs','worker.mjs','browser.mjs')]+
                 [HERE.parent/'foreign-lisp-callbacks'/name for name in ('checks.lisp','check.mjs','bridge.wat','mutants.py')]+
                 [HERE.parent/'foreign-strings'/name for name in ('check.mjs','checks.lisp','mutants.py')]+
                 [HERE.parent/'foreign-runtime/run.py',HERE.parent/'foreign-finalizers/check.mjs',HERE.parent/'foreign-finalizers/checks.lisp',HERE.parent/'foreign-finalizers/mutants.py']+
                 [ROOT/'tests/wasm/stage1/loader-target'/name for name in ('build.py','source-compile.lisp','boot0.mjs')]+
                 [ROOT/'tests/wasm/stage1/bootstrap-validation'/name for name in ('common.py','storage.py')])
        hashes={str(p.relative_to(ROOT)):c.sha(p) for p in sources}
        c.save(out/'sources.json',hashes)
        for name in RUNTIME+['collector.c']:shutil.copy2(ROOT/'runtime/wasm32'/name,out/'runtime'/name)
        for name in ('check.mjs','declaration.mjs'):shutil.copy2(HERE/name,out/name)
        shutil.copy2(HERE.parent/'foreign-finalizers/check.mjs',out/'finalizers.mjs')
        shutil.copy2(HERE.parent/'foreign-strings/check.mjs',out/'strings.mjs')
        shutil.copy2(HERE.parent/'foreign-lisp-callbacks/check.mjs',out/'lisp-callbacks.mjs')
        for name in ('node.mjs','worker.mjs'):shutil.copy2(SCALAR/name,out/name)
        shutil.copy2(args.boot/'runtime-binaries/collector.wasm',out/'collector.wasm')
        try:
            command([c.WABT,HERE/'library.wat','--enable-all','-o',out/'library.wasm'],out,'assembly.log')
            command([c.WABT,HERE.parent/'foreign-lisp-callbacks/bridge.wat','--enable-all','-o',out/'bridge.wasm'],out,'bridge-assembly.log')
            c.save(out/'binaries.json',['collector','library','bridge'])
            c.save(out/'artifacts.json',{name:dict(sha256=c.sha(out/(name+'.wasm')),bytes=(out/(name+'.wasm')).stat().st_size)
                                       for name in ('collector','library','bridge')})
            c.save(out/'tools.json',{name:dict(path=str(p),sha256=c.sha(p)) for name,p in
                                    [('clang',Path('/usr/local/opt/llvm/bin/clang')),('node',c.NODE),('wat2wasm',c.WABT),('python',Path(sys.executable)),('native-kernel',c.KERNEL)]})
            command([c.NODE,out/'node.mjs',out/'node.json'],out,'node.log')
            controls=[]
            for file,name,before,after,case in MUTANTS:
                path=out/'runtime'/file;original=path.read_text()
                try:
                    assert original.count(before)==1,name
                    path.write_text(original.replace(before,after))
                    if file=='collector.c':compile_collector(path,out)
                    status=command([c.NODE,out/'node.mjs',out/'mutant.json',case],out,'mutant.log',check=False)
                    result=c.read(out/'mutant.json')
                    assert status!=0 and result['status']=='FAIL' and result['error'].startswith('Error: '+case+':'),name
                    assert 'wrong refusal' not in result['error'], 'reason-only or late refusal: '+name
                    controls.append(dict(name=name,case=case,status='KILLED',error=result['error'],source_sha256=c.sha(path)))
                finally:
                    path.write_text(original);c.save(out/'mutants.json',controls)
                    if file=='collector.c':shutil.copy2(args.boot/'runtime-binaries/collector.wasm',out/'collector.wasm')
            if args.playwright:
                command([c.NODE,SCALAR/'browser.mjs',out,args.playwright]+([args.browser_config] if args.browser_config else []),out,'browser.log')
                for row in c.read(out/'browser.json')['results']:assert row['rows']==c.read(out/'node.json')['rows'],row['engine']
            lisp=None
            if args.checks:
                combined=(ROOT/'runtime/wasm32/foreign-api.lisp').read_text()+'\n'+(HERE/'checks.lisp').read_text()+'\n'+(HERE.parent/'foreign-finalizers/checks.lisp').read_text()+'\n'+(HERE.parent/'foreign-strings/checks.lisp').read_text()+'\n'+(HERE.parent/'foreign-lisp-callbacks/checks.lisp').read_text()
                parent=c.read(args.checks/'postimage-parent.json')
                assert parent['source_sha256']==hashlib.sha256(combined.encode()).hexdigest()
                assert parent['manifest']==c.sha(args.boot/'boot/artifacts/manifest.json')
                c.save(out/'inputs.json',dict(boot=str(args.boot),level1=str(args.level1),checks=str(args.checks),
                    manifests={str(p):c.sha(p) for p in [args.boot/'boot/artifacts/manifest.json',args.boot/'sources.json',
                     args.level1/'bundle-manifest.json',args.level1/'sources.json',args.checks/'bundle-manifest.json',args.checks/'sources.json',c.IMAGE]},
                    recipes={str(p):c.read(p) for p in [args.boot/'build-recipe.json',args.level1/'build-recipe.json',args.checks/'build-recipe.json']}))
                command([args.checks/'dx86cl64','-I',c.IMAGE,'--no-init','--batch','--load',args.checks/'benchmark.dx64fsl','--eval','(ccl:quit)'],out,'native.log',
                        env={'CCL_DEFAULT_DIRECTORY':str(ROOT)+'/'})
                command([c.NODE,ROOT/'tests/wasm/stage1/loader-target/boot0.mjs',args.boot,args.boot/'runtime-binaries',
                    '--bundles='+str(args.level1),'--bundles='+str(args.checks),'--post-ready-load=/ccl/bin/loader-benchmark.w32fsl','--expect-ready',
                    '--host-extension='+str(HERE/'extension.mjs'),'--extension-config='+json.dumps(dict(library=str(out/'library.wasm'))),
                    '--layout='+json.dumps(dict(freeTarget=0)),'--report='+str(out/'lisp.json')],out,'lisp.log')
                lisp=compare(out/'native.log',c.read(out/'lisp.json'));c.save(out/'lisp-check.json',lisp)
            for relative,digest in hashes.items():assert c.sha(ROOT/relative)==digest,relative
            summary=dict(status='PASS',checks=c.read(out/'node.json')['checks'],mutants=len(controls),lisp=lisp,
                browsers=[r['engine'] for r in c.read(out/'browser.json')['results']] if args.playwright else [],
                skips=['compiler corpus deferred until whole FFI layer is complete','generated Lisp in browser providers',
                       'multi-Worker D5, nested foreign calls, non-simple strings and other encodings']+
                      ([] if args.playwright else ['browser engines not requested'])+([] if args.checks else ['generated Lisp not requested']),
                review='NOT_REVIEWED',criterion_credit=False,product_lisp_lines_changed=25,product_lisp_lines_total=len((ROOT/'runtime/wasm32/foreign-api.lisp').read_text().splitlines()))
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
    for name in ('boot','level1','checks'):parser.add_argument('--'+name,type=Path,required=name=='boot')
    parser.add_argument('--output',type=Path,default=Path('/private/tmp/ccl-work/codex/foreign-api/run'))
    parser.add_argument('--playwright',type=Path)
    parser.add_argument('--browser-config',type=Path)
    args=parser.parse_args()
    if args.checks and not args.level1:parser.error('--checks requires --level1')
    run(args)
