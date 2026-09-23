#!/usr/bin/env python3
"""Build and execute the coordinated class image, using the accepted P4 cache."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage
from build import build
from execute import execute


def module(path):
    spec=importlib.util.spec_from_file_location('class_image_prepare',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def summary(out):
    full=c.read(out/'base/execution-report.json')
    writer,reader,boot=[c.read(out/(name+'.json')) for name in ('writer','reader','boot')]
    assert full['status']==writer['status']==reader['status']==boot['status']=='PASS'
    assert full['fresh_comparisons']==26048
    reference={r['caseId']+str(r['moved']):r for r in writer['results'][0]['rows']}
    for worker in reader['results']:
        assert len(worker['rows'])==len(reference)
        for row in worker['rows']:assert row==reference[row['caseId']+str(row['moved'])]
    assert writer['comparisons']==90 and reader['comparisons']==180 and boot['comparisons']==4
    assert all(row['ready']=='READY' and row['values']==[True,612,43,41]
               for worker in boot['results'] for row in worker['rows'])
    images=[c.read(p) for p in sorted((out/'images').glob('*.json'))]
    assert len(images)==46
    ready=c.read(out/'images/class-ready.json')
    result=dict(status='PASS',original_definitions=550,non_nil_witnesses=515,
        new_original_credit=0,baseline_comparisons=26048,producer_comparisons=90,
        cold_comparisons=180,persistent_root_comparisons=4,class_cells=612,
        controls=len(c.read(out/'controls.json')['checks']),images=len(images),
        ready_image_bytes=ready['record']['bytes'],ready_image_objects=ready['objects'],
        bytes=sum(r['record']['bytes'] for r in images),
        relocations=sum(len(r['record']['relocations']) for r in images),
        collections=sum(w['collections']+w['internalCollections'] for r in (reader,boot) for w in r['results']),
        placements=[8388608,2146500608],code_digest=reader['codeDigest'],
        limitation='Class-image readiness only. Projected class metadata, not a whole CCL cold build or LL15 READY.')
    c.save(out/'summary.json',result);return result


def run(out):
    out.mkdir(exist_ok=True)
    start=time.monotonic();phases={}
    build(out/'base',c.DEFAULT_CACHE)
    phases['full']=execute(out/'base',workers=4)
    module(HERE/'prepare.py').prepare(out/'base')
    for mode,name in [('write','writer'),('read','reader'),('boot','boot')]:
        phases[name]=c.command([c.NODE,HERE/'run.mjs',out/'base',mode,out/'images',out/(name+'.json')],
                              out/(name+'.log'),timeout=900)
    phases['controls']=c.command([c.NODE,HERE/'controls.mjs',out/'base',out/'controls.json'],out/'controls.log')
    result=summary(out);c.save(out/'times.json',dict(total=time.monotonic()-start,phases=phases))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--summarize',action='store_true');a=p.parse_args()
    storage.gc(c.DEFAULT_CACHE)
    with storage.lease([a.output]):
        print(json.dumps(summary(a.output) if a.summarize else run(a.output),sort_keys=True))
