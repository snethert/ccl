"""Replay the original stream, histories, graph patch and controls."""
import argparse
import gc
from pathlib import Path
from common import HERE,ROOT,read,save,digest,require
from run import load_inputs,execute

OUTPUTS=('facts.json.gz','histories.json.gz','delta.json.gz','summary.json','controls.json')


def verify(packet,evidence,base,work):
    work.mkdir(parents=True,exist_ok=False)
    record=read(packet/'packet.json');rows=record['files']
    require(record['id']=='NATIVE-BINDING-VERSIONS-R1' and record['review_disposition']=='NOT_REVIEWED','PACKET_SCOPE')
    require(len({r['path'] for r in rows})==len(rows),'PACKET_DUPLICATE')
    require({p.name for p in packet.iterdir() if p.is_file()}=={'packet.json'}|{r['path'] for r in rows},'PACKET_MEMBERSHIP')
    for r in rows:
        p=packet/r['path']
        require(p.parent==packet and p.stat().st_size==r['bytes'] and digest(p)==r['sha256'],'ARTIFACT '+r['path'])
    for path,sha in read(packet/'sources.json').items():require(digest(ROOT/path)==sha,'SOURCE '+path)
    require(read(packet/'inputs.json')==read(HERE/'inputs.json'),'INPUT_MANIFEST')
    gc.disable()
    try:
        summary=execute(load_inputs(evidence,base),work)
        for name in OUTPUTS:require((packet/name).read_bytes()==(work/name).read_bytes(),'REPRODUCTION '+name)
        save(work/'verification.json',dict(status='PASS',reproduced=list(OUTPUTS),
            controls_rejected=summary['controls_rejected'],integration=summary['integration'],
            native_execution=False,archive_scan=False))
        print('PASS: five outputs reproduced byte-identically; binding and graph controls reject; census remains BLOCKED.',flush=True)
    finally:gc.enable()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('packet','evidence','base','work'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();verify(a.packet.resolve(),a.evidence.resolve(),a.base.resolve(),a.work.resolve())
