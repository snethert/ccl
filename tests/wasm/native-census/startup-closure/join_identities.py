#!/usr/bin/env python3
"""Integrate reviewed execution identities; reuse unchanged evidence and controls."""
import argparse
from collections import Counter
import gc
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

from assemble import load_tool, digest
from identity_join import extend, check
from test_identity_join import run as controls

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent / 'rich-observation'))
from analyze import Graph, events


def save(path, value):
    if path.suffix == '.gz':
        with path.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0, compresslevel=6) as compressed:
            import io
            with io.TextIOWrapper(compressed, encoding='utf-8') as stream:
                json.dump(value, stream, separators=(',', ':'), ensure_ascii=False); stream.write('\n')
    else:
        path.write_text(json.dumps(value, indent=2) + '\n')


def read(path):
    with (gzip.open(path, 'rt') if path.suffix == '.gz' else path.open()) as stream:
        return json.load(stream)


def cold_calls(path):
    pending = {}; result = []
    for row in events(path):
        if row['kind'] not in ('startup-enter', 'startup-return'): continue
        g = Graph(row['payload']['function']); code = g.function(g.root)
        if row['kind'] == 'startup-enter':
            if row['process'] in pending: raise ValueError('nested cold callback')
            pending[row['process']] = {'initializer': row['sequence'], 'function': code}
        else:
            before = pending.pop(row['process'])
            if before['initializer'] != row['parent'] or before['function'] != code:
                raise ValueError('cold callback identity changed across return')
            result.append({**before, 'return': row['sequence']})
    if pending or len(result) != 35: raise ValueError('incomplete cold callback coverage')
    return result


def run(evidence, output):
    output.mkdir(parents=True, exist_ok=False)
    pins = json.loads((HERE / 'identity-inputs.json').read_text())
    paths = {name: evidence / r['path'] for name, r in pins['inputs'].items()}
    report = {'version': 1, 'status': 'FAIL', 'review_disposition': 'NOT_REVIEWED',
              'input_pins': pins, 'command': sys.argv,
              'verification_scope': 'New integration and direct retained joins only; no native rebuild, archive audit, aggregate regeneration or rerun of unchanged controls.'}
    start = time.monotonic()
    try:
        for name, path in paths.items():
            if digest(path) != pins['inputs'][name]['sha256']: raise ValueError('changed input: ' + name)
        sources = [HERE / n for n in ('join_identities.py', 'identity_join.py', 'test_identity_join.py', 'identity-inputs.json', 'assemble.py', 'exchange.py', 'effects.py')]
        sources += [HERE.parent / 'rich-observation/analyze.py', ROOT / 'doc/WASM/tools/check-census.py', ROOT / 'doc/WASM/contracts/census.schema.json', ROOT / 'doc/WASM/stage0/baseline.json', ROOT / 'doc/WASM/stage0/inventory.json']
        report['source_sha256'] = {str(p.relative_to(ROOT)): digest(p) for p in sources}
        print('Direct inputs verified; reading reviewed joins.', flush=True)
        # Large decoded JSON objects have no Python reference cycles.
        gc.disable()
        base = read(paths['base']); base_summary = read(paths['base_summary'])
        selected = ('effects', 'effect_schedule', 'compile_calls', 'load_calls', 'effect_values', 'materialized', 'fasl_reads')
        streams = {}
        for name in ('build', 'cold'):
            data = read(paths[name]); streams[name] = {k: data[k] for k in selected}; del data
        streams['cold']['startup_calls'] = cold_calls(paths['cold_events'])
        pin_bytes = json.dumps(pins, sort_keys=True).encode()
        identities = {'inputs': hashlib.sha256(pin_bytes).hexdigest(), 'instrumentation': pins['instrumentation_sha256']}
        print('Joining initializer boundaries, exact callees and returned values.', flush=True)
        graph, witnesses = extend(base, streams, identities)
        check(base, graph, witnesses, streams)
        print('Integration coverage PASS; running specific omission controls.', flush=True)
        checks = controls(base, graph, witnesses, streams)
        contract = load_tool('identity_census_contract', ROOT / 'doc/WASM/tools/check-census.py')
        errors = contract.validate(graph)
        prefixes = ('unresolved reachable edge from ', 'unimplemented reachable node ')
        unexpected = [e for e in errors if not e.startswith(prefixes)]
        if unexpected: raise ValueError('graph invariant: ' + '; '.join(unexpected[:3]))
        grouped = {p.strip(): sum(e.startswith(p) for e in errors) for p in prefixes}
        expected_errors = dict(base_summary['census_error_counts'])
        expected_errors['unimplemented reachable node'] += 3  # Explicit build/cold closure and boot-process obligations.
        if grouped != expected_errors: raise ValueError(('unexpected change to unresolved obligations', grouped, expected_errors))
        summary = {'version': 1, 'status': 'IDENTITIES_INTEGRATED_UNQUALIFIED', 'integration_coverage': 'PASS',
                   'schema_and_graph_invariants': 'PASS', 'census_contract': 'BLOCKED', 'review_disposition': 'NOT_REVIEWED',
                   'original_nodes_preserved': len(base['nodes']), 'original_edges_preserved': len(base['edges']),
                   'new_nodes': len(graph['nodes']) - len(base['nodes']), 'new_edges': len(graph['edges']) - len(base['edges']),
                   'build_boundaries': len(streams['build']['effect_schedule']), 'cold_boundaries': len(streams['cold']['effect_schedule']),
                   'compile_callees_joined': len(streams['build']['compile_calls']), 'loader_callees_joined': len(streams['build']['load_calls']),
                   'callback_callees_joined': len(streams['cold']['startup_calls']),
                   'reader_effects': dict(Counter(e.get('reader_mode') for e in streams['build']['effects'] if e['family'] == 'fasl-effect')),
                   'controls_rejected': len(checks['controls']), 'census_error_counts': grouped,
                   'stage0_gate': {'accepted': 28, 'missing': 21, 'unreviewed': 0, 'basis': 'Existing acceptance record; not re-executed.'},
                   'scope': 'Actual execution identities and conservative phase boundaries joined into the existing exchange schema. Older captures remain distinct and unchanged; no historical initializer is promoted based on a different run.',
                   'remaining': ['Bootstrap subprocess installation witness.', 'Full target source traversal and static callees, including bounds on the retained 1,729 dynamic sites.', 'Review the thirteen seeds and classify lowering, imports and stores for the target.', 'Reconcile/supersede provisional obligations only with corresponding scenario and source witnesses, then run the complete passing census and its omission mutants.']}
        for name, data in [('census.json.gz', graph), ('joins.json.gz', witnesses), ('summary.json', summary), ('controls.json', checks)]:
            save(output / name, data)
        report.update(status=summary['status'], elapsed_seconds=round(time.monotonic() - start, 3),
                      artifacts=[{'path': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in sorted(output.iterdir()) if p.name != 'run.json'])
        return summary
    except BaseException as exc:
        report['error'] = type(exc).__name__ + ': ' + str(exc); raise
    finally:
        gc.enable(); save(output / 'run.json', report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.evidence_root.resolve(), args.output.resolve()), indent=2))
