#!/usr/bin/env python3
"""Reproduce the projected-image process READY join."""
from pathlib import Path
import importlib.util
import json
import sys
import time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage
from build import build
from probe import probe
from prepare import prepare as execution_prepare

def local(name):
    spec=importlib.util.spec_from_file_location('ready_'+name,HERE/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def admission_controls(out):
    compiled=out/'compiled'
    driver=HERE.parent/'class-image/controls.mjs'
    identities={name:c.sha(compiled/name) for name in
                ('runtime/heap-image.mjs','runtime/sha256.mjs')}
    seconds=c.command([c.NODE,driver,compiled,out/'admission-controls.json'],
                      out/'admission-controls.log',timeout=60)
    assert identities=={name:c.sha(compiled/name) for name in identities}
    record=c.read(out/'admission-controls.json')
    record.update(imported_modules=identities,driver_sha256=c.sha(driver),new_execution=True)
    c.save(out/'admission-controls.json',record)
    return seconds

def measurements(out):
    closure=local('closure').census(out/'compiled')
    c.save(out/'closure.json',closure)
    c.save(out/'callbacks.json',local('dispositions').dispositions(closure))
    c.save(out/'replacements.json',local('replacements').census(closure))
    # Import normally for mock-patching the read boundary in directed controls.
    import closure as closure_module
    c.save(out/'census-controls.json',closure_module.controls(out/'compiled'))
    local('measure').measure(out/'base',out/'compiled',out/'coverage.json')

def run(out):
    out.mkdir(exist_ok=True);times={}
    start=time.monotonic();build(out/'base',c.DEFAULT_CACHE);times['build']=time.monotonic()-start
    start=time.monotonic()
    probe(out/'base',HERE/'startup.lisp',HERE/'inputs.lisp',out/'compiled',c.DEFAULT_CACHE,'class',4)
    execution_prepare(out/'compiled');local('prepare').prepare(out/'compiled')
    times['compile']=time.monotonic()-start
    c.save(out/'closure.json',local('closure').census(out/'compiled'))
    times['heap_keys']=c.command([c.NODE,HERE/'heap-keys.mjs',out/'compiled/hash.wasm',out/'heap-keys.json'],
                                out/'heap-keys.log',timeout=60)
    times['admission_controls']=admission_controls(out)
    for mode,name in [('write','writer'),('read','reader')]:
        times[name]=c.command([c.NODE,HERE/'run.mjs',out/'compiled',mode,out/'images',out/(name+'.json')],
                             out/(name+'.log'),timeout=600)
    measurements(out)
    c.save(out/'times.json',times)
    return summarize(out)

def summarize(out):
    writer,reader=[c.read(out/(name+'.json')) for name in ('writer','reader')]
    assert writer['status']==reader['status']=='PASS'
    assert writer['codeDigest']==reader['codeDigest']==(out/'compiled/class-image-code.sha256').read_text().strip()
    admission=c.read(out/'admission-controls.json')
    assert admission['status']=='PASS' and len(admission['checks'])==31
    assert admission['imported_modules']=={name:c.sha(out/'compiled'/name) for name in admission['imported_modules']}
    assert (out/'compiled/probe.log').read_text().count('READY-NATIVE-STATE-RESTORED ')==6
    assert writer['comparisons']==1 and reader['comparisons']==4
    reference=writer['results'][0]['rows'][0]
    for result in reader['results']:
        assert result['processReady']==2 and result['classMode'] and not result['scheduler']
        row=result['rows'][0]
        assert {k:v for k,v in row.items() if k!='moved'}=={k:v for k,v in reference.items() if k!='moved'}
    assert [r['rejected'] for r in reader['refusals']]==['no-image','no-entry','early-ready','native-table-gethash','native-table-puthash','native-table-remhash','native-table-clrhash']
    assert all(r['state']==3 for r in reader['refusals'])
    assert reference['values'][:4]==[612,33,43,41]
    for result in writer['results']+reader['results']:
        assert len(result['profileChecks'])==1
        check=result['profileChecks'][0]
        assert check['admitted'] and check['rootsPreserved']==5
        values=check['refusals'][0]; count=0
        while values:
            value,values=values
            if count<8:assert isinstance(value,dict) and 'symbol' in value
            else:assert value is True
            count+=1
        assert count==9

    keys=c.read(out/'heap-keys.json')
    assert keys['status']=='PASS' and len(keys['records'])==2
    assert all(r['omitted_moved_lookup_misses']>0 for r in keys['records'])
    report=dict(status='PASS',producer_comparisons=1,cold_boots=4,
        heap_key_placements=2,heap_key_controls=2,
        classes=612,generic_functions=33,controls=len(reader['refusals']),
        image_admission_controls=31,profile_refusals=8,public_table_bindings=4,native_state_restorations=6,
        collections=sum(w['collections']+w['internalCollections'] for w in reader['results']),
        original_definition_credit=0,slot_credit=False,
        scope='Process READY over the selected projected class/condition image. LL15 membership and replacement census remain incomplete.')
    c.save(out/'summary.json',report);return report

if __name__=='__main__':
    out=Path(sys.argv[1]);storage.gc(c.DEFAULT_CACHE)
    with storage.lease([out]):
        print(json.dumps(summarize(out) if '--summarize' in sys.argv else run(out)))
