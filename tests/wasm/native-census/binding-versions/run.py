#!/usr/bin/env python3
"""Join recorded global binding versions and consolidate census obligations."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import gc
import importlib.util
import platform
import shutil
import sys
import traceback
from pathlib import Path
from common import HERE,ROOT,require,read,save,digest
from collect import collect
from history import assemble,check as check_history
from links import make,check,apply
from controls import run as controls


def load_inputs(evidence,base):
    manifest=read(HERE/'inputs.json'); values={}
    for name,r in manifest['inputs'].items():
        path=base if name=='base' else evidence/r['path']
        require(digest(path)==r['sha256'],'INPUT_IDENTITY '+name)
        values[name]=path if name=='events' else read(path)
    original=values['base'];prior=values['flow_delta']
    values['base']=dict(original,nodes=original['nodes']+prior['nodes'],edges=original['edges']+prior['edges'],
                        profile=original['profile']+'; '+prior['scope'])
    return values


def project(base,histories,calls):
    delta=make(base,histories,calls);check(delta,base,histories,calls);graph=apply(base,delta)
    spec=importlib.util.spec_from_file_location('binding_contract',ROOT/'doc/WASM/tools/check-census.py')
    contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
    errors=contract.validate(graph)
    prefixes=('unresolved reachable edge from ','unimplemented reachable node ')
    other=[e for e in errors if not e.startswith(prefixes)]
    require(not other,'EXCHANGE_INVARIANT '+str(other[:3]))
    require(all(graph[k]==v for k,v in base.items() if k not in ('nodes','edges','profile')),'BASE_METADATA_CHANGED')
    return delta,dict(structural_contract='PASS',closure='BLOCKED',graph_nodes=len(graph['nodes']),
        graph_edges=len(graph['edges']),call_sites_retargeted=len(delta['replacements']),
        superseded_name_placeholders=len(delta['removed_name_nodes']),
        binding_obligations=sum(e['evidence'].startswith('binding-versions/open/') for e in delta['edges']),
        observed_body_joins=sum(e['evidence'].startswith('binding-versions/body/') and e['resolution']=='complete' for e in delta['edges']),
        observed_bodies_unjoined=sum(e['evidence'].startswith('binding-versions/body/') and e['resolution']=='unresolved' for e in delta['edges']),
        errors={p.strip():sum(e.startswith(p) for e in errors) for p in prefixes},
        computed_calls_unchanged=True,builtin_calls_unchanged=True,widening_edges_unchanged=True)


def execute(inputs,output):
    print('Reading retained binding inventories and store/loader events.',flush=True)
    facts,samples=collect(inputs['events']);save(output/'facts.json.gz',facts)
    histories,summary=assemble(facts,inputs['functions'],inputs['calls'])
    check_history(histories,summary,facts,inputs['functions'],inputs['calls'])
    save(output/'histories.json.gz',histories)
    print('Checking consolidated graph and omission/insertion controls.',flush=True)
    delta,integration=project(inputs['base'],histories,inputs['calls'])
    checks=controls(facts,inputs['functions'],inputs['calls'],histories,summary,delta,inputs['base'],samples)
    summary.update(integration=integration,controls_rejected=checks['controls_rejected'])
    for name,value in [('delta.json.gz',delta),('summary.json',summary),('controls.json',checks)]:save(output/name,value)
    print(__import__('json').dumps(summary,sort_keys=True),flush=True)
    return summary


def run(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    paths=sorted(HERE.glob('*.py'))+[HERE/'inputs.json',HERE.parent/'rich-observation/analyze.py',
        HERE.parent/'rich-observation/observer.lisp',HERE.parent/'rich-observation/build_patch.py',
        ROOT/'level-0/l0-def.lisp',ROOT/'xdump/xx8664-fasload.lisp',
        ROOT/'doc/WASM/tools/check-census.py',ROOT/'doc/WASM/contracts/census.schema.json']
    for p in paths:
        dst=out/'sources'/p.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
    save(out/'run.json',dict(started=datetime.now(timezone.utc).isoformat(),command=sys.argv,
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in paths},inputs=read(HERE/'inputs.json'),
        host=platform.platform(),python=platform.python_version(),python_executable_sha256=digest(Path(sys.executable))))
    try:
        gc.disable(); summary=execute(load_inputs(args.evidence,args.base),out)
        require(summary['census_gate_credit'] is False,'FALSE_GATE_CREDIT')
    except BaseException:
        (out/'failure.txt').write_text(traceback.format_exc());raise
    finally:gc.enable()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('evidence','base','output'):p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())
