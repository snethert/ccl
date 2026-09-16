#!/usr/bin/env python3
"""Re-execute the lazy corpus and controls; do not rebuild unchanged compilers."""
import argparse,tempfile,json,shutil
from pathlib import Path
from run import HERE,ROOT,BASE,sha,read,run

def safe(root,name):
    p=(root/name).resolve();assert p.is_relative_to(root.resolve()),'CONTAINED_PATH';return p

def verify(evidence,packet):
    for name,h in read(packet/'source-pins.json').items():
        assert sha(safe(ROOT,name))==h and sha(safe(packet/'source',name))==h,'SOURCE '+name
    for row in read(packet/'packet.json')['files']:assert sha(safe(packet,row['path']))==row['sha256'],'PAYLOAD '+row['path']
    assert sha(evidence/BASE/'packet.json')==read(packet/'run.json')['base_manifest_sha256'],'BASE_MANIFEST'
    for row in read(packet/'dependencies.json'):assert sha(safe(evidence,row['path']))==row['sha256'],'INPUT '+row['path']
    for name,row in read(packet/'toolchain.json').items():assert sha(Path(row['path']))==row['sha256'],'TOOL '+name
    tmp=Path(tempfile.mkdtemp(prefix='ccl-lazy-replay-')).resolve()
    try:
        fresh=tmp/'run';run(evidence,fresh)
        for name in ['harness.mjs','catalog.json','alias-catalog.json','lazy-stub.wasm','malformed.json','execution.json','controls.json','mutants.json','summary.json']:
            assert (fresh/name).read_bytes()==(packet/name).read_bytes(),'REPLAY '+name
        for p in (packet/'malformed').iterdir():assert p.read_bytes()==(fresh/'malformed'/p.name).read_bytes(),'MALFORMED_BINARY '+p.name
    except BaseException:
        print('Replay failure retained at',tmp,flush=True)
        raise
    else:shutil.rmtree(tmp)
    print('S1-B-LAZY-CALLS-VERIFIED: pinned generated modules; identical corpus, cold installation, controls and mutants')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packet',required=True,type=Path);p.add_argument('--evidence',required=True,type=Path);a=p.parse_args();verify(a.evidence.resolve(),a.packet.resolve())
