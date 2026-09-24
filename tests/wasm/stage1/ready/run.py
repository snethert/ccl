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
    c.save(out/'macro-calls.json',local('macro_calls').census(out/'compiled',closure))
    c.save(out/'macro-controls.json',local('macro_calls').controls(out/'compiled',closure))
    expected={'GCD':'ccl:lib;numbers.lisp',
              'MAPCAR':'ccl:lib;lists.lisp','MAPLIST':'ccl:lib;lists.lisp',
              'MAPL':'ccl:lib;lists.lisp','MAPCAN':'ccl:lib;lists.lisp','MAPCON':'ccl:lib;lists.lisp',
              '%INTEGER-ABS':'ccl:level-0;l0-int.lisp',
              '%GET-HASHED-HTAB-SYMBOL':'ccl:level-0;nfasload.lisp',
              'CTYPE-P':'ccl:level-1;l1-typesys.lisp',
              '%INTEGER-TO-STRING':'ccl:level-0;l0-int.lisp',
              '%PR-INTEGER':'ccl:level-0;l0-int.lisp',
              'PRINT-BIGNUM-2':'ccl:level-0;l0-int.lisp',
              'LDIFF':'ccl:lib;lists.lisp','MAPC':'ccl:lib;lists.lisp',
              'MAP1':'ccl:lib;lists.lisp',
              'CSUBTYPEP':'ccl:level-1;l1-typesys.lisp','TYPE=':'ccl:level-1;l1-typesys.lisp'}
    selected={}
    for name,source in expected.items():
        rows=[row for row in closure['modules'] if row['name'] and row['name'].split('::')[-1]==name]
        assert len(rows)==1 and rows[0]['source']==source, ('whole-file support binding',name,rows)
        selected[name]=rows[0]
    assert not any(name in edge['callee'] for edge in closure['edges']
                   for name in ('WITH-ONE-NEGATED-BIGNUM-BUFFER','INVOKE-TYPE-METHOD'))
    assert 'READY-PRINT-INITIALIZER-SOURCE-EQUAL' in (out/'compiled/probe.log').read_text()
    assert 'READY-ISTRUCT-CLASSIFIER-SOURCE-EQUAL' in (out/'compiled/probe.log').read_text()
    assert 'READY-NATIVE-CLOSURE-REFUSED' in (out/'compiled/probe.log').read_text()
    c.save(out/'startup-support.json',dict(status='PASS',whole_file_bindings=selected,
        integer_radix_pairs_per_boot=55,mapc_callbacks_per_boot=3,
        mapping_functions=6,mapping_callbacks_per_boot=22,function_classes_per_boot=4,
        radix_initializer_source='level-0/l0-int.lisp',native_word_bits=61,target_word_bits=30,
        radix_globals_cleared_before_boot=True,initializer_omission_refused=True,
        return_it=True,stream_support_claim=False,
        unsupported_native_closure_refused=True,projected_generic_functions=50,
        integer_magnitudes_per_boot=13,symbol_lookups_per_boot=9,
        ctype_predicates_per_boot=7,type_method_results_per_boot=10,collecting_type_method_calls_per_boot=6,
        istruct_classifications_per_boot=3,
        classifier_source='level-1/l1-clos-boot.lisp',native_class_table_preserved=True))
    c.save(out/'callbacks.json',local('dispositions').dispositions(closure))
    c.save(out/'replacements.json',local('replacements').census(closure))
    c.save(out/'replacement-controls.json',local('replacements').controls(closure))
    # Import normally for mock-patching the read boundary in directed controls.
    import closure as closure_module
    c.save(out/'census-controls.json',closure_module.controls(out/'compiled'))
    local('measure').measure(out/'base',out/'compiled',out/'coverage.json')

def run(out):
    out.mkdir(exist_ok=True);times={}
    local('compiler').install()
    start=time.monotonic();build(out/'base',c.DEFAULT_CACHE);times['build']=time.monotonic()-start
    start=time.monotonic()
    probe(out/'base',HERE/'startup.lisp',HERE/'inputs.lisp',out/'compiled',c.DEFAULT_CACHE,'class',4)
    execution_prepare(out/'compiled');local('prepare').prepare(out/'compiled')
    times['compile']=time.monotonic()-start
    from execute import execute
    c.save(out/'closure.json',local('closure').census(out/'compiled'))
    times['heap_keys']=c.command([c.NODE,HERE/'heap-keys.mjs',out/'compiled/hash.wasm',out/'heap-keys.json'],
                                out/'heap-keys.log',timeout=60)
    times['admission_controls']=admission_controls(out)
    times['owner_controls']=c.command([c.NODE,HERE/'owner-controls.mjs',out/'compiled',out/'owner-controls.json'],out/'owner-controls.log',timeout=60)
    for mode,name in [('write','writer'),('read','reader')]:
        times[name]=c.command([c.NODE,HERE/'run.mjs',out/'compiled',mode,out/'images',out/(name+'.json')],
                             out/(name+'.log'),timeout=600)
        if mode=='write':
            # Reach the new image interface before the unchanged regression corpus.
            times['full_corpus']=execute(out/'base',4,'full')
    start=time.monotonic();local('guard_control').check(out,local('prepare').prepare)
    times['guard_control']=time.monotonic()-start
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
    assert (out/'compiled/probe.log').read_text().count('READY-NATIVE-STATE-RESTORED ')==16
    assert writer['comparisons']==1 and reader['comparisons']==4
    reference=writer['results'][0]['rows'][0]
    for result in reader['results']:
        assert result['processReady']==2 and result['classMode'] and not result['scheduler']
        row=result['rows'][0]
        assert {k:v for k,v in row.items() if k!='moved'}=={k:v for k,v in reference.items() if k!='moved'}
    assert [r['rejected'] for r in reader['refusals']]==['no-image','no-entry','early-ready','omit-radix-initializer','standalone-type-subtypep','standalone-type-equal','standalone-integer-abs','standalone-symbol-lookup','native-table-gethash','native-table-puthash','native-table-remhash','native-table-clrhash','image-class-shape','image-class-cpl','image-class-wrapper','image-wrapper-class','image-obsolete-wrapper','image-cpl-head','image-method-combination','image-method-function']
    assert all(r['state']==3 for r in reader['refusals'])
    assert all(r['directEntry'] and r['rootsPreserved']==7 for r in reader['refusals'] if r['rejected'].startswith('image-'))
    assert reference['values'][:4]==[612,50,43,41]
    for result in writer['results']+reader['results']:
        assert [row['name'] for row in result['supportChecks']]==['READY-INTEGER-STRINGS','READY-LIST-CALLEES','READY-TYPE-METHODS','READY-INTEGER-MAGNITUDE','READY-SYMBOL-LOOKUP','READY-CLASS-PROTOCOL','READY-SLOT-ERRORS']
        assert len(result['profileChecks'])==1
        check=result['profileChecks'][0]
        assert check['admitted'] and check['rootsPreserved']==7
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
    assert c.read(out/'owner-controls.json')['status']=='PASS'
    guard=c.read(out/'guard-control.json')
    assert guard['status']=='PASS' and guard['rejectedBy']=='startup root preservation'
    from execute import bound_report
    full,_=bound_report(out/'base/execution-report.json')
    assert full['tier']=='full' and full['inherited_comparisons']==0
    report=dict(status='PASS',generated_admission_omission_rejected=True,producer_comparisons=1,cold_boots=4,
        full_corpus_comparisons=full['fresh_comparisons'],
        heap_key_placements=2,heap_key_controls=2,
        classes=612,generic_functions=50,controls=len(reader['refusals']),
        image_admission_controls=31,support_comparisons=35,profile_refusals=8,public_table_bindings=4,native_state_restorations=16,
        collections=sum(w['collections']+w['internalCollections'] for w in reader['results']),
        original_definition_credit=0,slot_credit=False,
        scope='Process READY over the selected projected class/condition image. LL15 membership and replacement census remain incomplete.')
    c.save(out/'summary.json',report);return report

if __name__=='__main__':
    out=Path(sys.argv[1]);storage.gc(c.DEFAULT_CACHE)
    with storage.lease([out]):
        print(json.dumps(summarize(out) if '--summarize' in sys.argv else run(out)))
