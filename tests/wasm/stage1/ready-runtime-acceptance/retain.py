"""Retain this integration once, then delete its managed workspaces."""
from pathlib import Path
import argparse
import json
import shutil
import sys
import tarfile
from check import ROOT,check,sha
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage

def retain(work,native,readers,packet):
    identity=check(c.STORE)
    qualification=c.read(native/'qualification.json')
    assert qualification['source_identity']==identity['source_identity']
    assert qualification['native_run_sha256']==sha(native/'results/run.json')
    run=c.read(native/'results/run.json')
    assert run['status']=='PASS' and run['registered_tests']['passed']==21843 and run['restored_fasls']==164
    for name in ('summary.json','integrated-preparation.json'):
        assert c.read(work/'focused'/name)['status']=='PASS'
    assert c.read(readers/'summary.json')['status']=='PASS'
    assert c.read(work/'runtime-build.json')['status']=='PASS'
    packet.mkdir()
    for name in ('identity.json','r9-standing.json','r9-identity-before.json','r9-controls.json','runtime-build.json','integration-files.json'):
        shutil.copyfile(work/name,packet/name)
    for name in ('qualification.json','proposal-identity.json'):
        shutil.copyfile(native/name,packet/name)
    shutil.copyfile(native/'results/run.json',packet/'native-run.json')
    with tarfile.open(packet/'native-results.tar.gz','w:gz') as archive:
        for path in c.files(native/'results'):archive.add(path,arcname=str(path.relative_to(native/'results')),recursive=False)
    shutil.copytree(readers,packet/'readers')
    shutil.copytree(work/'focused',packet/'focused',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(HERE,packet/'source',ignore=shutil.ignore_patterns('__pycache__'))
    old=HERE.parent/'ready-acceptance'
    for name in ('check.py','README.md'):shutil.copyfile(old/name,packet/('r9-'+name))
    for name in ('acceptance-ready-runtime.json','integration-ready-runtime.json'):
        shutil.copyfile(ROOT/'doc/WASM/stage1'/name,packet/name)
    c.save(packet/'pins.json',{str(p.relative_to(ROOT)):sha(p) for p in c.files(HERE)} |
        {str(p.relative_to(ROOT)):sha(p) for p in (old/'check.py',old/'README.md')})
    c.save(packet/'verification.json',dict(status='PASS',source_identity=identity['source_identity'],
        runtime_identity=identity['runtime_identity'],native_rebuilt=True,native_tests=21843,
        restored_fasls=164,reader_comparisons=68,target_full_corpus_rebuilt=False,
        target_full_comparisons_reused=26048,focused_cold_boots=4,original_definitions=568,
        non_nil=531,new_original_credit=0,slot_credit=False,execution_during_retention=False))
    c.save(packet/'packet.json',dict(id='STAGE1-READY-RUNTIME-ACCEPTANCE',files=c.inventory(packet),slot_credit=False))
    c.verify_files(packet,c.read(packet/'packet.json')['files'])
    for path in (work,native,readers):shutil.rmtree(storage.workspace(path))
    return dict(status='PASS',retained=str(packet),workspaces_deleted=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('work','native','readers','packet'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    with storage.lease([args.work,args.native,args.readers]):print(json.dumps(retain(args.work,args.native,args.readers,args.packet)))
