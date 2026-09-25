"""Bind the integrated loader to the exact unit accepted after audit 179."""
from pathlib import Path
import hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
PACKET='2026-09-25-loader-design-r1'
PACKET_SHA='31ac1213773283983f2cadbb725040db698b0e90f6b39cef042024bd05f8aaeb'

def check():
    packet=c.STORE/PACKET
    assert c.sha(packet/'packet.json')==PACKET_SHA
    files=c.read(packet/'packet.json')['files']
    def bound(name):
        assert c.sha(packet/name)==files[name],name
        return c.read(packet/name)
    record=c.read(c.ROOT/'doc/WASM/stage1/integration-loader.json')
    assert record['status']=='ACCEPTED_AND_INTEGRATED' and record['packet']['sha256']==PACKET_SHA
    review=record['review'];blob=(c.ROOT/review['path']).read_bytes()[:review['bytes']]
    assert hashlib.sha256(blob).hexdigest()==review['sha256'],'review identity'
    native=bound('native/qualification.json');identity=native['source_identity']
    assert identity==record['qualification']['source_identity']
    c.verify_files(c.ROOT,identity)
    for name,digest in record['qualification']['records'].items():
        assert c.sha(packet/name)==digest==files[name],name
    expected=set(c.read(HERE.parent/'loader/provenance.json')['sources'])|{
        'runtime/wasm32/bundle.mjs','runtime/wasm32/cross-image.mjs','runtime/wasm32/heap-image.mjs'}
    assert {r['file'] for r in record['files']}==expected
    for row in record['files']:
        name=row['file'];assert c.sha(c.ROOT/name)==row['after']==row['reviewed']==files['proposal/'+name],name
        assert c.sha(packet/'proposal'/name)==row['reviewed'],name
    for row in record['generator']:
        assert c.sha(c.ROOT/row['file'])==row['after'],row['file']
        name='source/architecture/'+Path(row['file']).name
        assert c.sha(packet/name)==row['reviewed_sha256']==files[name]
        original=(packet/name).read_text()
        if name.endswith('generate.py'):original=original.replace('ROOT=HERE.parents[4]','ROOT=HERE.parents[3]')
        assert (c.ROOT/row['file']).read_text()==original
    path=HERE.parent/'architecture/generate.py'
    spec=importlib.util.spec_from_file_location('integrated_wasm_architecture',path)
    generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)
    source,_=generator.generate(c.read(generator.LAYOUT),c.read(generator.TCR))
    assert source==(c.ROOT/'compiler/WASM32/wasm32-arch.lisp').read_text()
    run=bound('native/results/run.json');readers=bound('readers/summary.json');corpus=bound('corpus/regression.json')
    assert run['status']==readers['status']==corpus['status']=='PASS'
    assert run['registered_tests']['passed']==21843 and corpus['fresh_comparisons']==26048
    assert readers['comparisons']==51 and readers['native_profiles_admitting_wasm_fasl']==0
    return dict(status='PASS',product_files=9,generator_files=3,source_identity=identity,
        runtime_identity={r['file']:r['after'] for r in record['files'] if r['file'].startswith('runtime/')},
        reviewed_packet=PACKET,reviewed_packet_sha256=PACKET_SHA,review_commit=review['commit'],
        native_tests_reused=21843,restored_fasls=164,reader_rows_reused=51,corpus_comparisons_reused=26048,
        mode='EXACT_REVIEWED_SOURCE_IDENTITY',new_execution=False,slot_credit=False,
        production_files=[0,0,0],accepted_originals=[575,535],ledger=[21,12])

if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
