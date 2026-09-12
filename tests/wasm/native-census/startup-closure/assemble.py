#!/usr/bin/env python3
"""Assemble one unqualified census exchange packet using pinned retained inputs."""
import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

import candidates as candidate_tools
import check_exchange
import effects
import exchange
import opcodes

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode()


def save(path, value):
    data = encoded(value)
    path.write_bytes(gzip.compress(data, mtime=0) if path.suffix == '.gz' else data)


def load_tool(name, path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def inputs(evidence):
    pins = json.loads((HERE / 'exchange-inputs.json').read_text())
    values, paths = {}, {}
    for name, pin in pins['inputs'].items():
        path = (evidence if pin['repository'] == 'evidence' else ROOT) / pin['path']
        if digest(path) != pin['sha256']:
            raise ValueError('pinned input changed: ' + name)
        paths[name] = path
        if path.suffix == '.json':
            values[name] = json.loads(path.read_text())
    candidate_tools.check_coverage(values['candidates'], values['image'], values['observed'], values['seeds'])
    if values['observed']['source_log_sha256'] != pins['inputs']['rebuild']['sha256']:
        raise ValueError('observed graph and rebuild stream differ')
    accepted = values['stub_acceptance']['results']
    if len(accepted) != 1 or accepted[0]['id'] != 'S0-LL08-a' or accepted[0]['review_disposition'] != 'ACCEPTED':
        raise ValueError('requires the pinned LL08-a project acceptance')
    if not any(a['sha256'] == pins['inputs']['stub']['sha256'] for a in accepted[0]['artifacts']):
        raise ValueError('target session is not an accepted LL08-a artifact')
    return pins, values, paths


def make(evidence, output):
    if output.exists():
        raise ValueError('output must be new; retained evidence is never overwritten')
    output.mkdir(parents=True)
    record = {'version': 1, 'status': 'RUNNING', 'operation': 'RETAINED_INPUT_ANALYSIS_NO_NATIVE_EXECUTION',
              'command': [sys.executable, str(Path(__file__).resolve()), '--evidence-root', str(evidence), '--output', str(output)],
              'verification_scope': 'New analysis and direct input bytes only; no native rebuild, acceptance aggregate or archive scan.'}
    save(output / 'run.json', record)
    started = time.monotonic()
    try:
        pins, values, paths = inputs(evidence)
        record['pinned_inputs'] = pins
        sources = ['assemble.py', 'exchange.py', 'effects.py', 'opcodes.py', 'check_exchange.py',
                   'test_exchange.py', 'exchange-inputs.json', 'candidates.py', 'seeds.json']
        source_paths = [HERE / name for name in sources]
        source_paths += [ROOT / 'doc/WASM/tools/check-census.py', ROOT / 'doc/WASM/contracts/census.schema.json',
                         ROOT / 'doc/WASM/stage0/baseline.json', ROOT / 'doc/WASM/stage0/inventory.json',
                         HERE.parent / 'reconcile-trace.py']
        record['source_sha256'] = {str(p.relative_to(ROOT)): digest(p) for p in source_paths}
        print('Pinned direct inputs verified; assembling effect and lowering joins.', flush=True)
        e = effects.collect(paths['rebuild'], paths['cold'], values['image'])
        lower = opcodes.collect(values['image'])
        raw = check_exchange.witnesses(paths['rebuild'], paths['cold'])
        identities = {'inputs': hashlib.sha256(encoded(pins)).hexdigest(),
                      'instrumentation': hashlib.sha256(encoded(pins['instrumentation'])).hexdigest(),
                      'trace': pins['inputs']['trace']['sha256']}
        graph, joins = exchange.build(values['image'], values['observed'], values['candidates'], values['seeds'],
                                      e, lower, values['stub'], identities)
        parser = load_tool('census_trace', HERE.parent / 'reconcile-trace.py')
        # Reconcile the pinned trace bytes; reuse prior runtime/baseline identity
        # verification. Do not reopen every historic execution artifact.
        trace = parser.reconcile_events(paths['trace'].parent, values['trace'], paths['trace_log'].read_text())
        if trace['unresolved_path_contexts']:
            raise ValueError('unresolved trace pathname context')
        joins['trace'] = {k: trace[k] for k in ['scope', 'checks', 'classification_counts',
                                               'lisp_file_operations', 'dyld_directory_contexts']}
        checker_args = (values['image'], values['observed'], values['candidates'], values['seeds'], raw, lower, values['stub'])
        coverage = check_exchange.check(graph, joins, *checker_args)
        print('Projection coverage PASS; checking census contract and omission controls.', flush=True)
        census = load_tool('census_contract', ROOT / 'doc/WASM/tools/check-census.py')
        schema = json.loads((ROOT / 'doc/WASM/contracts/census.schema.json').read_text())
        shape_errors = census.shape(graph, schema, schema['$defs'])
        if shape_errors:
            raise ValueError('exchange schema failure: ' + '; '.join(shape_errors[:3]))
        errors = census.validate(graph)
        allowed_errors = ('unresolved reachable edge from ', 'unimplemented reachable node ')
        unexpected = [error for error in errors if not error.startswith(allowed_errors)]
        if unexpected:
            raise ValueError('unexpected census graph defect: ' + '; '.join(unexpected[:3]))
        if not errors:
            raise ValueError('unqualified observations were incorrectly promoted to a closed census')
        from test_exchange import run as test
        checks = test(graph, joins, checker_args)
        nodes = Counter(n['kind'] for n in graph['nodes'])
        summary = {'version': 1, 'status': 'ASSEMBLED_UNQUALIFIED', 'projection_coverage': coverage['status'],
                   'schema': 'PASS', 'census_contract': 'BLOCKED', 'LL15_b': 'NOT_QUALIFIED', 'LL15_c': 'NOT_QUALIFIED',
                   'nodes': len(graph['nodes']), 'nodes_by_kind': dict(sorted(nodes.items())), 'edges': len(graph['edges']),
                   'reachable_nodes': len(exchange.fixed_point(graph)), 'phases': sorted({e['phase'] for e in graph['edges']}),
                   'compile_effects_returned': len(e['compile']), 'compile_previews_changed': sum(r['preview'] != r['return_preview'] for r in e['compile']),
                   'load_effects_emitted_not_executed': len(e['load']), 'startup_callbacks_returned': len(e['startup']),
                   'dynamic_calls_unqualified': len(values['candidates']['dynamic_calls']),
                   'missing_named_candidates': len(joins['missing_named_candidates']), 'evaluated_templates_decoded': len(lower),
                   'projection_controls_rejected': len(checks['controls']),
                   'census_error_counts': {prefix.strip(): sum(s.startswith(prefix) for s in errors) for prefix in allowed_errors},
                   'qualification_work': [
                       'Review the 13 proposed seeds and prove an installation-aware conservative call bound.',
                       'Capture full source reachability under Wasm target state; LL08-a covers fourteen fixture forms.',
                       'Join identity-bearing read/macroexpand effects and semantic compile/load prerequisites/completions.',
                       'Join operator emission, subprimitive cycles, foreign/import targets and pointer-store classes; assign Wasm dispositions.',
                       'Reconcile the r5 traced heap with the r7 inspected/captured heap without conflating their identities.',
                       'Qualify LL15-c on a complete passing census; these controls test an intentionally blocked projection.'],
                   'stage0_gate': {'accepted': 28, 'missing': 21, 'unreviewed': 0,
                                   'basis': 'Reuse accepted 02ff713d gate; no new gate credit or aggregate regeneration.'}}
        for name, value in [('census.json.gz', graph), ('joins.json.gz', joins),
                            ('summary.json', summary), ('controls.json', checks)]:
            save(output / name, value)
        record.update(status='ASSEMBLED_UNQUALIFIED', elapsed_seconds=round(time.monotonic() - started, 3),
                      artifacts=[{'path': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)}
                                 for p in sorted(output.iterdir()) if p.name != 'run.json'])
        return summary
    except BaseException as exc:
        record.update(status='FAIL', error=str(exc))
        raise
    finally:
        save(output / 'run.json', record)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(make(args.evidence_root.resolve(), args.output.resolve()), indent=2))
