"""Owned byte ranges: real owner/collector, portable controls, loaded Lisp."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
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
MUTANTS = [
 ('buffer-limit','buffers.maximumBytes>0','true','declare-buffer-limit'),
 ('allocate-abi',"signature(declared.get(buffers.allocate))==='[[\"i32\"],[\"i32\"]]'",'true','declare-allocate-abi'),
 ('release-abi',"signature(declared.get(buffers.release))==='[[\"i32\"],[]]'",'true','declare-release-abi'),
 ('range-alias',"JSON.stringify(ranges.get(a.name))===JSON.stringify(ranges.get(b.name))",'true','declare-range-alias'),
 ('range-format',"['read','write','readwrite'].includes(r.access)",'true','declare-range-access'),
 ('encoding',"['bytes','utf-8'].includes(r.encoding)",'true','declare-range-encoding'),
 ('range-distinct','r.pointer!==r.length','true','declare-range-same'),
 ('range-duplicate','!used.has(r.pointer)&&!used.has(r.length)','true','declare-range-duplicate'),
 ('range-index',"e.params[r.pointer]==='i32'",'true','declare-range-index'),
 ('raw-managed','!managedNames.has(name)','true','managed-allocate-alias'),
 ('size-positive','size>0','true','refuse-zero'),
 ('size-limit','size<=buffers.maximumBytes','true','refuse-limit'),
 ('range-length','length<=h.size-offset','true','refuse-read-overflow'),
 ('allocation-null','pointer===0||','', 'allocator-result-1'),
 ('allocation-extent','pointer+size>memory().buffer.byteLength||','', 'allocator-result-2'),
 ('allocation-overlap','[...live].some(h=>pointer<h.pointer+h.size&&h.pointer<pointer+size)','false','allocator-result-3'),
 ('handle-active',"need(h?.active,'HANDLE')","need(h,'HANDLE')",'offset-reuse'),
 ('release-once',"if(!h.active)return false;",';','offset-reuse'),
 ('retire-allocations','for(const h of live)h.active=false;',';', 'call-failure-trap'),
 ('growth-view','const view=(h,offset,length)=>new Uint8Array(memory().buffer,',
  'let cachedBuffer;const view=(h,offset,length)=>new Uint8Array(cachedBuffer??=memory().buffer,','copy-moving-growth-0'),
 ('read-copy','view(owned(handle),offset,length).slice()','view(owned(handle),offset,length)','copy-moving-growth-0'),
 ('utf8-input',"if(r.access!=='write')textRange(h,slice.offset,length,r.encoding);",';','utf8-input'),
 ('utf8-output',"if(r.access!=='read')textRange(h,offset,length,r.encoding);",';','utf8-output'),
 ('fatal-utf8','fatal:true','fatal:false','utf8-input'),
 ('release-invalidate','h.active=false;live.delete(h);','live.delete(h);','release-failure-exception'),
 ('retire-on-free-trap',"error instanceof WebAssembly.RuntimeError||state==='initializing'","state==='initializing'",'release-failure-trap'),
]


def compare(native, report):
    text=''.join(r['text'] for r in report['outputEvents'] if r['channel']==1)
    reference=Path(native).read_text()
    rows=lambda s:[line for line in s.splitlines() if line.startswith('FB-ROW ')]
    assert report['ready'] and report['targetLoadedFiles']==82
    assert report['postReadyLoads']==[dict(path='/ccl/bin/loader-benchmark.w32fsl',readyBefore=True,value=True)]
    assert not report['openFiles'] and not report['abandonedSessions']
    assert text.count('FB-PASS')==reference.count('FB-PASS')==1
    assert rows(text)==rows(reference) and len(rows(text))==7, (rows(text),rows(reference))
    r=report['hostExtension']['result']
    assert len(r['entries'])==38 and len(r['collections'])==26, (len(r['entries']),len(r['collections']))
    assert all(c['source']!=c['destination'] and c['poisonedBytes']>0 and c['state']==3 for c in r['collections'])
    assert [c['kind'] for c in r['cases']]==[None,None,'exception','trap','trap','exception']
    assert [c['releases'] for c in r['cases']]==[2,2,2,0,1,1]
    assert [c['collections'] for c in r['cases']]==[5,5,5,3,4,4]
    return dict(status='PASS',native_matched_rows=7,foreign_entries=38,moving_collections=26,rows=rows(text),
                scope='Lisp octets/root/binding/value/cleanup semantics; declared fixture supplies foreign answers and failure policy')


def run(args):
    out=args.output.resolve()
    with storage.lease([out]):
        storage.reset_run(out)
        (out/'runtime').mkdir()
        sources=([ROOT/'runtime/wasm32'/name for name in runtime.RUNTIME]+
                 [ROOT/'runtime/wasm32/collector.c']+
                 sorted(p for p in HERE.iterdir() if p.suffix in ('.mjs','.py','.wat','.lisp'))+
                 [SCALAR/name for name in ('node.mjs','worker.mjs','browser.mjs')]+
                 [HERE.parent/'foreign-runtime/run.py']+
                 [ROOT/'tests/wasm/stage1/bootstrap-validation'/name for name in ('common.py','storage.py')])
        hashes={str(p.relative_to(ROOT)):c.sha(p) for p in sources}
        c.save(out/'sources.json',hashes)
        shutil.copy2(HERE/'run.py',out/'run-source.py')
        for name in runtime.RUNTIME:shutil.copy2(ROOT/'runtime/wasm32'/name,out/'runtime'/name)
        for name in ('check.mjs','declaration.mjs'):shutil.copy2(HERE/name,out/name)
        for name in ('node.mjs','worker.mjs'):shutil.copy2(SCALAR/name,out/name)
        shutil.copy2(args.boot/'runtime-binaries/collector.wasm',out/'collector.wasm')
        try:
            command([c.WABT,HERE/'library.wat','--enable-all','-o',out/'library.wasm'],out,'assembly.log')
            c.save(out/'binaries.json',['collector','library'])
            c.save(out/'artifacts.json',{name:dict(sha256=c.sha(out/(name+'.wasm')),bytes=(out/(name+'.wasm')).stat().st_size)
                                       for name in ('collector','library')})
            c.save(out/'tools.json',{name:dict(path=str(p),sha256=c.sha(p)) for name,p in
                                    [('node',c.NODE),('wat2wasm',c.WABT),('python',Path(sys.executable)),('native-kernel',c.KERNEL)]})
            command([c.NODE,out/'node.mjs',out/'node.json'],out,'node.log')
            original=(out/'runtime/foreign-module.mjs').read_text();controls=[]
            try:
                for name,before,after,case in MUTANTS:
                    assert original.count(before)==1,name
                    (out/'runtime/foreign-module.mjs').write_text(original.replace(before,after))
                    status=command([c.NODE,out/'node.mjs',out/'mutant.json',case],out,'mutant.log',check=False)
                    result=c.read(out/'mutant.json')
                    assert status!=0 and result['status']=='FAIL' and result['error'].startswith('Error: '+case+':'),name
                    assert 'wrong refusal' not in result['error'], 'reason-only or late refusal: '+name
                    controls.append(dict(name=name,case=case,status='KILLED',error=result['error'],source_sha256=c.sha(out/'runtime/foreign-module.mjs')))
            finally:
                (out/'runtime/foreign-module.mjs').write_text(original);c.save(out/'mutants.json',controls)
            if args.playwright:
                command([c.NODE,SCALAR/'browser.mjs',out,args.playwright]+([args.browser_config] if args.browser_config else []),out,'browser.log')
                for row in c.read(out/'browser.json')['results']:assert row['rows']==c.read(out/'node.json')['rows'],row['engine']
            lisp=None
            if args.checks:
                parent=c.read(args.checks/'postimage-parent.json')
                assert parent['source_sha256']==c.sha(HERE/'checks.lisp')
                assert parent['manifest']==c.sha(args.boot/'boot/artifacts/manifest.json')
                c.save(out/'inputs.json',dict(boot=str(args.boot),level1=str(args.level1),checks=str(args.checks),
                    manifests={str(p):c.sha(p) for p in [args.boot/'boot/artifacts/manifest.json',args.boot/'sources.json',
                     args.level1/'bundle-manifest.json',args.level1/'sources.json',args.checks/'bundle-manifest.json',
                     args.checks/'sources.json',args.checks/'benchmark.dx64fsl',c.IMAGE]},
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
                       'multi-Worker D5, callbacks, queued finalization and product Lisp API']+
                      ([] if args.playwright else ['browser engines not requested'])+([] if args.checks else ['generated Lisp not requested']),
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
    for name in ('boot','level1','checks'):parser.add_argument('--'+name,type=Path,required=name=='boot')
    parser.add_argument('--output',type=Path,default=Path('/private/tmp/ccl-work/codex/foreign-buffers/run'))
    parser.add_argument('--playwright',type=Path)
    parser.add_argument('--browser-config',type=Path)
    args=parser.parse_args()
    if args.checks and not args.level1:parser.error('--checks requires --level1')
    run(args)
