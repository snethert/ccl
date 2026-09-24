"""Bind integrated R10-R12 sources to audit 174; reuse target execution only."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess
ROOT=Path(__file__).resolve().parents[4]
PACKET='2026-09-24-stage1-ready-join-r12'
PACKET_SHA='e36a8d881fe2df73cc2ce34829165a7fa13654e3cc05157eda8c053506a21d9c'
BACKEND='compiler/WASM32/wasm32-backend.lisp'
RUNTIME={'runtime/wasm32/collector.c':'runtime-proposal/runtime/collector.c',
         'runtime/wasm32/heap-image.mjs':'runtime-proposal/runtime/heap-image.mjs'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())
def reviewed(store,revision=None):
    packet=store/PACKET
    assert sha(packet/'packet.json')==PACKET_SHA
    files=read(packet/'packet.json')['files']
    def bound(name):
        assert sha(packet/name)==files[name],name
        return read(packet/name)
    identity=bound('native-proposal-identity.json')
    assert identity==bound('native-reuse.json')['source_identity']
    def source(name):
        if revision:
            return subprocess.check_output(['git','show',revision+':'+name],cwd=ROOT)
        return (ROOT/name).read_bytes()
    for name,digest in identity.items():assert hashlib.sha256(source(name)).hexdigest()==digest,name
    for name,proposal in RUNTIME.items():
        assert sha(packet/proposal)==files[proposal]
        assert hashlib.sha256(source(name)).hexdigest()==files[proposal],name
    spec=importlib.util.spec_from_file_location('r9_check',ROOT/'tests/wasm/stage1/ready-acceptance/check.py')
    r9=importlib.util.module_from_spec(spec);spec.loader.exec_module(r9)
    r9.check_bit_layout((ROOT/'tests/wasm/stage1/ready/worker.mjs').read_text(),
                       (packet/'source/worker.mjs').read_text())
    return packet,identity,bound

def check(store):
    revision='4730cbae'
    packet,identity,bound=reviewed(store,revision)
    summary=bound('summary.json');assert summary['status']=='PASS'
    acceptance=read(ROOT/'doc/WASM/stage1/acceptance-ready-runtime.json')
    review=acceptance['review']
    blob=subprocess.check_output(['git','show',review['commit']+':'+review['path']],cwd=ROOT)
    assert hashlib.sha256(blob).hexdigest()==review['sha256']
    assert next(p for p in acceptance['packets'] if p['id']=='STAGE1-READY-JOIN-R12')['sha256']==PACKET_SHA
    return dict(status='PASS',mode='HISTORICAL_SOURCE_AND_CURRENT_RAW_LAYOUT',
        source_revision=revision,packet=PACKET,packet_sha256=PACKET_SHA,
        source_identity=identity,runtime_identity={p:sha(packet/s) for p,s in RUNTIME.items()},
        comparisons_reused=summary['full_corpus_comparisons'],cold_boots_reused=summary['cold_boots'],
        original_definitions=568,non_nil=531,raw_bit_layout_check_preserved=True,new_execution=False,slot_credit=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=check(args.evidence)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_identity','runtime_identity')}))
