"""Replay the accepted READY consumers under the namespace compiler proposal."""
from pathlib import Path
import importlib.util, sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage
import regression
import proposal

def run(base,out,resume=False):
    out.mkdir(parents=True,exist_ok=True)
    compiler=regression.compiler_setup()
    from probe import probe
    ready=HERE.parent/'ready'
    compiled=out/'compiled'
    if not resume:probe(base,ready/'startup.lisp',ready/'inputs.lisp',compiled,c.DEFAULT_CACHE,'class',4)
    sys.path.insert(0,str(ready))
    import pool_runtime
    pool_runtime.reset_parent(compiled)
    compiler.execution_prepare(compiled)
    spec=importlib.util.spec_from_file_location('namespace_ready_prepare',ready/'prepare.py')
    prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)
    prepare.prepare(compiled)
    worker=compiled/'ready-worker.mjs';original=c.sha(worker);text=worker.read_text()
    old='encode({octets:[1,2,3]})'
    assert text.count(old)==2
    worker.write_text(text.replace(old,'encode({vector:[1,2,3]})'))
    c.save(out/'admission-update.json',dict(before=original,after=c.sha(worker),cases=2,
        reason='UB8 is now an admitted byte-copy layout; use a node vector for the two wrong-kind refusals. All twelve refusals remain.'))
    (compiled/'runtime/collector.c').write_text(proposal.collector())
    c.command(['/usr/local/opt/llvm/bin/clang','--target=wasm32','-O2','-nostdlib','-fno-builtin','-matomics','-mbulk-memory',
      '-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,--shared-memory',
      '-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer',
      compiled/'runtime/collector.c','-o',compiled/'collector.wasm'],out/'collector.log')
    code=c.read(compiled/'class-image-code.json')
    for name in ('ready-worker.mjs','collector.wasm'):code[name]=c.sha(compiled/name)
    (compiled/'class-image-code.json').write_bytes(c.canonical(code))
    (compiled/'class-image-code.sha256').write_text(c.sha(compiled/'class-image-code.json')+'\n')
    for mode,name in [('write','writer'),('read','reader')]:
        c.command([c.NODE,ready/'run.mjs',compiled,mode,out/'images',out/(name+'.json')],out/(name+'.log'),timeout=600)
    writer,reader=[c.read(out/(name+'.json')) for name in ('writer','reader')]
    assert writer['status']==reader['status']=='PASS'
    assert writer['codeDigest']==reader['codeDigest']
    result=dict(status='PASS',codeDigest=writer['codeDigest'],boots=len(writer['results'])+len(reader['results']),
        refusals=len(reader['refusals']),comparisons=writer['comparisons']+reader['comparisons'])
    c.save(out/'summary.json',result);print(result,flush=True)
    return result

if __name__=='__main__':
    with storage.lease([Path(sys.argv[2])]):run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve(),'--resume' in sys.argv)
