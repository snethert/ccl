"""Typed callback boundary, on leased RAM storage; no compiler corpus replay."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT/'tests/wasm/stage1/bootstrap-validation'))
import common as c
import storage
spec = importlib.util.spec_from_file_location('api_driver', HERE.parent/'foreign-api/run.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
command = api.command
SCALAR = HERE.parent/'foreign-scalar'
RUNTIME = api.RUNTIME
spec = importlib.util.spec_from_file_location('callback_mutants', HERE/'mutants.py')
mutants = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mutants)


def run(args):
    out = args.output.resolve()
    with storage.lease([out]):
        storage.reset_run(out)
        (out/'runtime').mkdir()
        sources = ([ROOT/'runtime/wasm32'/name for name in RUNTIME+['collector.c']]+
                   sorted(p for p in HERE.iterdir() if p.suffix in ('.mjs','.py','.wat'))+
                   [SCALAR/name for name in ('node.mjs','worker.mjs','browser.mjs')]+
                   [HERE.parent/'foreign-api/run.py',HERE.parent/'foreign-runtime/run.py']+
                   [ROOT/'tests/wasm/stage1/bootstrap-validation'/name for name in ('common.py','storage.py')])
        hashes = {str(p.relative_to(ROOT)):c.sha(p) for p in sources}
        c.save(out/'sources.json',hashes)
        for name in RUNTIME:shutil.copy2(ROOT/'runtime/wasm32'/name,out/'runtime'/name)
        for name in ('check.mjs','setup.mjs','declaration.mjs'):shutil.copy2(HERE/name,out/name)
        for name in ('node.mjs','worker.mjs'):shutil.copy2(SCALAR/name,out/name)
        try:
            api.compile_collector(ROOT/'runtime/wasm32/collector.c',out)
            command([c.WABT,HERE/'library.wat','--enable-all','-o',out/'library.wasm'],out,'assembly.log')
            (out/'hidden.wat').write_text((HERE/'library.wat').read_text().replace('(table (export "callbacks")','(table'))
            command([c.WABT,out/'hidden.wat','--enable-all','-o',out/'hidden.wasm'],out,'hidden-assembly.log')
            (out/'hidden.wat').unlink()
            c.save(out/'binaries.json',['collector','library','hidden'])
            c.save(out/'artifacts.json',{name:dict(sha256=c.sha(out/(name+'.wasm')),bytes=(out/(name+'.wasm')).stat().st_size)
                                       for name in ('collector','library','hidden')})
            c.save(out/'tools.json',{name:dict(path=str(p),sha256=c.sha(p)) for name,p in
                        [('clang',Path('/usr/local/opt/llvm/bin/clang')),('node',c.NODE),('wat2wasm',c.WABT),('python',Path(sys.executable))]})
            command([c.NODE,out/'node.mjs',out/'node.json'],out,'node.log')
            controls=[]
            for file,name,before,after,case in mutants.MUTANTS:
                path=out/'runtime'/file;original=path.read_text()
                try:
                    assert original.count(before)==1,(name,original.count(before))
                    path.write_text(original.replace(before,after))
                    status=command([c.NODE,out/'node.mjs',out/'mutant.json',case],out,'mutant.log',check=False)
                    result=c.read(out/'mutant.json')
                    assert status!=0 and result['status']=='FAIL' and result['error'].startswith('Error: '+case+':'),name
                    assert 'wrong refusal' not in result['error'],'reason-only or late refusal: '+name
                    controls.append(dict(name=name,case=case,status='KILLED',error=result['error'],source_sha256=c.sha(path)))
                finally:
                    path.write_text(original);c.save(out/'mutants.json',controls)
            if args.playwright:
                command([c.NODE,SCALAR/'browser.mjs',out,args.playwright]+([args.browser_config] if args.browser_config else []),out,'browser.log')
                for row in c.read(out/'browser.json')['results']:assert row['rows']==c.read(out/'node.json')['rows'],row['engine']
            for relative,digest in hashes.items():assert c.sha(ROOT/relative)==digest,relative
            summary=dict(status='PASS',checks=c.read(out/'node.json')['checks'],mutants=len(controls),
                browsers=[r['engine'] for r in c.read(out/'browser.json')['results']] if args.playwright else [],
                skips=['generated Lisp callback invocation and Lisp API','multi-Worker D5 admission',
                       'nested foreign calls from callbacks','compiler corpus deferred until whole FFI layer is complete'],
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
    parser.add_argument('--output',type=Path,default=Path('/private/tmp/ccl-work/codex/foreign-callbacks/run'))
    parser.add_argument('--playwright',type=Path)
    parser.add_argument('--browser-config',type=Path)
    run(parser.parse_args())
