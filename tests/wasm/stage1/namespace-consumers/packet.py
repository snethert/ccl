#!/usr/bin/env python3
"""Retain one namespace deliverable and replay its exact uninstrumented code."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, sys, tarfile
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage
import proposal

def local(name):
    spec=importlib.util.spec_from_file_location('namespace_packet_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def copy(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)

def retain(packet,consumers,regression,ready,native,readers,primitives):
    packet.mkdir(parents=True)
    result=local('run').summarize(packet,consumers,regression,ready,native,readers)
    for name,body in {**proposal.sources(),**proposal.runtime_sources()}.items():
        path=packet/'proposal'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
    for p in HERE.iterdir():
        if p.is_file():copy(p,packet/'source'/p.name)
    for p in consumers.iterdir():
        if p.is_file() and p.suffix in ('.json','.log'):copy(p,packet/'consumers'/p.name)
    if (consumers/'development').exists():shutil.copytree(consumers/'development',packet/'development/consumer-failures')
    for name in ('core-build.log','extension.log'):
        copy(consumers/name,packet/'compilation'/name)
    for name in ('records.sexp','modules.json','public-definitions.json','setf-bindings.json','load-bindings.json','methods.lisp','type-startup.lisp','foreign-startup.lisp','core-cache.json'):
        copy(consumers/'extension'/name,packet/'compilation'/name)
    for p in native.iterdir():
        if p.is_file() and p.suffix=='.json':copy(p,packet/'native'/p.name)
    for p in (native/'results').rglob('*'):
        if p.is_file() and p.suffix not in ('.image',) and 'proposal' not in p.relative_to(native/'results').parts:
            copy(p,packet/'native/results'/p.relative_to(native/'results'))
    shutil.copytree(readers,packet/'readers')
    for p in regression.iterdir():
        if p.is_file() and p.suffix=='.json':copy(p,packet/'regression'/p.name)
    for p in (regression/'base').iterdir():
        if p.is_file() and p.suffix in ('.json','.log'):copy(p,packet/'regression/base'/p.name)
    for p in ready.iterdir():
        if p.is_file() and p.suffix in ('.json','.log'):copy(p,packet/'ready'/p.name)
    for name in ('class-image-code.json','class-image-code.sha256','ready-worker.mjs','probe.log'):
        copy(ready/'compiled'/name,packet/'ready'/name)
    # Primitive R2 is a prerequisite section of this deliverable, not a second packet.
    for p in primitives.iterdir():
        if p.is_file() and p.suffix in ('.json','.log'):copy(p,packet/'primitive-r2'/p.name)
    shutil.copytree(primitives/'faults',packet/'primitive-r2/faults')
    copy(primitives/'compiled/compile.log',packet/'primitive-r2/compile.log')
    copy(primitives/'compiled/compile-completion.json',packet/'primitive-r2/compile-completion.json')
    primitive_inputs=c.read(primitives/'summary.json')['execution_inputs'];c.verify_files(c.ROOT,primitive_inputs)
    c.save(packet/'primitive-r2/pins.json',primitive_inputs)
    target=consumers/'target';modules=c.read(target/'compiled/modules.json')
    files=[p for p in target.iterdir() if p.is_file() and p.suffix in ('.mjs','.wasm','.json')]
    files += [p for p in c.files(target/'runtime') if p.suffix in ('.mjs','.json','.c','.h','.wat')]
    files += [p for p in (target/'compiled').iterdir() if p.suffix=='.json']
    files += [target/'compiled'/(m['name']+suffix) for m in modules for suffix in ('.wat','.wasm')]
    files += [target/'compiled/collector_probe_hook.wasm']
    files=sorted(set(files));manifest={str(p.relative_to(target)):c.sha(p) for p in files}
    # Every submitted code module must be the assembler output of the clean WAT.
    for m in modules:
        wat=target/'compiled'/(m['name']+'.wat');binary=wat.with_suffix('.wasm')
        entry=c.cache_read(c.DEFAULT_CACHE,'wabt',c.digest(c.assembly_key(wat)))
        assert entry and c.sha(binary)==c.sha(entry/'module.wasm'),('instrumented or mismatched module',m['name'])
    with tarfile.open(packet/'execution.tar.gz','w:gz') as archive:
        for p in files:archive.add(p,arcname='target/'+str(p.relative_to(target)),recursive=False)
        for name in ('consumer-native.json','consumer-native.json.foreign'):
            archive.add(consumers/name,arcname=name,recursive=False)
    c.save(packet/'execution-inputs.json',manifest)
    c.save(packet/'packet.json',dict(id='STAGE1-NAMESPACE-CONSUMERS-R1',status='PROPOSED',slot_credit=False,
        prerequisites={name:c.sha(c.STORE/name/'packet.json') for name in ('2026-09-24-namespace-provider-r1','2026-09-24-namespace-primitives-r1')},
        files=c.inventory(packet)))
    c.verify_files(packet,c.read(packet/'packet.json')['files'])
    return dict(status='PASS',workers=len(result['profiles']),archive=c.sha(packet/'execution.tar.gz'))

def verify(packet,out):
    c.verify_files(packet,c.read(packet/'packet.json')['files'])
    record=c.read(packet/'summary.json');c.verify_files(c.ROOT,record['implementation_inputs'])
    c.verify_files(c.ROOT,c.read(packet/'primitive-r2/pins.json'))
    out.mkdir(parents=True,exist_ok=True)
    with tarfile.open(packet/'execution.tar.gz') as archive:archive.extractall(out,filter='data')
    c.verify_files(out/'target',c.read(packet/'execution-inputs.json'))
    # Reuse the bound native observations; execute each target in a fresh Worker.
    for base in (8388608,2146500608):
        for move in (False,True):
            args=[c.NODE,HERE/'check.mjs',out/'target','--namespace','--foreign']
            if base>8388608:args.append('--high')
            if move:args.append('--move')
            suffix=f'{base}-{str(move).lower()}'
            c.command(args,out/('replay-'+suffix+'.log'),timeout=180)
            name='consumer-result-'+suffix+'.json'
            assert c.read(out/name)==c.read(packet/'consumers'/name),name
    result=dict(status='PASS',new_target_execution=True,native_observations='reused by exact hash',workers=4,
                execution_archive=c.sha(packet/'execution.tar.gz'))
    c.save(out/'verification.json',result);return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['retain','verify']);parser.add_argument('packet',type=Path);parser.add_argument('paths',nargs='+',type=Path)
    a=parser.parse_args()
    if a.command=='retain':
        assert len(a.paths)==6;result=retain(a.packet.resolve(),*[p.resolve() for p in a.paths])
    else:
        assert len(a.paths)==1
        with storage.lease(a.paths):result=verify(a.packet.resolve(),a.paths[0].resolve())
    print(json.dumps(result,sort_keys=True))
