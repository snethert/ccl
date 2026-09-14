"""Replay the retained build's IR and exact graph attachment; no native rebuild."""
import argparse
import gc
from pathlib import Path
from run import HERE, ROOT, INPUT, INPUT_SHA, BASE_SHA, CALLBACK_SHA, collect, project, read, save, digest
from flow import require
from controls import run as controls


def verify(packet, evidence, base_path, work):
    work.mkdir(parents=True,exist_ok=False)
    record=read(packet/'packet.json');rows=record['files']
    require(record['id']=='NATIVE-BUILD-FLOW-R1' and record['review_disposition']=='NOT_REVIEWED','PACKET_SCOPE')
    require(len({r['path'] for r in rows})==len(rows),'PACKET_DUPLICATE')
    require({p.name for p in packet.iterdir()if p.is_file()}=={'packet.json'}|{r['path'] for r in rows},'PACKET_MEMBERSHIP')
    for r in rows:
        p=packet/r['path']
        require(p.parent==packet and p.stat().st_size==r['bytes'] and digest(p)==r['sha256'],'ARTIFACT '+r['path'])
    for path,sha in read(packet/'sources.json').items():require(digest(ROOT/path)==sha,'SOURCE '+path)
    require(read(packet/'inputs.json')==read(HERE/'inputs.json'),'INPUT_MANIFEST')
    require(digest(evidence/INPUT)==INPUT_SHA and digest(base_path)==BASE_SHA,'INPUT_IDENTITY')
    require(digest(packet/'callback-capture.json.gz')==CALLBACK_SHA,'CALLBACK_IDENTITY')
    gc.disable()
    try:
        fs,calls,summary,samples=collect(evidence/INPUT)
        base=read(base_path);delta,integration=project(base,fs,calls)
        result=controls(samples,read(packet/'callback-capture.json.gz'),base,fs,calls,BASE_SHA)
        summary.update(integration=integration,controls_rejected=result['controls_rejected'],callback_probes=len(result['callback_probes']))
        outputs={'functions.json.gz':fs,'calls.json.gz':calls,'samples.json.gz':samples,
                 'delta.json.gz':delta,'summary.json':summary,'controls.json':result}
        for name,value in outputs.items():
            save(work/name,value)
            require((work/name).read_bytes()==(packet/name).read_bytes(),'REPRODUCTION '+name)
        save(work/'verification.json',dict(status='PASS',reproduced=list(outputs),controls=result['controls_rejected'],
             callbacks=len(result['callback_probes']),graph=integration,native_rerun=False,archive_scan=False))
        print('PASS: original build IR/code joins, six outputs byte-identical, callback and insertion/omission controls; closure remains BLOCKED.',flush=True)
    finally:gc.enable()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('packet','evidence','base','work'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();verify(a.packet.resolve(),a.evidence.resolve(),a.base.resolve(),a.work.resolve())
