#!/usr/bin/env python3
"""Build the integrated development census. Exit 2 means a valid but blocked closure."""
import argparse
from datetime import datetime,timezone
import gc
import json
from pathlib import Path
import shutil
import sys
import traceback
from support import HERE,ROOT,read,save,digest,require,legacy_tools,source_files,load_inputs
from compose import materialize
import seeds
from assess import analyze

OUTPUTS=('report.json','blockers.json.gz','worklists.json.gz','seed-integration.json.gz','composition.json')


def execute(args):
    out=args.output.resolve();store=args.evidence.resolve()
    require(out!=store and out not in store.parents and store not in out.parents and ROOT not in out.parents,'OUTPUT_PATH')
    out.mkdir(parents=True,exist_ok=False)
    pins=read(HERE/'inputs.json')
    record=dict(version=1,status='ERROR',exit_code=1,command=sys.argv,timestamp=datetime.now(timezone.utc).isoformat(),
                native_execution=False,source_sha256={str(p.relative_to(ROOT)):digest(p) for p in source_files()},
                inputs=pins,scope='Integrated development closure; no LL15 result envelope, project acceptance or native rebuild.')
    for p in source_files():
        dest=out/'sources'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    save(out/'run.json',record)
    try:
        gc.disable();tools=legacy_tools();v=load_inputs(store,pins)
        print('Reconstructing reviewed graph fragments.',flush=True)
        base,stages=materialize(v,pins,tools)
        delta=seeds.make(v,pins,tools);graph=seeds.apply(base,delta)
        seeds.check(base,graph,delta,seeds.make(v,pins,tools))
        print('Reviewed graph reconstructed; checking revision-2 seeds and closure obligations.',flush=True)
        report,blockers,work=analyze(base,graph,v,delta,tools)
        for name,value in zip(OUTPUTS,(report,blockers,work,delta,dict(version=1,stages=stages))):save(out/name,value)
        if args.graph:
            save(out/'census.json.gz',graph)
            record['working_graph']=dict(path='census.json.gz',sha256=digest(out/'census.json.gz'),bytes=(out/'census.json.gz').stat().st_size)
        if args.controls:
            from integration_controls import run
            checks=run(base,graph,delta,v,pins,tools,report)
            save(out/'controls.json',checks);record['integration_controls_rejected']=checks['controls_rejected']
        if args.packet:
            packet=args.packet.resolve();manifest=read(packet/'packet.json')
            require(manifest['id']=='CENSUS-DEVELOPMENT-CLOSURE-R1','PACKET_ID')
            rows=manifest['files'];require(len({r['path'] for r in rows})==len(rows),'PACKET_MEMBERSHIP')
            for r in rows:
                p=packet/r['path'];require(p.parent==packet and digest(p)==r['sha256'] and p.stat().st_size==r['bytes'],'PACKET_BYTES '+r['path'])
            require(record['source_sha256']==read(packet/'sources.json'),'PACKET_SOURCES')
            for name in OUTPUTS+('controls.json',):
                require((out/name).read_bytes()==(packet/name).read_bytes(),'REPRODUCTION '+name)
            record['reproduced_outputs']=len(OUTPUTS)+1
        record.update(status='BLOCKED',exit_code=2,analysis_completed=True)
        print(json.dumps(dict(status='BLOCKED',counts=report['counts'],controls=record.get('integration_controls_rejected'),
                              next_work=report['next_work']),sort_keys=True),flush=True)
        return 2
    except BaseException:
        (out/'failure.txt').write_text(traceback.format_exc());raise
    finally:
        gc.enable();save(out/'run.json',record)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--graph',action='store_true',help='Also write the reproducible working census.json.gz; do not duplicate it in the evidence packet.')
    p.add_argument('--controls',action='store_true',help='Run integration regressions, not LL15-c qualification.')
    p.add_argument('--packet',type=Path,help='Reproduce retained outputs, including controls.')
    args=p.parse_args()
    if args.packet:args.controls=True
    sys.exit(execute(args))
