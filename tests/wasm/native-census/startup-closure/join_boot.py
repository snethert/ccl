#!/usr/bin/env python3
"""Integrate reviewed boot execution and cold origins into the census exchange."""
import argparse
from collections import Counter
import gc
import hashlib
import json
from pathlib import Path
import sys
import time
from join_identities import HERE, ROOT, read, save, digest
from assemble import load_tool
from lowering_join import apply_delta as emission_graph
from boot_join import make_delta, apply_delta, canonical
from check_boot import expectations, check, check_materialized
from test_boot_join import run as controls


def bind_inputs(evidence, pins):
    paths = {name: evidence / pin['path'] for name, pin in pins['inputs'].items()}
    for name, path in paths.items():
        if digest(path) != pins['inputs'][name]['sha256']: raise ValueError('changed direct input: ' + name)
    return paths


def load_base(paths, pins):
    base = read(paths['base']); delta = read(paths['emission_delta'])
    if delta['version'] != 2 or delta['base_sha256'] != pins['inputs']['base']['sha256']:
        raise ValueError('emission base identity')
    graph = emission_graph(base, delta)
    graph['inputs_sha256'] = hashlib.sha256(json.dumps({'base': base['inputs_sha256'], 'delta': pins['inputs']['emission_delta']['sha256']}, sort_keys=True).encode()).hexdigest()
    return graph


def run(evidence, output, materialize=None):
    output.mkdir(parents=True, exist_ok=False)
    if materialize and materialize.exists(): raise ValueError('materialization must be new')
    started = time.monotonic(); pins = read(HERE / 'boot-inputs.json')
    report = {'version': 1, 'status': 'FAIL', 'review_disposition': 'NOT_REVIEWED',
              'command': sys.argv, 'input_pins': pins,
              'scope': 'Analysis integration only. No native rebuild, observation changes, archive scan or acceptance change.'}
    try:
        gc.disable(); paths = bind_inputs(evidence, pins)
        sources = [HERE / n for n in ('join_boot.py','boot_join.py','check_boot.py','test_boot_join.py','boot-inputs.json',
                   'join_identities.py','assemble.py','lowering_join.py','identity_join.py','exchange.py','effects.py')]
        sources += [HERE.parent/'boot-observation/analyze.py', ROOT/'doc/WASM/tools/check-census.py',
                    ROOT/'doc/WASM/contracts/census.schema.json', ROOT/'doc/WASM/stage0/baseline.json', ROOT/'doc/WASM/stage0/inventory.json']
        report['source_sha256'] = {str(p.relative_to(ROOT)): digest(p) for p in sources}
        print('Pinned direct inputs verified; reconstructing the reviewed emission graph.', flush=True)
        base = load_base(paths, pins)
        temp = output/'prior-base.json.gz'; save(temp, base)
        if digest(temp) != read(paths['emission_materialization'])['materialization']['output_sha256']:
            raise ValueError('reviewed base materialization differs')
        report['prior_graph_reproduced'] = True; temp.unlink()
        analyzer = load_tool('boot_integration_source_analyzer', HERE.parent/'boot-observation/analyze.py')
        rows = analyzer.read(paths['boot_events']); boot = analyzer.analyze(rows)
        if boot != read(paths['boot_joins']): raise ValueError('boot analysis differs from reviewed joins')
        files = read(paths['boot_files']); origins = read(paths['origins'])
        origin_run = read(paths['origins_run']); boot_run = read(paths['boot_run'])
        original = [v for p,v in origin_run['inputs'].items() if p.endswith('/2026-09-13-boot-observation-r1/capture/events.jsonl.gz')]
        if (origin_run['status'] != 'PASS' or not origin_run['fresh_boot_stream_identical_after_root_relocation'] or
                original != [pins['inputs']['boot_events']['sha256']] or origin_run['kernel']['sha256'] != boot_run['kernel']['sha256']):
            raise ValueError('origin execution binding')
        report['scope_counts'] = boot['summary']
        print('Reviewed boot analysis reproduced; constructing bounded graph additions.', flush=True)
        binding = {k:v['sha256'] for k,v in pins['inputs'].items()}
        expected = expectations(base, rows, boot, files, origins, binding)
        delta = make_delta(base, rows, boot, files, origins, binding); check(delta, expected)
        graph = apply_delta(base, delta); check_materialized(base, graph, delta)
        print('Checking genuine omission/insertion controls and the complete exchange graph.', flush=True)
        tests = controls(base, delta, expected, graph)
        # Actual absolute/relative aliases must bind identical bytes. Exercise
        # each derivation against a disagreement in the retained alias witness.
        from copy import deepcopy
        aliased = next(r['relative_path'] for r in files['files'] if sum(s['relative_path']==r['relative_path'] for s in files['files']) > 1)
        corrupted = deepcopy(files)
        next(r for r in corrupted['files'] if r['relative_path']==aliased)['sha256'] = '0'*64
        for label, producer in (('producer',make_delta),('checker',expectations)):
            try: producer(base,rows,boot,corrupted,origins,binding)
            except ValueError as exc:
                if str(exc) != 'FILE_ALIAS_BYTES': raise
            else: raise ValueError('inconsistent file alias escaped '+label)
            tests['controls'].append({'name':'inconsistent-file-alias-'+label,'status':'REJECTED','reason':'FILE_ALIAS_BYTES'})
        tests['controls_rejected'] = len(tests['controls'])
        contract = load_tool('boot_integration_contract', ROOT/'doc/WASM/tools/check-census.py')
        errors = contract.validate(graph)
        prefixes = ('unresolved reachable edge from ', 'unimplemented reachable node ')
        unexpected = [e for e in errors if not e.startswith(prefixes)]
        if unexpected: raise ValueError('graph invariant: ' + '; '.join(unexpected[:3]))
        # Serialize only the additive fragment. Full graphs are reproducible and
        # optional; neither the prior graph nor unchanged capture is duplicated.
        save(output/'delta.json.gz',delta); save(output/'controls.json',tests)
        if materialize:
            save(materialize, graph)
            report['materialization'] = {'path':str(materialize),'sha256':digest(materialize),
                                         'bytes':materialize.stat().st_size,'nodes':len(graph['nodes']),'edges':len(graph['edges'])}
        summary = {'version':1,'status':'BOOT_INTEGRATED_UNQUALIFIED','review_disposition':'NOT_REVIEWED',
                   **boot['summary'],'source_modules':origins['summary']['modules'],
                   'loaded_file_names':len(files['files']),
                   'loaded_file_paths':len({r['relative_path'] for r in files['files']}),
                   'source_contexts':origins['summary']['with_source_context'],
                   'missing_source_contexts':origins['summary']['without_source_context'],
                   'opaque_binding_values':sum(r['kind']=='store' and r['disposition']=='unresolved' for r in delta['nodes']),
                   'delta_nodes':len(delta['nodes']),'delta_edges':len(delta['edges']),
                   'event_initializers':len(delta['initializers']),'delta_modules':len(delta['unobserved_modules']),
                   'graph_nodes':len(graph['nodes']),'graph_edges':len(graph['edges']),
                   'controls_rejected':tests['controls_rejected'],'schema_and_graph_invariants':'PASS',
                   'census_contract':'BLOCKED','census_error_counts':{p.strip():sum(e.startswith(p) for e in errors) for p in prefixes},
                   'scope':'Distinct boot identities, observed event order and explicit source-inventory membership; no cross-run callable equivalence.',
                   'remaining':['Source traversal against the registered target, reviewed seeds and conservative dynamic-call bounds.',
                                'Opaque function-cell contents, remaining lowering/import/store classifications and final scenario reconciliation.'],
                   'stage0_gate':{'accepted':28,'missing':20,'unreviewed':0,'new_credit':0,'basis':'Accepted aggregate unchanged; gate not rerun.'}}
        save(output/'summary.json',summary)
        report.update(status='PASS',elapsed_seconds=round(time.monotonic()-started,3),
                      artifacts=[{'path':p.name,'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(output.iterdir()) if p.name!='run.json'])
        return summary
    except BaseException as exc:
        report['error']=type(exc).__name__+': '+str(exc);raise
    finally:
        gc.enable();save(output/'run.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--materialize',type=Path,help='Optional new gzip exchange graph file outside the retained packet.')
    a=p.parse_args();print(json.dumps(run(a.evidence_root.resolve(),a.output.resolve(),a.materialize.resolve() if a.materialize else None),indent=2))
