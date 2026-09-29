"""Run the existing FOREIGN owner cases and controls without rebuilding Lisp."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('callbacks', HERE/'run.py')
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)
c, storage, command = cb.c, cb.storage, cb.command
runtime = cb.api.runtime


def run(args):
    out=args.output.resolve()
    with storage.lease([out]):
        storage.reset_run(out)
        (out/'runtime').mkdir()
        source_paths=([cb.ROOT/'runtime/wasm32'/name for name in runtime.RUNTIME]+[cb.ROOT/'runtime/wasm32/collector.c']+
            [HERE.parent/'foreign-runtime'/name for name in ('owner-check.mjs','library.wat','run.py')]+
            [cb.SCALAR/name for name in ('node.mjs','worker.mjs','browser.mjs')]+
            [cb.ROOT/'tests/wasm/stage1/loader-target/owner-check.mjs',Path(__file__)])
        sources={str(p.relative_to(cb.ROOT)):c.sha(p) for p in source_paths}
        c.save(out/'sources.json',sources)
        for name in runtime.RUNTIME:shutil.copy2(cb.ROOT/'runtime/wasm32'/name,out/'runtime'/name)
        shutil.copy2(HERE.parent/'foreign-runtime/owner-check.mjs',out/'check.mjs')
        for name in ('node.mjs','worker.mjs'):shutil.copy2(cb.SCALAR/name,out/name)
        try:
            cb.api.compile_collector(cb.ROOT/'runtime/wasm32/collector.c',out)
            command([c.WABT,HERE.parent/'foreign-runtime/library.wat','--enable-all','-o',out/'library.wasm'],out,'assembly.log')
            c.save(out/'binaries.json',['collector','library'])
            c.save(out/'artifacts.json',{name:c.sha(out/(name+'.wasm')) for name in ('collector','library')})
            c.save(out/'tools.json',{name:dict(path=str(p),sha256=c.sha(p)) for name,p in
                    [('node',c.NODE),('clang',Path('/usr/local/opt/llvm/bin/clang')),('wat2wasm',c.WABT)]})
            command([c.NODE,out/'node.mjs',out/'node.json'],out,'node.log')
            controls=[];path=out/'runtime/collector-owner.mjs';original=path.read_text()
            try:
                for name,before,after,case in runtime.MUTANTS:
                    assert original.count(before)==1,name
                    path.write_text(original.replace(before,after))
                    status=command([c.NODE,out/'node.mjs',out/'mutant.json',case],out,'mutant.log',check=False)
                    result=c.read(out/'mutant.json')
                    assert status!=0 and result['status']=='FAIL' and result['error'].startswith('Error: '+case+':'),name
                    assert 'wrong refusal' not in result['error'],name
                    controls.append(dict(name=name,case=case,status='KILLED',error=result['error'],source_sha256=c.sha(path)))
            finally:
                path.write_text(original);c.save(out/'mutants.json',controls)
            if args.playwright:
                command([c.NODE,cb.SCALAR/'browser.mjs',out,args.playwright]+([args.browser_config] if args.browser_config else []),out,'browser.log')
                for r in c.read(out/'browser.json')['results']:assert r['rows']==c.read(out/'node.json')['rows']
            command([c.NODE,cb.ROOT/'tests/wasm/stage1/loader-target/owner-check.mjs',out/'collector.wasm',out/'collector-owner.json'],out,'collector-owner.log')
            for path,digest in sources.items():assert c.sha(cb.ROOT/path)==digest,path
            summary=dict(status='PASS',checks=c.read(out/'node.json')['checks'],mutants=len(controls),
                         collector_owner=c.read(out/'collector-owner.json'))
            c.save(out/'summary.json',summary)
            for p in out.glob('*.wasm'):p.unlink()
            for name in ('mutant.json','mutant.log'):(out/name).unlink(missing_ok=True)
            c.save(out/'.run.json',dict(status='PASS'));print(json.dumps({k:v for k,v in summary.items() if k!='collector_owner'}))
        except Exception as error:
            c.save(out/'failure.json',dict(status='FAIL',error=str(error)))
            c.save(out/'failure-inputs.json',[str(p.relative_to(out)) for p in out.glob('*.wasm')])
            c.save(out/'.run.json',dict(status='FAIL'));raise

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path('/private/tmp/ccl-work/codex/foreign-callback-owner/run'))
    parser.add_argument('--playwright',type=Path)
    parser.add_argument('--browser-config',type=Path)
    run(parser.parse_args())
