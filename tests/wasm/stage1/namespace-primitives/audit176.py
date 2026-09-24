"""Replay the two standing-tool fixes alongside the primitive boundary cases."""
import importlib.util
import sys
from pathlib import Path
import common as c
HERE=Path(__file__).resolve().parent

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result

def run(out):
    runtime=module('runtime_identity',HERE.parent/'ready-runtime-acceptance/check.py')
    identity=runtime.check(c.STORE)
    # Historical source pinning must not silently become current-source reuse.
    try:runtime.reviewed(c.STORE,'b2f0ad8f')
    except AssertionError as error:
        assert str(error)=='compiler/WASM32/wasm32-backend.lisp'
    else:raise AssertionError('R13 must differ from the R12 source identity')
    provider=module('provider_run',HERE.parent/'namespace/run.py')
    nested=out/'provider/nested/run'
    paths=list(sys.path)
    try:
        sys.path.insert(0,str(provider.HERE))
        summary=provider.run(nested)
    finally:
        sys.path[:]=paths
    packet=c.STORE/'2026-09-24-namespace-provider-r1'
    assert c.sha(packet/'packet.json')=='75ffac356644cb4ad18a22f6310204e739940c55d170f05fa55d51b54cfa3416'
    files=c.read(packet/'packet.json')['files']
    records={}
    for name in ('native.json','namespace.json','mailbox.json','foreign-types.json','controls.json'):
        assert c.sha(packet/name)==files[name]
        assert c.read(nested/name)==c.read(packet/name),name
        records[name]=c.sha(nested/name)
    result=dict(status='PASS',historical_identity=identity,R13_rejected_as_R12=True,
        nested_output_created=True,provider_records=records,
        provider_execution_inputs=summary['execution_inputs'],provider_native_comparisons=summary['native_comparisons'],
        provider_controls=summary['controls'],provider_faults=summary['faults'])
    c.save(out/'audit176.json',result)
    return result
