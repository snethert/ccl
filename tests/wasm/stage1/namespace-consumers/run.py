#!/usr/bin/env python3
"""Build and qualify the read-only namespace and its original CCL consumers."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse, hashlib, importlib.util, json, sys, time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage
import proposal

def local(name):
    spec=importlib.util.spec_from_file_location('namespace_'+name.replace('-','_'),HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def source_identity():
    return {name:hashlib.sha256(body.encode()).hexdigest() for name,body in proposal.sources().items()}

def matrix(out):
    target=out/'target'
    local('oracle').run(out)
    local('execute').prepare(target)
    def one(variant):
        base,move=variant
        args=[c.NODE,HERE/'check.mjs',target,'--namespace','--foreign']
        if base>8388608:args.append('--high')
        if move:args.append('--move')
        c.command(args,out/f'consumer-{base}-{str(move).lower()}.log',timeout=180)
        result=c.read(out/f'consumer-result-{base}-{str(move).lower()}.json')
        assert result['type']=='done' and result['nativeMatched'] and not result['openHandles']
        assert len(result['controls'])==47 and result['tableRefusalCount']==12
        assert len(result['packageState']['admissionControls'])==11
        return result
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(one,[(base,move) for base in (8388608,2146500608) for move in (False,True)]))

def summarize(out,consumers,regression,ready,native,readers):
    identity=source_identity()
    native_result=c.read(native/'qualification.json');assert native_result['status']=='PASS'
    assert all(native_result['source_identity'][name]==sha for name,sha in identity.items())
    reader_result=c.read(readers/'summary.json');assert reader_result['status']=='PASS'
    assert all(reader_result['full_sources'][name]['after']==sha for name,sha in identity.items() if '/WASM32/' not in name)
    cold=c.read(regression/'cold-compiler.json');assert cold['status']=='PASS' and not cold['cache_hit']
    assert all(cold['environment']['ready_compiler']['sources'][name]==sha for name,sha in identity.items())
    full=c.read(regression/'regression.json');assert full['status']=='PASS' and full['tier']=='full'
    ready_result=c.read(ready/'summary.json');assert ready_result['status']=='PASS'
    projection=c.read(consumers/'projection.json');assert projection['compiler_key']==cold['key']
    profiles=[]
    for base in (8388608,2146500608):
        for move in (False,True):
            result=c.read(consumers/f'consumer-result-{base}-{str(move).lower()}.json')
            assert result['type']=='done' and result['nativeMatched'] and not result['openHandles']
            profiles.append({key:result[key] for key in ('base','collectOnRequest','requests','collections','tableRefusalCount','substitutions')})
            assert len(result['controls'])==47 and len(result['packageState']['admissionControls'])==11
    record=dict(status='PASS',source_identity=identity,
        runtime_identity={name:hashlib.sha256(body.encode()).hexdigest() for name,body in proposal.runtime_sources().items()},
        compiler_key=cold['key'],cold_compiler=True,profiles=profiles,projection=projection,
        original_regression=full,ready_regression=ready_result,native_qualification=c.sha(native/'qualification.json'),
        reader_qualification=c.sha(readers/'summary.json'),
        implementation_inputs={str(p.relative_to(c.ROOT)):c.sha(p) for p in c.files(HERE) if '__pycache__' not in p.parts},
        accepted_originals=575,accepted_non_nil=535,slot_credit=False,
        files_cross_compiled=0,files_cross_loaded=0,files_target_loaded=0,
        profile='full mailbox; JSPI deferred by NSL-P2',
        scope='Read-only namespace consumers; source and bundle publication/loading belong to NSL-2/NSL-3.')
    c.save(out/'summary.json',record)
    return record

def run(out):
    started=time.monotonic();out.mkdir(parents=True,exist_ok=True)
    assert not (out/'summary.json').exists(),'completed packet'
    regression=local('regression');key=regression.run(out/'regression')
    local('ready-regression').run(out/'regression/base',out/'ready')
    local('develop').run(out/'consumers',key)
    matrix(out/'consumers')
    sys.setrecursionlimit(20000)
    local('native').run(out/'native')
    local('readers').run(out/'readers')
    result=summarize(out,*[out/name for name in ('consumers','regression','ready','native','readers')])
    print(json.dumps(dict(status=result['status'],seconds=time.monotonic()-started,workers=4)),flush=True)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    parser.add_argument('--matrix-only',action='store_true',help='Rerun observations against an already built consumer directory')
    args=parser.parse_args();storage.gc()
    with storage.lease([args.output]):
        if args.matrix_only:matrix(args.output.resolve())
        else:run(args.output.resolve())
