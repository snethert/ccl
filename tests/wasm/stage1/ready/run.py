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

def run(out):
    out.mkdir(exist_ok=True);times={}
    start=time.monotonic();build(out/'base',c.DEFAULT_CACHE);times['build']=time.monotonic()-start
    start=time.monotonic()
    probe(out/'base',HERE/'startup.lisp',HERE/'inputs.lisp',out/'compiled',c.DEFAULT_CACHE,'class',4)
    execution_prepare(out/'compiled');local('prepare').prepare(out/'compiled')
    times['compile']=time.monotonic()-start
    for mode,name in [('write','writer'),('read','reader')]:
        times[name]=c.command([c.NODE,HERE/'run.mjs',out/'compiled',mode,out/'images',out/(name+'.json')],
                             out/(name+'.log'),timeout=600)
    local('measure').measure(out/'base',out/'compiled',out/'coverage.json')
    c.save(out/'times.json',times)
    return summarize(out)

def summarize(out):
    writer,reader=[c.read(out/(name+'.json')) for name in ('writer','reader')]
    assert writer['status']==reader['status']=='PASS'
    assert writer['comparisons']==1 and reader['comparisons']==4
    reference=writer['results'][0]['rows'][0]
    for result in reader['results']:
        assert result['processReady']==2 and result['classMode'] and not result['scheduler']
        row=result['rows'][0]
        assert {k:v for k,v in row.items() if k!='moved'}=={k:v for k,v in reference.items() if k!='moved'}
    assert [r['rejected'] for r in reader['refusals']]==['no-image','no-entry','early-ready']
    assert all(r['state']==3 for r in reader['refusals'])
    assert reference['values'][:4]==[612,33,43,41]
    report=dict(status='PASS',producer_comparisons=1,cold_boots=4,
        classes=612,generic_functions=33,controls=len(reader['refusals']),
        collections=sum(w['collections']+w['internalCollections'] for w in reader['results']),
        original_definition_credit=0,slot_credit=False,
        scope='Process READY over the selected projected class/condition image. LL15 membership and replacement census remain incomplete.')
    c.save(out/'summary.json',report);return report

if __name__=='__main__':
    out=Path(sys.argv[1]);storage.gc(c.DEFAULT_CACHE)
    with storage.lease([out]):
        print(json.dumps(summarize(out) if '--summarize' in sys.argv else run(out)))
