#!/usr/bin/env python3
"""Run finite-callee analysis and native probes, then apply the bounds to a graph.

Development output only. This command writes no evidence catalog, acceptance
record, documentation or commit. Success of this pass does not close LL15.
"""
import argparse
from collections import Counter
import gc
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import traceback

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'build-flow'))
from flow import convert
from finite import Resolver,require
from test_finite import native_checks
import integrate
sys.path.insert(0,str(HERE.parent/'closure'))
from support import read,save,digest,load_module

HEADER=re.compile(rb'^\{"version":2,"sequence":([0-9]+),"kind":"([a-z0-9-]+)"')
STREAM_SHA='23b63396031cca638f845822d15d2b7af927aa8d0c5d193ae4c03df70b120a7b'


def probes(out,store):
    work=out/'native';work.mkdir()
    pins=read(HERE.parent/'source-traversal/inputs.json')['inputs']
    with tarfile.open(store/pins['source']['path']) as archive:archive.extractall(work,filter='data')
    binary=work/'dx86cl64';shutil.copyfile(store/pins['kernel']['path'],binary);binary.chmod(0o755)
    env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(work),FINITE_OUTPUT=str(out/'native-probes.json'))
    argv=[str(binary),'--image-name',str(store/pins['image']['path']),'--no-init','--batch']
    for name in ('observer.lisp','dependencies.lisp','rich-observation/observer.lisp','finite-callees/probes.lisp'):
        argv+=['--load',str(HERE.parent/name)]
    argv+=['--eval','(progn (census-finite-probes::run) (ccl:quit))']
    with (out/'native.log').open('w') as log:
        result=subprocess.run(argv,cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60)
    require(result.returncode==0,'NATIVE_PROBE_EXIT')
    return native_checks(read(out/'native-probes.json'),convert)


def collect(stream,calls,operators,out):
    wanted={(c['function_id'],c['site_id']):c for c in calls
            if c['dependency']['category'] in ('function-variable','computed-callee')
            and not c.get('lexical_bound',{}).get('targets')}
    events={c['event'] for c in wanted.values()};found={};counts=Counter();last=0;done=False;captures=0
    with gzip.open(stream,'rb') as src,gzip.open(out/'selected-ir.jsonl.gz','wb',compresslevel=1) as selected:
        for line in src:
            match=HEADER.match(line);require(match is not None,'EVENT_HEADER')
            seq=int(match[1]);kind=match[2].decode();require(seq==last+1 and not done,'EVENT_SEQUENCE')
            last=seq;counts[kind]+=1
            if seq in events:
                require(kind in ('before-pass2','frontend'),'SELECTED_EVENT_KIND')
                row=json.loads(line);capture=convert(row['payload'],operators);resolver=Resolver(capture)
                expected_calls={(f['function_id'],c['site_id']):c for f in resolver.family.values() for c in f['calls']}
                symbols={n['id']:n for n in row['payload']['ir']['objects'] if n['kind']=='symbol'}
                for r in resolver.calls():
                    key=(r['function_id'],r['site_id'])
                    if key not in wanted:continue
                    old=wanted[key]
                    require(key not in found and old['event']==seq and old['dependency']==expected_calls[key]['dependency'],
                            'ORIGINAL_CALL_JOIN')
                    for target in r['targets']:
                        if target['kind']=='symbol':target['descriptor']=symbols[target['id']]
                    r.update(event=seq,source=row['source'],source_position=row['source_position'],old_reason=old.get('lexical_bound'))
                    found[key]=r
                selected.write(line);captures+=1
                if captures%100==0:print(f'Analyzed {captures} original compiler families.',flush=True)
            if kind=='complete':
                row=json.loads(line);actual=dict(counts);del actual['complete']
                require(actual=={r['kind']:r['count'] for r in row['payload']['counts']} and
                        row['payload']['events_before_complete']==seq-1,'COMPLETION_COUNTS');done=True
    require(done and set(found)==set(wanted) and captures==len(events),'COMPUTED_POPULATION_COVERAGE')
    return [found[k] for k in sorted(found)],captures


def replay(selected,proofs,calls,operators):
    expected={(r['function_id'],r['site_id']):r for r in proofs};actual={}
    with gzip.open(selected,'rt') as src:
        for line in src:
            row=json.loads(line);symbols={n['id']:n for n in row['payload']['ir']['objects'] if n['kind']=='symbol'}
            for r in Resolver(convert(row['payload'],operators)).calls():
                key=(r['function_id'],r['site_id'])
                if key not in expected:continue
                for t in r['targets']:
                    if t['kind']=='symbol':t['descriptor']=symbols[t['id']]
                r.update(event=row['sequence'],source=row['source'],source_position=row['source_position'],old_reason=calls[key].get('lexical_bound'))
                require(key not in actual,'REPLAY_DUPLICATE');actual[key]=r
    require(actual==expected,'REPLAY_PROOFS')


def execute(a):
    out=a.output.resolve();store=a.evidence.resolve();require(ROOT not in out.parents and store not in out.parents,'OUTPUT_PATH')
    out.mkdir(parents=True,exist_ok=False)
    # Keep original failures locally; publication is deliberately not part of
    # this runner. No shared source is patched, compiled into the baseline or saved.
    shutil.copytree(HERE,out/'executed-sources',ignore=shutil.ignore_patterns('__pycache__'))
    try:
        p=read(HERE.parent/'builtin-slots/inputs.json')['inputs'];values={}
        for key in ('calls','functions','samples'):
            path=store/p[key]['path'];require(digest(path)==p[key]['sha256'],'INPUT_IDENTITY '+key);values[key]=read(path)
        stream=store/'2026-09-12-rich-census-r1/observed-r4.jsonl.gz';require(digest(stream)==STREAM_SHA,'STREAM_IDENTITY')
        sample=next(iter(values['samples'].values()));operators={int(k):v for k,v in sample['operators'].items()}
        print('Running native compiler probes and mutation checks.',flush=True);checks=probes(out,store)
        print('Bounding the original computed calls from complete retained IR.',flush=True)
        proofs,captures=collect(stream,values['calls'],operators,out)
        save(out/'proofs.json.gz',proofs)
        hs_path=store/'2026-09-14-binding-versions-r1/histories.json.gz'
        require(digest(hs_path)=='4054a5980aa83a5d22b2749f90683acab663ed3a405d9276cabd4053c544bd69','HISTORIES_IDENTITY')
        histories=read(hs_path)
        base=read(a.base);base_sha=digest(a.base)
        if a.base_sha:require(base_sha==a.base_sha,'BASE_IDENTITY')
        delta=integrate.patch(base,proofs,histories);graph=integrate.apply(base,delta)
        integrate.check(base,graph,delta,proofs,histories)
        checks['integration']=integrate.controls(base,graph,delta,proofs,histories)
        print('Applying finite expression bounds and checking the resulting census.',flush=True)
        contract=load_module('finite_contract',ROOT/'doc/WASM/tools/check-census.py')
        errors=contract.validate(graph);prefixes=('unresolved reachable edge from ','unimplemented reachable node ')
        require(all(e.startswith(prefixes) for e in errors),'GRAPH_STRUCTURE')
        save(out/'delta.json.gz',delta);save(out/'census.json.gz',graph);save(out/'controls.json',checks)
        resolved=[r for r in proofs if r['status']=='FINITE_EXPRESSION'];remaining=[r for r in proofs if r['status']=='UNRESOLVED']
        save(out/'remaining-calls.json.gz',remaining)
        report=dict(status='PASS',census_status='BLOCKED',gate_credit=False,original_open_calls=len(proofs),
            finite_expression_bounds=len(resolved),remaining_computed_calls=len(remaining),
            lexical_only_bounds=sum(all(t['kind']=='afunc' for t in r['targets']) for r in resolved),
            symbol_cell_expression_bounds=sum(any(t['kind']=='symbol' for t in r['targets']) for r in resolved),
            new_unresolved_cells=len(delta['nodes']),new_cell_value_gaps=len(delta['edges']),
            remaining_reasons=dict(Counter(r['reason'] for r in remaining)),compiler_families=captures,
            graph_nodes=len(graph['nodes']),graph_edges=len(graph['edges']),
            errors={p.strip():sum(e.startswith(p) for e in errors) for p in prefixes},
            native_probes=checks['native_probes'],controls_rejected=checks['controls_rejected']+len(checks['integration']),
            base_sha256=base_sha,graph_sha256=digest(out/'census.json.gz'),
            scope='Finite lexical prototypes and symbol-cell expressions proved from IR; symbol-cell code values and target lowering remain separately unresolved.')
        save(out/'summary.json',report);print(json.dumps(report,sort_keys=True),flush=True);return 0
    except BaseException:
        (out/'failure.txt').write_text(traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--base',type=Path,required=True)
    p.add_argument('--base-sha');p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence')
    sys.exit(execute(p.parse_args()))
