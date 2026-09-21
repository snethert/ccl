import argparse, importlib.util, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from backend import generate
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
EVIDENCE=ROOT.parent/'ccl-evidence'
def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
def chunks():
    rows=[]
    for directory in ('level-0','level-1'):
        for path in sorted((ROOT/directory).glob('*.lisp')):
            text=path.read_text()
            rows.append([str(path.relative_to(ROOT)), 0, text])
    return rows

def compile_proposal(out):
    driver=out/'driver'
    shutil.copytree(ROOT/'tests/wasm/stage1/constants',driver,ignore=shutil.ignore_patterns('__pycache__'))
    (driver/'entry-cases.lisp').write_text((HERE/'cases.lisp').read_text())
    rows=chunks()
    save(out/'source-chunks.json',rows)
    (driver/'source-chunks.lisp').write_text("'("+'\n'.join('('+json.dumps(p)+' '+str(i)+' '+('"'+s.replace('\\','\\\\').replace('"','\\"')+'"')+')' for p,i,s in rows)+')\n')
    for name in ('compile.lisp','measure.lisp','controls.lisp','legacy.lisp'):
        shutil.copy(HERE/name,driver/name)
    p=driver/'compile.py'
    p.write_text(p.read_text().replace("ROOT=HERE.parents[3];REG=HERE.parent/'registration'",f"ROOT=Path({str(ROOT)!r});REG=ROOT/'tests/wasm/stage1/registration'"))
    sys.path.insert(0,str(driver))
    spec=importlib.util.spec_from_file_location('bootstrap_compile',p)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.run(EVIDENCE,out/'compiled',generate())
    import encode
    encode.Encoder.__init__.__defaults__=(ROOT/'doc/WASM/contracts/wasm32-layout.v1.json',16*1024*1024)
    from pool import compile_pool
    mat=compile_pool(json.loads((out/'compiled/pools.json').read_text())).at(2097152)
    save(out/'compiled/materialized.json',dict(image=mat.image.hex(),roots=mat.roots))

def compare_legacy(out):
    driver=out/'baseline-driver'
    shutil.copytree(out/'driver',driver)
    (driver/'compile.lisp').write_text('(in-package :wasm32-compiler)\n(load (merge-pathnames "legacy.lisp" *load-pathname*))\n(frontend-legacy (ccl:getenv "POOL_OUTPUT"))\n(format t "POOL-COMPILE-PASS~%") (ccl:quit)\n')
    spec=importlib.util.spec_from_file_location('bootstrap_baseline',driver/'compile.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.run(EVIDENCE,out/'baseline',(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text())
    files=sorted(p.name for p in (out/'baseline').glob('*.legacy'))
    assert files and files==sorted(p.name for p in (out/'compiled').glob('*.legacy'))
    for name in files:assert (out/'compiled'/name).read_bytes()==(out/'baseline'/name).read_bytes(),name
    save(out/'legacy.json',dict(status='PASS',identical_files=files))

def run(out):
    out.mkdir(parents=True,exist_ok=False)
    compile_proposal(out)
    compare_legacy(out)
    flags=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect']
    subprocess.run(['/usr/local/opt/llvm/bin/clang',*flags,ROOT/'runtime/wasm32/collector.c','-o',out/'collector.wasm'],check=True)
    for n in ('install.mjs','check.mjs'):shutil.copy(HERE/n,out/n)
    subprocess.run(['/usr/local/bin/node',out/'check.mjs',out,out/'execution.json'],check=True)
    throughput=json.loads((out/'compiled/throughput.json').read_text())
    execution=json.loads((out/'execution.json').read_text())
    save(out/'summary.json',dict(status='PASS',inventory_functions=len(throughput['functions']),
        baseline_admitted=sum(r['baseline']=='admitted' for r in throughput['functions']),
        proposal_admitted=sum(r['proposal']=='admitted' for r in throughput['functions']),
        reader_and_name_skips=len(throughput['skips']),executed_original_definitions=4,
        native_cases=len(json.loads((out/'compiled/native.json').read_text())),
        comparisons=sum(r['comparisons'] for r in execution['rows']),
        collections=sum(r['collections'] for r in execution['rows']),
        modules=len(json.loads((out/'compiled/modules.json').read_text())),
        legacy_identical=len(json.loads((out/'legacy.json').read_text())['identical_files']),
        admission_controls=len(json.loads((out/'compiled/admission.json').read_text()))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    run(p.parse_args().output.resolve())
