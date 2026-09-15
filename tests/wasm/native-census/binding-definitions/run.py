#!/usr/bin/env python3
"""Join the 95-cell source batch into the development graph; expected exit 2."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import gc
import json
from pathlib import Path
import shutil
import sys
import traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'closure'))
from support import read,save,digest,load_module,source_files,legacy_tools,load_inputs,compressed
from definition_join import require,collect,replay,patch,apply,check
from classification import classify
from batch_controls import run as controls

OUTPUTS=('facts.json.gz','witnesses.jsonl.gz','delta.json.gz','classification.json','report.json','controls.json')

def execute(a):
    out=a.output.resolve();store=a.evidence.resolve()
    require(ROOT not in out.parents and store not in out.parents and out!=ROOT and out!=store,'OUTPUT_PATH')
    out.mkdir(parents=True,exist_ok=False);pins=read(HERE/'inputs.json')
    sources=set(source_files())|set(HERE.glob('*.py'))|set(HERE.glob('*.json'))
    sources|={ROOT/n for n in pins['source_sha256']}
    sources|={HERE.parent/'rich-observation/observer.lisp'}
    record=dict(version=1,status='ERROR',exit_code=1,command=sys.argv,timestamp=datetime.now(timezone.utc).isoformat(),
                native_execution=False,source_sha256={str(p.relative_to(ROOT)):digest(p) for p in sorted(sources)},
                inputs=pins,review_disposition='NOT_REVIEWED')
    save(out/'run.json',record)
    for p in sources:
        dest=out/'sources'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    try:
        for name,h in pins['source_sha256'].items():require(digest(ROOT/name)==h,'SOURCE_IDENTITY '+name)
        paths={k:store/r['path'] for k,r in pins['inputs'].items()}
        for k,p in paths.items():require(digest(p)==pins['inputs'][k]['sha256'],'INPUT_IDENTITY '+k)
        values={k:read(p) for k,p in paths.items() if k!='stream'}
        source_work=read(HERE/'source-work.json')
        for r in source_work['records']:
            s=r['source'];raw=(ROOT/s['path']).read_bytes();marker=s['marker'].encode();start=s['byte_offset']
            require(pins['source_sha256'][s['path']]==s['sha256'] and raw[start:start+len(marker)]==marker and
                    raw[:start].count(b'\n')+1==s['line'],'SOURCE_ANCHOR')
        print('Reading the retained build for exact compiler/declaration identities.',flush=True)
        facts=collect(paths['stream'],values['histories'],values['functions'],out/'witnesses.jsonl.gz')
        replay(out/'witnesses.jsonl.gz',values['histories'],values['functions'],facts)
        classification=classify(values['histories'],facts,source_work)
        save(out/'facts.json.gz',facts);save(out/'classification.json',classification)
        print('The 95-cell batch is accounted for; integrating compile-phase references.',flush=True)
        gc.disable()
        if a.base:
            require(digest(a.base)==pins['base_graph_sha256'],'BASE_GRAPH_IDENTITY');base=read(a.base)
        else:
            from compose import materialize
            import seeds
            cp=read(HERE.parent/'closure/inputs.json');cv=load_inputs(store,cp);tools=legacy_tools()
            previous,_=materialize(cv,cp,tools);d=seeds.make(cv,cp,tools);base=seeds.apply(previous,d)
            import hashlib
            require(hashlib.sha256(compressed(base)).hexdigest()==pins['base_graph_sha256'],'BASE_RECONSTRUCTION')
        delta=patch(facts);graph=apply(base,delta);check(base,graph,delta,facts)
        checks=controls(base,graph,delta,facts,values['histories'],values['functions'],out/'witnesses.jsonl.gz',source_work)
        contract=load_module('binding_definition_contract',ROOT/'doc/WASM/tools/check-census.py')
        errors=contract.validate(graph);prefixes=('unresolved reachable edge from ','unimplemented reachable node ')
        require(all(e.startswith(prefixes) for e in errors),'GRAPH_STRUCTURE')
        error_counts={p.strip():sum(e.startswith(p) for e in errors) for p in prefixes}
        prior=values['prior_report'];require(prior['status']=='BLOCKED','PRIOR_QUALIFICATION')
        require(error_counts['unresolved reachable edge from']==prior['counts']['unresolved_edges'] and
                error_counts['unimplemented reachable node']==prior['counts']['unimplemented_nodes']+len(delta['nodes']), 'OBLIGATION_RECOUNT')
        report=dict(version=1,status='BLOCKED',exit_code=2,census_gate_credit=False,structure='PASS',
                    scope=facts['scope'],classification=classification['counts'],symbols=95,call_sites=classification['call_sites'],
                    compiled_name_identities=len(facts['compiled']),accessor_declaration_events=len(facts['declarations']),
                    graph_nodes=len(graph['nodes']),graph_edges=len(graph['edges']),contract_errors=error_counts,
                    graph_change=dict(nodes=len(delta['nodes']),edges=len(delta['edges']),prior_records_changed=0,
                                      original_runtime_obligations_closed=0,new_class_construction_gaps=len(delta['nodes'])),
                    runtime_unwitnessed_cells=95,runtime_unbounded_cells=prior['counts']['called_symbol_cells'],
                    open_computed_calls=prior['counts']['open_computed_sites'],original_body_obligations=prior['counts']['original_body_obligations'],
                    controls_rejected=checks['controls_rejected'],
                    next_work='Join module loading/installation and SETF registry identities where required; apply actual parameter/registry bounds. A fresh combined capture is permitted when faster.')
        for name,value in (('delta.json.gz',delta),('report.json',report),('controls.json',checks)):save(out/name,value)
        if a.graph:
            save(out/'census.json.gz',graph)
            record['working_graph']=dict(sha256=digest(out/'census.json.gz'),bytes=(out/'census.json.gz').stat().st_size)
        if a.packet:
            p=a.packet.resolve();m=read(p/'packet.json')
            require(m['id']=='CENSUS-BINDING-DEFINITIONS-R1','PACKET_ID')
            for r in m['files']:
                f=p/r['path'];require(f.parent==p and digest(f)==r['sha256'] and f.stat().st_size==r['bytes'],'PACKET_BYTES')
            require(read(p/'sources.json')==record['source_sha256'],'PACKET_SOURCES')
            for name in OUTPUTS:require((out/name).read_bytes()==(p/name).read_bytes(),'REPRODUCTION '+name)
            record['reproduced_outputs']=len(OUTPUTS)
        record.update(status='BLOCKED',exit_code=2,analysis_completed=True)
        print(json.dumps(report,sort_keys=True),flush=True);return 2
    except BaseException:
        (out/'failure.txt').write_text(traceback.format_exc());raise
    finally:
        gc.enable();save(out/'run.json',record)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence')
    p.add_argument('--base',type=Path,help='Optional cached previous development graph; exact retained hash required.')
    p.add_argument('--graph',action='store_true')
    p.add_argument('--packet',type=Path)
    sys.exit(execute(p.parse_args()))
