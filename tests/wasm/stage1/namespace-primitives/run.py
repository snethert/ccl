#!/usr/bin/env python3
from pathlib import Path
import argparse
import importlib.util
import json
import os
import shutil
import sys
import time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage

def lisp(x):
    if isinstance(x,list):return '('+' '.join(map(lisp,x))+')'
    if isinstance(x,str):return '"'+x.replace('\\','\\\\').replace('"','\\"')+'"'
    return str(x)

def execution_inputs():
    paths=[p for p in c.files(HERE) if p.suffix in ('.py','.lisp','.mjs','.wat','.json')]
    paths+=c.files(c.ROOT/'runtime/wasm32')
    paths+=[p for p in c.files(HERE.parent/'namespace') if p.suffix in ('.py','.mjs','.lisp')]
    for directory in ('integrated-runtime','runtime-boundary'):
        paths+=c.files(c.ROOT/'tests/wasm/stage0'/directory)
    paths+=[HERE.parent/n for n in ('ready-runtime-acceptance/check.py','ready-acceptance/check.py','ready/worker.mjs')]
    paths+=[c.ROOT/'doc/WASM/stage1/acceptance-ready-runtime.json']
    paths+=[c.ROOT/n for n in ('compiler/WASM32/wasm32-backend.lisp','compiler/WASM32/wasm32-arch.lisp',
        'lib/systems.lisp','lib/compile-ccl.lisp','xdump/xwasm32-fasload.lisp',
        'doc/WASM/contracts/wasm32-layout.v1.json','doc/WASM/contracts/tcr.v2.json')]
    paths+=[HERE.parent/n for n in ('registration/load.lisp','constants/export.lisp','constants/encode.py','constants/pool.py',
        'bootstrap-values/extra.lisp','bootstrap-validation/driver/whole-file.lisp','bootstrap-validation/common.py','bootstrap-validation/storage.py')]
    return {str(p.relative_to(c.ROOT)):c.sha(p) for p in sorted(set(paths))}


def run(out, reuse=False):
    if (out/'summary.json').exists():raise ValueError('Do not overwrite completed execution')
    out.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    inputs=execution_inputs()
    spec=importlib.util.spec_from_file_location('file_compile',HERE/'compile.py')
    compile=importlib.util.module_from_spec(spec);spec.loader.exec_module(compile)
    compile_start=time.monotonic()
    if not reuse:compile.run(out/'compiled')
    compile_seconds=time.monotonic()-compile_start
    runtime_start=time.monotonic()
    c.command(['/usr/local/opt/llvm/bin/clang','--target=wasm32','-O2','-nostdlib','-fno-builtin','-matomics','-mbulk-memory',
      '-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,--shared-memory',
      '-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer',
      c.ROOT/'runtime/wasm32/collector.c','-o',out/'collector.wasm'],out/'collector-build.log')
    c.command(['/usr/local/opt/llvm/bin/clang','--target=wasm32','-O2','-nostdlib','-fno-builtin',
      '-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=65536',
      '-Wl,-z,stack-size=65536','-Wl,--export=integer_calculate','-Wl,--export=integer_workspace_bytes',
      c.ROOT/'runtime/wasm32/integer.c','-o',out/'integer.wasm'],out/'integer-build.log')
    c.command([sys.executable,c.ROOT/'runtime/wasm32/build-float.py','--output',out],out/'float-build.log')
    c.command([c.WABT,*c.FLAGS,c.ROOT/'runtime/wasm32/float-detector.wat','-o',out/'detector.wasm'],out/'detector.log')
    c.command([c.WABT,*c.FLAGS,HERE/'adapter.wat','-o',out/'adapter.wasm'],out/'adapter.log')
    runtime_seconds=time.monotonic()-runtime_start
    (out/'runtime').mkdir(exist_ok=True)
    shutil.copyfile(HERE.parent/'namespace/namespace.mjs',out/'runtime/namespace.mjs')
    for name in ('sha256.mjs','bytes.mjs'):shutil.copyfile(c.ROOT/'runtime/wasm32'/name,out/'runtime'/name)
    c.command([c.NODE,HERE.parent/'namespace/prepare.mjs',out],out/'prepare.log')
    c.command([c.NODE,'--input-type=module','-e',
        "import fs from 'node:fs'; import {largeFile} from '"+(HERE/'fixtures.mjs').as_uri()+"'; "
        "fs.writeFileSync(process.argv[1],largeFile);",out/'native-tree/ccl/large.bin'],out/'large-file.log')
    shutil.copyfile(HERE/'cases.json',out/'cases.json')
    (out/'cases.lisp').write_text(lisp(c.read(HERE/'cases.json'))+'\n')
    env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(c.ROOT)+'/',FILES_SOURCE=str(HERE)+'/',
             NAMESPACE_ROOT=str(out/'native-tree'),FILES_CASES=str(out/'cases.lisp'),FILES_NATIVE=str(out/'native.json'))
    times={'compiler_process':c.read(out/'compiled/compile-completion.json')['seconds'],
           'compile_and_assembly':compile_seconds,'runtime_builds':runtime_seconds}
    times['native']=c.command([out/'compiled/dx86cl64','-I',c.IMAGE,'--no-init','--batch','--load',HERE/'native.lisp'],out/'native.log',env,timeout=60)
    # Native runner emits compact rows; preserve arguments and every result.
    rows=c.read(out/'native.json')
    c.save(out/'native.json',[dict(op=op,args=args,value=value) for op,args,value in rows])
    times['target']=c.command([c.NODE,HERE/'check.mjs',out],out/'target.log',timeout=120)
    times['controls']=c.command([c.NODE,HERE/'controls.mjs',out],out/'controls.log',timeout=60)
    fault_spec=importlib.util.spec_from_file_location('namespace_faults',HERE/'faults.py')
    faults=importlib.util.module_from_spec(fault_spec);fault_spec.loader.exec_module(faults)
    fault_start=time.monotonic()
    fault_rows=faults.run(out)
    times['faults']=time.monotonic()-fault_start
    from audit176 import run as audit
    audit_start=time.monotonic();audit(out);times['audit176']=time.monotonic()-audit_start
    result=c.read(out/'execution.json')
    times['total']=time.monotonic()-started
    assert inputs==execution_inputs(),'Sources changed during execution'
    c.save(out/'summary.json',dict(status='PASS',modules=12,comparisons=result['comparisons'],
        bounded_reads=result['bounded_reads'],
        execution_inputs=inputs,fresh_compilation=not reuse,
        tools={str(p):c.sha(p) for p in (c.KERNEL,c.IMAGE,c.NODE,c.WABT,Path('/usr/local/opt/llvm/bin/clang'))},
        faults=len(fault_rows),controls=len(c.read(out/'controls.json')['rows']),
        requests=sum(r['requests'] for r in result['records']),collections=sum(r['collections'] for r in result['records']),
        workers=len(result['records']),times=times,compiler_changed=False,slot_credit=False,
        target_loaded_files=0,product_integrated=False))
    print(json.dumps({k:v for k,v in c.read(out/'summary.json').items() if k not in ('execution_inputs','tools')},sort_keys=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--reuse-compiled',action='store_true')
    a=p.parse_args()
    storage.gc()
    with storage.lease([a.output]):run(a.output.resolve(),a.reuse_compiled)
