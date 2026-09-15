#!/usr/bin/env python3
"""Apply local argument/capture bounds to the preceding working census.

Uses the preceding pass's complete selected IR cache. Run and replay produce
local working output only; neither command publishes evidence or changes a gate.
"""
import argparse
from collections import Counter
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import traceback

from run import HERE,ROOT,convert,read,save,digest,require,load_module,integrate
from lexical import Resolver
from test_lexical import check as check_native

HISTORIES='2026-09-14-binding-versions-r1/histories.json.gz'
HISTORIES_SHA='4054a5980aa83a5d22b2749f90683acab663ed3a405d9276cabd4053c544bd69'


def inputs(previous,store):
    paths={name:previous/name for name in ('selected-ir.jsonl.gz','proofs.json.gz','census.json.gz','summary.json')}
    pins=read(HERE.parent/'builtin-slots/inputs.json')['inputs']
    for name in ('calls','samples'):
        paths[name]=store/pins[name]['path']
        require(digest(paths[name])==pins[name]['sha256'],'INPUT_IDENTITY '+name)
    paths['histories']=store/HISTORIES
    require(digest(paths['histories'])==HISTORIES_SHA,'INPUT_IDENTITY histories')
    report=read(paths['summary.json'])
    require(report['status']=='PASS' and report['census_status']=='BLOCKED' and report['gate_credit'] is False,
            'PREVIOUS_SCOPE')
    require(digest(paths['census.json.gz'])==report['graph_sha256'],'PREVIOUS_GRAPH')
    previous_proofs=read(paths['proofs.json.gz']);calls=read(paths['calls'])
    wanted={(r['function_id'],r['site_id']):r for r in calls
            if r['dependency']['category'] in ('function-variable','computed-callee')
            and not r.get('lexical_bound',{}).get('targets')}
    old={(r['function_id'],r['site_id']):r for r in previous_proofs}
    require(len(old)==len(previous_proofs)==report['original_open_calls'] and old.keys()==wanted.keys(),
            'PREVIOUS_POPULATION')
    require(sum(r['status']=='FINITE_EXPRESSION' for r in previous_proofs)==report['finite_expression_bounds'] and
            sum(r['status']=='UNRESOLVED' for r in previous_proofs)==report['remaining_computed_calls'] and
            all(r['status'] in ('FINITE_EXPRESSION','UNRESOLVED') for r in previous_proofs),'PREVIOUS_PARTITION')
    sample=next(iter(read(paths['samples']).values()))
    operators={int(k):v for k,v in sample['operators'].items()}
    identities={k:dict(path=str(p),sha256=digest(p)) for k,p in paths.items()}
    return wanted,old,operators,identities


def collect(selected,wanted,old,operators,resolver_class=Resolver):
    seen=set();found={};preserved={};events={r['event'] for r in wanted.values()}
    with gzip.open(selected,'rt') as src:
        for line in src:
            row=json.loads(line);seq=row['sequence']
            require(seq in events and seq not in seen and row['kind'] in ('before-pass2','frontend'),'CACHE_EVENT')
            seen.add(seq);resolver=resolver_class(convert(row['payload'],operators))
            native_calls={(f['function_id'],c['site_id']):c for f in resolver.family.values() for c in f['calls']}
            symbols={n['id']:n for n in row['payload']['ir']['objects'] if n['kind']=='symbol'}
            for result in resolver.calls():
                key=(result['function_id'],result['site_id'])
                if key not in wanted:continue
                original=wanted[key];prior=old[key]
                require(key not in found and key not in preserved and original['event']==seq and
                        original['dependency']==native_calls[key]['dependency'],'ORIGINAL_CALL_JOIN')
                for target in result['targets']:
                    if target['kind']=='symbol':
                        symbol=symbols.get(target['id'],getattr(resolver,'auxiliary_symbols',{}).get(target['id']))
                        require(symbol is not None and symbol['id']==target['id'],'PROOF_SYMBOL_DESCRIPTOR')
                        target['descriptor']=symbol
                result.update(event=seq,source=row['source'],source_position=row['source_position'],
                              old_reason=original.get('lexical_bound'))
                if prior['status']=='FINITE_EXPRESSION':
                    require(result['status']=='FINITE_EXPRESSION' and result['targets']==prior['targets'],
                            'EARLIER_BOUND_CHANGED')
                    preserved[key]=dict(function_id=key[0],site_id=key[1],targets=result['targets'])
                else:found[key]=result
            if len(seen)%150==0:print(f'Analyzed {len(seen)} original compiler families.',flush=True)
    require(seen==events and set(found)|set(preserved)==set(wanted),'CACHE_POPULATION_COVERAGE')
    return [found[k] for k in sorted(found)],[preserved[k] for k in sorted(preserved)],len(seen)


def native(out,store):
    work=out/'native';work.mkdir()
    pins=read(HERE.parent/'source-traversal/inputs.json')['inputs']
    with tarfile.open(store/pins['source']['path']) as archive:archive.extractall(work,filter='data')
    binary=work/'dx86cl64';shutil.copyfile(store/pins['kernel']['path'],binary);binary.chmod(0o755)
    env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(work),FINITE_OUTPUT=str(out/'native-probes.json'))
    argv=[str(binary),'--image-name',str(store/pins['image']['path']),'--no-init','--batch']
    for name in ('observer.lisp','dependencies.lisp','rich-observation/observer.lisp',
                 'finite-callees/probes.lisp','finite-callees/lexical-probes.lisp'):
        argv+=['--load',str(HERE.parent/name)]
    argv+=['--eval','(progn (census-finite-probes::run) (ccl:quit))']
    save(out/'native-command.json',dict(argv=argv,cwd=str(work),
         inputs={k:pins[k] for k in ('source','kernel','image')}))
    with (out/'native.log').open('w') as log:
        p=subprocess.run(argv,cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60)
    require(p.returncode==0,'NATIVE_EXIT')
    return check_native(read(out/'native-probes.json'),convert)


def summarize(proofs,preserved,graph,delta,checks,families,errors):
    good=[r for r in proofs if r['status']=='FINITE_EXPRESSION'];remaining=[r for r in proofs if r['status']=='UNRESOLVED']
    prefixes=('unresolved reachable edge from ','unimplemented reachable node ')
    require(all(e.startswith(prefixes) for e in errors),'GRAPH_STRUCTURE')
    return dict(status='PASS',census_status='BLOCKED',gate_credit=False,prior_open_calls=len(proofs),
        new_finite_bounds=len(good),preserved_bounds=len(preserved),remaining_computed_calls=len(remaining),
        lexical_prototype_bounds=sum(all(t['kind']=='afunc' for t in r['targets']) for r in good),
        symbol_cell_expression_bounds=sum(any(t['kind']=='symbol' for t in r['targets']) for r in good),
        remaining_reasons=dict(Counter(r['reason'] for r in remaining)),compiler_families=families,
        new_unresolved_cells=len(delta['nodes']),graph_nodes=len(graph['nodes']),graph_edges=len(graph['edges']),
        errors={p.strip():sum(e.startswith(p) for e in errors) for p in prefixes},
        native_probes=checks['native_probes'],controls_rejected=checks['controls_rejected']+len(checks['integration']),
        scope='Exhaustive local argument flow and immutable captures. Symbol-cell contents and target lowering remain unresolved.')


def run(a):
    out=a.output.resolve();store=a.evidence.resolve();previous=a.previous.resolve()
    require(ROOT not in out.parents and store not in out.parents,'OUTPUT_PATH');out.mkdir(parents=True,exist_ok=False)
    shutil.copytree(HERE,out/'executed-sources',ignore=shutil.ignore_patterns('__pycache__'))
    try:
        wanted,old,ops,identities=inputs(previous,store);save(out/'inputs.json',identities)
        print('Running native argument-flow and capture probes.',flush=True);checks=native(out,store)
        proofs,preserved,families=collect(previous/'selected-ir.jsonl.gz',wanted,old,ops)
        save(out/'proofs.json.gz',proofs);save(out/'preserved-bounds.json.gz',preserved)
        save(out/'remaining-calls.json.gz',[r for r in proofs if r['status']=='UNRESOLVED'])
        base=read(previous/'census.json.gz');histories=read(store/HISTORIES)
        delta=integrate.patch(base,proofs,histories);graph=integrate.apply(base,delta)
        integrate.check(base,graph,delta,proofs,histories)
        checks['integration']=integrate.controls(base,graph,delta,proofs,histories)
        print('Applying the new bounds to the working census.',flush=True)
        errors=load_module('lexical_contract',ROOT/'doc/WASM/tools/check-census.py').validate(graph)
        save(out/'delta.json.gz',delta);save(out/'census.json.gz',graph);save(out/'controls.json',checks)
        report=summarize(proofs,preserved,graph,delta,checks,families,errors)
        report['graph_sha256']=digest(out/'census.json.gz');save(out/'summary.json',report)
        print(json.dumps(report,sort_keys=True),flush=True)
    except BaseException:
        (out/'failure.txt').write_text(traceback.format_exc());raise


def verify(a):
    out=a.output.resolve();store=a.evidence.resolve();identities=read(out/'inputs.json')
    for name,row in identities.items():require(digest(Path(row['path']))==row['sha256'],'REPLAY_INPUT '+name)
    previous=Path(identities['proofs.json.gz']['path']).parent
    for source in (out/'executed-sources').iterdir():
        if source.is_file():require(source.read_bytes()==(HERE/source.name).read_bytes(),'EXECUTED_SOURCE '+source.name)
    wanted,old,ops,current=inputs(previous,store);require(current==identities,'REPLAY_IDENTITIES')
    proofs,preserved,families=collect(previous/'selected-ir.jsonl.gz',wanted,old,ops)
    require(proofs==read(out/'proofs.json.gz') and preserved==read(out/'preserved-bounds.json.gz'),'REPLAY_PROOFS')
    require([r for r in proofs if r['status']=='UNRESOLVED']==read(out/'remaining-calls.json.gz'),'REPLAY_REMAINDER')
    checks=check_native(read(out/'native-probes.json'),convert)
    base=read(previous/'census.json.gz');graph=read(out/'census.json.gz');delta=read(out/'delta.json.gz');hs=read(store/HISTORIES)
    integrate.check(base,graph,delta,proofs,hs)
    checks['integration']=integrate.controls(base,graph,delta,proofs,hs)
    require(checks==read(out/'controls.json'),'REPLAY_CONTROLS')
    report=read(out/'summary.json')
    require(digest(out/'census.json.gz')==report['graph_sha256'],'REPLAY_GRAPH')
    errors=load_module('lexical_replay_contract',ROOT/'doc/WASM/tools/check-census.py').validate(graph)
    expected=summarize(proofs,preserved,graph,delta,checks,families,errors)
    expected['graph_sha256']=report['graph_sha256'];require(expected==report,'REPLAY_SUMMARY')
    result=dict(status='PASS',replayed_calls=len(proofs)+len(preserved),new_bounds=report['new_finite_bounds'],
                preserved_bounds=len(preserved),remaining=report['remaining_computed_calls'],
                native_probes=checks['native_probes'],controls_rejected=report['controls_rejected'],graph_identical=True)
    save(out/'verification.json',result);print(result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('run','verify'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--previous',type=Path)
    p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');a=p.parse_args()
    if a.action=='run':
        if a.previous is None:p.error('--previous is required for run')
        run(a)
    else:verify(a)
