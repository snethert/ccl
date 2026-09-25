#!/usr/bin/env python3
"""Compile two files, reconstruct their image from FASLs, and execute its
initializers and definitions with relocation/collection and a native oracle."""
from pathlib import Path
import importlib.util, json, subprocess, sys, time, platform
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage
import proposal
import shutil
CLANG='/usr/local/opt/llvm/bin/clang'
def local(name):
    spec=importlib.util.spec_from_file_location('cross_load_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def inputs():
    separate={'r6.py','qualify.py','readers.py','comparison.py','comparison-controls.py','corpus.py','extra.py','packet.py','replay.py'}
    paths=[p for p in c.files(HERE) if p.suffix in ('.py','.lisp','.mjs','.json','.patch') and p.name not in separate and 'results' not in p.relative_to(HERE).parts]
    paths+=[c.ROOT/n for n in local('build').SOURCES+local('build').integrated()]
    paths+=[p for p in c.files(c.ROOT/'runtime/wasm32') if p.suffix!='.md']
    paths+=[HERE.parent/'registration/load.lisp',HERE.parent/'bootstrap-validation/common.py',HERE.parent/'bootstrap-validation/storage.py']
    return {str(p.relative_to(c.ROOT)):c.sha(p) for p in sorted(set(paths))}
def runtime(out):
    out.mkdir(exist_ok=True)
    c.command([CLANG,'--target=wasm32','-O2','-nostdlib','-fno-builtin','-matomics','-mbulk-memory','-Wl,--no-entry','-Wl,--import-memory',
      '-Wl,--max-memory=2147549184','-Wl,--shared-memory','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer',
      c.ROOT/'runtime/wasm32/collector.c','-o',out/'collector.wasm'],out/'collector-build.log')
    c.command([CLANG,'--target=wasm32','-O2','-nostdlib','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184',
      '-Wl,--global-base=65536','-Wl,-z,stack-size=65536','-Wl,--export=integer_calculate','-Wl,--export=integer_workspace_bytes',
      c.ROOT/'runtime/wasm32/integer.c','-o',out/'integer.wasm'],out/'integer-build.log')
    c.command([sys.executable,c.ROOT/'runtime/wasm32/build-float.py','--output',out],out/'float-build.log')
    c.command([c.WABT,*c.FLAGS,c.ROOT/'runtime/wasm32/float-detector.wat','-o',out/'detector.wasm'],out/'detector.log')
def node(args,log):
    with open(log,'w') as stream:
        result=subprocess.run([c.NODE,*[str(a) for a in args]],stdout=stream,stderr=subprocess.STDOUT,timeout=300)
    text=Path(log).read_text()
    assert result.returncode==0,text[-3000:]
    return json.loads(text.strip().splitlines()[-1])
def run(out,stops=True):
    started=time.monotonic();out.mkdir(parents=True,exist_ok=True)
    assert not (out/'summary.json').exists(),'completed run'
    pins=inputs();times={}
    toolchain={str(p):dict(sha256=c.sha(p),version=subprocess.check_output([str(p),'--version'],text=True).splitlines()[0]) for p in [c.NODE,c.WABT,Path('/usr/local/bin/wasm-objdump'),Path(CLANG)]}
    environment=dict(platform=platform.platform(),machine=platform.machine(),python=sys.version,
        kernel=c.sha(c.KERNEL),image=c.sha(c.IMAGE),upstream_pins=c.read(c.STORE/'macos-u1-inputs/pins.json'),tools=toolchain)

    proposal.prepare_runtime(out/'runtime')
    for name in ('write.mjs','boot.mjs','controls.mjs','d2.mjs'):shutil.copyfile(HERE/name,out/name)
    policy=c.read(c.STORE/'2026-09-20-stage1-materialization-r1/execution/policy.json')
    assert policy['materializer']['sha256']==c.sha(out/'runtime/materializer.mjs')
    c.save(out/'policy.json',policy)
    c.save(out/'versions.json',dict(abi=dict(name='B',version=1),layout=dict(version=1,sha256=c.sha(c.ROOT/'doc/WASM/contracts/wasm32-layout.v1.json'))))
    t=time.monotonic();local('build').run(out/'p2-0',stops);times['build']=time.monotonic()-t
    t=time.monotonic();written=node([out/'write.mjs',out/'p2-0',out/'p2-0/artifacts',out/'policy.json',out/'versions.json'],out/'write.log');times['write']=time.monotonic()-t
    t=time.monotonic();runtime(out/'runtime');times['runtime']=time.monotonic()-t
    artifacts=out/'p2-0/artifacts'
    t=time.monotonic()
    boots={mode:node([out/'boot.mjs',artifacts,out/'runtime',HERE/'cases.json',*(['--collect'] if 'collect' in mode else []),*(['--relocate'] if 'relocate' in mode else [])],out/f'boot-{mode}.log') for mode in ('plain','collect','relocate','relocate-collect')}
    times['boot']=time.monotonic()-t
    t=time.monotonic();native=local('native').run(out/'native');times['native']=time.monotonic()-t
    for mode,boot in boots.items():
        assert boot['status']=='PASS' and boot['observations']==native['observations'],mode
    assert boots['collect']['collections']>=len(json.loads((HERE/'cases.json').read_text()))
    controls=node([out/'controls.mjs',artifacts],out/'controls.log')
    stops_rows=c.read(out/'p2-0/stops.json') if stops else None
    record=dict(status='PASS',
        artifacts=dict(heap_digest=written['digest'],code_digest=written['codeDigest'],heap_bytes=written['heapBytes'],objects=written['objects'],relocations=written['relocations'],modules=written['modules']),
        target=dict(cold_load_functions=boots['plain']['coldLoad'],observations=boots['plain']['observations'],collections=boots['collect']['collections']),
        native=native,native_matched=True,controls=controls['rows'],
        level0=dict(files=len(stops_rows),compiled=sum(1 for r in stops_rows if r['status']=='COMPILED'),modules=sum(r['modules'] for r in stops_rows),
                    rows=[{k:r[k] for k in ('file','status','modules','condition')}|{'message':(r['message'] or '')[:200]} for r in stops_rows]) if stops else None,
        files_cross_compiled=0,files_cross_loaded=0,files_target_loaded=0,accepted_originals=575,accepted_non_nil=535,slot_credit=False,
        execution_inputs=pins,environment=environment,boots=boots,times=times,seconds=time.monotonic()-started)
    assert pins==inputs(),'sources changed during execution'
    c.save(out/'summary.json',record)
    print(json.dumps({k:record[k] for k in ('status','artifacts','seconds')}))
    return record
if __name__=='__main__':
    with storage.lease([Path(sys.argv[1])]):run(Path(sys.argv[1]).resolve(),'--no-stops' not in sys.argv)
