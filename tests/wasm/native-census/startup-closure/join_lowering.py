#!/usr/bin/env python3
"""Join native emissions and parameterized subprimitive targets without a rebuild."""
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
from analyze import events
from lowering_join import capture, make_delta, apply_delta
from check_lowering import check
from test_lowering import run as controls


def run(evidence, output):
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic(); pins = read(HERE / 'lowering-inputs.json')
    report = {'version': 1, 'status': 'FAIL', 'review_disposition': 'NOT_REVIEWED',
              'command': sys.argv, 'input_pins': pins,
              'scope': 'Native emission dependency joins and explicit subprimitive operands only. No native execution, static-closure qualification, archive scan or acceptance change.'}
    try:
        paths = {name: evidence / pin['path'] for name, pin in pins['inputs'].items()}
        for name, path in paths.items():
            if digest(path) != pins['inputs'][name]['sha256']: raise ValueError('changed direct input: ' + name)
        source = ROOT / pins['template_source']['path']
        if digest(source) != pins['template_source']['sha256']: raise ValueError('changed subprimitive operand definitions')
        dependencies = ['join_lowering.py', 'lowering_join.py', 'check_lowering.py', 'test_lowering.py',
                        'lowering-inputs.json', 'join_identities.py', 'identity_join.py', 'exchange.py', 'effects.py', 'assemble.py', 'test_identity_join.py']
        sources = [HERE / n for n in dependencies] + [source, HERE.parent / 'rich-observation/analyze.py',
                   ROOT / 'doc/WASM/tools/check-census.py', ROOT / 'doc/WASM/contracts/census.schema.json',
                   ROOT / 'doc/WASM/stage0/baseline.json', ROOT / 'doc/WASM/stage0/inventory.json']
        report['source_sha256'] = {str(p.relative_to(ROOT)): digest(p) for p in sources}
        build = read(paths['build_run']); inspected = read(paths['image_run'])
        kernels = [v for k, v in inspected['input_sha256'].items() if Path(k).name == 'dx86cl64']
        if kernels != [build['kernel']['sha256']]: raise ValueError('subprimitive table and build use different kernels')
        report['same_kernel_sha256'] = kernels[0]
        print('Direct inputs verified; reading reviewed emissions and the same-kernel table.', flush=True)
        gc.disable(); reviewed = read(paths['joins']); image = read(paths['image'])
        print('Joining raw operands and checking every emission against the reviewed capture.', flush=True)
        facts, samples, oracle = capture(events(paths['events']), reviewed, image['subprimitives'])
        save(output / 'joins.json.gz', facts)
        save(output / 'operand-samples.json', {'scope': 'First retained raw event for each exercised decoder family.', 'samples': samples})
        base = read(paths['base']); base_hash = pins['inputs']['base']['sha256']
        delta = make_delta(base, facts, base_hash); check(base, delta, facts, base_hash)
        print('Emission joins complete; exercising omission, substitution and operand controls.', flush=True)
        tests = controls(base, delta, facts, reviewed, oracle, {r['offset']: r['name'] for r in image['subprimitives']}, samples, base_hash)
        graph = apply_delta(base, delta)
        contract = load_tool('emission_census_contract', ROOT / 'doc/WASM/tools/check-census.py')
        errors = contract.validate(graph)
        prefixes = ('unresolved reachable edge from ', 'unimplemented reachable node ')
        unexpected = [e for e in errors if not e.startswith(prefixes)]
        if unexpected: raise ValueError('graph invariant: ' + '; '.join(unexpected[:3]))
        summary = {'version': 1, 'status': 'EMISSIONS_JOINED_UNQUALIFIED', 'review_disposition': 'NOT_REVIEWED',
                   **facts['summary'], 'delta_nodes': len(delta['nodes']), 'delta_edges': len(delta['edges']),
                   'controls_rejected': len(tests['controls']), 'synthetic_operand_layout_cases': len(tests['operand_layout_cases']),
                   'schema_and_graph_invariants': 'PASS', 'census_contract': 'BLOCKED',
                   'census_error_counts': {p.strip(): sum(e.startswith(p) for e in errors) for p in prefixes},
                   'stage0_gate': {'accepted': 28, 'missing': 21, 'unreviewed': 0, 'basis': 'Accepted records unchanged; gate not rerun.'},
                   'scope': facts['scope'], 'remaining': ['Boot-image subprocess witness and full target traversal.',
                   'Reviewed seed set and conservative dynamic-call bounds.', 'Other subprimitive paths, imports, stores, trap classification and target dispositions.']}
        save(output / 'delta.json.gz', delta); save(output / 'controls.json', tests); save(output / 'summary.json', summary)
        report.update(status='PASS', elapsed_seconds=round(time.monotonic() - started, 3),
                      artifacts=[{'path': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)}
                                 for p in sorted(output.iterdir()) if p.name != 'run.json'])
        return summary
    except BaseException as exc:
        report['error'] = type(exc).__name__ + ': ' + str(exc); raise
    finally:
        gc.enable(); save(output / 'run.json', report)


def materialize(evidence, packet, output):
    """Apply a retained additive fragment to its pinned base, into a new file."""
    if output.exists(): raise ValueError('output must be new')
    run_record = read(packet / 'run.json')
    if run_record['status'] != 'PASS': raise ValueError('fragment execution did not pass')
    for name in ('delta.json.gz', 'joins.json.gz'):
        entry = next(r for r in run_record['artifacts'] if r['path'] == name)
        if digest(packet / name) != entry['sha256']: raise ValueError('changed fragment artifact: ' + name)
    pin = run_record['input_pins']['inputs']['base']; path = evidence / pin['path']
    if digest(path) != pin['sha256']: raise ValueError('changed base graph')
    base = read(path); delta = read(packet / 'delta.json.gz'); facts = read(packet / 'joins.json.gz')
    check(base, delta, facts, pin['sha256']); graph = apply_delta(base, delta)
    graph['inputs_sha256'] = hashlib.sha256(json.dumps({'base': base['inputs_sha256'], 'delta': digest(packet / 'delta.json.gz')}, sort_keys=True).encode()).hexdigest()
    save(output, graph)
    return {'status': 'MATERIALIZED_UNQUALIFIED', 'nodes': len(graph['nodes']), 'edges': len(graph['edges'])}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--evidence-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); p.add_argument('--materialize', type=Path, metavar='PACKET_DIRECTORY')
    a = p.parse_args()
    print(json.dumps(materialize(a.evidence_root.resolve(), a.materialize.resolve(), a.output.resolve()) if a.materialize
                     else run(a.evidence_root.resolve(), a.output.resolve()), indent=2))
