#!/usr/bin/env python3
"""Consolidate builtin slots in the integrated census; expected BLOCKED exit 2."""
import argparse
from datetime import datetime,timezone
import gc
import hashlib
import json
from pathlib import Path
import shutil
import sys
import traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'closure'))
from support import read,save,digest,load_module,source_files,legacy_tools,load_inputs,compressed,require
import slots
from slot_controls import run as controls

OUTPUTS=('facts.json.gz','delta.json.gz','worklists.json.gz','report.json','controls.json')


def materialize(store,pins,values):
    from compose import materialize as previous
    import seeds
    cp=read(HERE.parent/'closure/inputs.json');cv=load_inputs(store,cp);tools=legacy_tools()
    graph,_=previous(cv,cp,tools);graph=seeds.apply(graph,seeds.make(cv,cp,tools))
    require(hashlib.sha256(compressed(graph)).hexdigest()==pins['closure_graph_sha256'],'CLOSURE_RECONSTRUCTION')
    definitions=load_module('builtin_definition_materializer',HERE.parent/'binding-definitions/definition_join.py')
    graph=definitions.apply(graph,values['definitions'])
    require(hashlib.sha256(compressed(graph)).hexdigest()==pins['base_graph_sha256'],'BASE_RECONSTRUCTION')
    return graph


def execute(a):
    out=a.output.resolve();store=a.evidence.resolve();pins=read(HERE/'inputs.json')
    require(ROOT not in out.parents and store not in out.parents and out not in (ROOT,store),'OUTPUT_PATH')
    out.mkdir(parents=True,exist_ok=False)
    sources=set(source_files())|set(HERE.glob('*.py'))|set(HERE.glob('*.json'))
    sources|={HERE.parent/'binding-definitions/definition_join.py'}|{ROOT/n for n in pins['source_sha256']}
    record=dict(version=1,status='ERROR',exit_code=1,command=sys.argv,timestamp=datetime.now(timezone.utc).isoformat(),
                native_execution=False,inputs=pins,source_sha256={str(p.relative_to(ROOT)):digest(p) for p in sorted(sources)},
                review_disposition='NOT_REVIEWED')
    save(out/'run.json',record)
    for p in sources:
        dest=out/'sources'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    try:
        for name,h in pins['source_sha256'].items():require(digest(ROOT/name)==h,'SOURCE_IDENTITY '+name)
        values=load_inputs(store,pins)
        native=slots.native_routes(values['samples'],{n:(ROOT/n).read_bytes() for n in pins['source_sha256']})
        gc.disable()
        if a.base:
            require(digest(a.base)==pins['base_graph_sha256'],'BASE_GRAPH_IDENTITY');base=read(a.base)
        else:base=materialize(store,pins,values)
        print('Accounting for every build-flow call and its exact graph edge.',flush=True)
        obligations=read(HERE/'obligations.json')
        f=slots.facts(values['calls'],values['functions'],base,native,obligations)
        delta=slots.delta(f);graph=slots.apply(base,delta)
        slots.check(base,graph,delta,f,values['calls'],values['functions'],native,obligations)
        checks=controls(base,graph,delta,f,values['calls'],values['functions'],native,obligations,
                        values['samples'],{n:(ROOT/n).read_bytes() for n in pins['source_sha256']})
        print('Builtin site identities joined; checking remaining unresolved target obligations.',flush=True)
        contract=load_module('builtin_slot_contract',ROOT/'doc/WASM/tools/check-census.py')
        errors=contract.validate(graph);prefixes=('unresolved reachable edge from ','unimplemented reachable node ')
        require(all(e.startswith(prefixes) for e in errors),'GRAPH_STRUCTURE')
        counts={p.strip():sum(e.startswith(p) for e in errors) for p in prefixes}
        prior=values['prior_report'];n=len(f['slots']);sites=f['builtin_call_sites']
        require(prior['status']=='BLOCKED' and prior['census_gate_credit'] is False,'PRIOR_SCOPE')
        expected=dict(prior['contract_errors']);expected[prefixes[0].strip()]+=n-sites;expected[prefixes[1].strip()]+=n
        require(counts==expected,'OBLIGATION_RECOUNT')
        # Every prior named population is preserved verbatim. The previous
        # packet remains historical; this derivative adds the missing family.
        work=dict(values['prior_worklists'],version=2,builtin_slots=f['slots'],
                  original_unresolved_build_flow_calls=f['original_unresolved_call_edges'],
                  builtin_call_sites=sites,open_computed_sites=f['open_computed_sites'],
                  builtin_scope=slots.SCOPE)
        require({c['evidence'] for c in work['open_computed_calls']}==set(f['open_computed_evidence']),
                'PRIOR_COMPUTED_WORKLIST')
        report=dict(version=1,status='BLOCKED',exit_code=2,census_gate_credit=False,structure='PASS',scope=slots.SCOPE,
                    graph_nodes=len(graph['nodes']),graph_edges=len(graph['edges']),contract_errors=counts,
                    original_unresolved_build_flow_calls=f['original_unresolved_call_edges'],
                    builtin_call_sites=sites,builtin_slots=n,open_computed_sites=f['open_computed_sites'],
                    remaining_site_edges=f['open_computed_sites'],new_shared_builtin_gap_edges=n,
                    target_lowerings_qualified=0,runtime_bounds_completed=0,
                    graph_change=dict(nodes_added=n,edges_added=n,site_edges_retargeted=sites,
                                      old_nodes_removed=0,other_edges_changed=0,diagnostic_gap_consolidation=sites-n),
                    slot_counts=[dict(index=s['index'],name=s['name'],calls=len(s['call_sites']),
                                      native_subprimitive=s['native_source']['native_subprimitive']) for s in f['slots']],
                    controls_rejected=checks['controls_rejected'],
                    next_work='Qualify the eight target operations with their dependencies; continue the distinct 1,562 computed-call bounds and installation/registry work. Native primitive addresses and displayed names are not target callable identities.')
        for name,value in zip(OUTPUTS,(f,delta,work,report,checks)):save(out/name,value)
        if a.graph:
            save(out/'census.json.gz',graph)
            record['working_graph']=dict(sha256=digest(out/'census.json.gz'),bytes=(out/'census.json.gz').stat().st_size)
        if a.packet:
            p=a.packet.resolve();m=read(p/'packet.json');require(m['id']=='CENSUS-BUILTIN-SLOTS-R1','PACKET_ID')
            for r in m['files']:
                path=p/r['path'];require(path.parent==p and digest(path)==r['sha256'] and path.stat().st_size==r['bytes'],'PACKET_BYTES')
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
    p.add_argument('--base',type=Path,help='Optional exact-hash cache of the reviewed binding-definitions graph.')
    p.add_argument('--graph',action='store_true');p.add_argument('--packet',type=Path)
    sys.exit(execute(p.parse_args()))
