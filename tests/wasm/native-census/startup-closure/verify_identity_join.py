#!/usr/bin/env python3
"""Recheck the retained graph and reproduce the former insertion escapes."""
import argparse
import ast
import gc
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from join_identities import HERE, ROOT, cold_calls, digest, read, save
from test_identity_join import run as controls

PREVIOUS = 'f3b4b07e'
METADATA_PREVIOUS = 'c421e39a'


def run(evidence, output):
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = {'version': 1, 'status': 'FAIL', 'review_disposition': 'NOT_REVIEWED',
              'command': sys.argv, 'previous_revision': PREVIOUS,
              'scope': 'New checker and controls applied to the retained graph. Former checker escapes reproduced from its committed source. No graph regeneration, native execution, archive audit or acceptance change.'}
    try:
        pins = json.loads((HERE / 'identity-inputs.json').read_text())
        extra = json.loads((HERE / 'identity-verification-inputs.json').read_text())
        inputs = {**pins['inputs'], **extra['inputs']}
        paths = {name: evidence / pin['path'] for name, pin in inputs.items()}
        for name, path in paths.items():
            if digest(path) != inputs[name]['sha256']: raise ValueError('changed direct input: ' + name)
        report['input_pins'] = inputs
        original = read(paths['original_run'])
        source_path = HERE / 'identity_join.py'
        relative = str(source_path.relative_to(ROOT))
        old_source = subprocess.check_output(['git', 'show', PREVIOUS + ':' + relative], cwd=ROOT)
        old_hash = hashlib.sha256(old_source).hexdigest()
        if old_hash != original['source_sha256'][relative]: raise ValueError('former checker does not match the retained run')
        report['previous_checker_sha256'] = old_hash
        changed = {relative, str((HERE / 'test_identity_join.py').relative_to(ROOT))}
        current = {name: digest(ROOT / name) for name in original['source_sha256']}
        for name, expected in original['source_sha256'].items():
            if name not in changed and current[name] != expected: raise ValueError('changed producer dependency: ' + name)
        # The producer and its helpers are unchanged; only checker code is new.
        def producer(source):
            tree = ast.parse(source)
            tree.body = [n for n in tree.body if not (isinstance(n, ast.FunctionDef) and n.name in ('check', 'expected_additions'))]
            return ast.dump(tree, include_attributes=False)
        if producer(old_source) != producer(source_path.read_bytes()): raise ValueError('producer changed; regenerate the graph')
        report['producer_ast_unchanged'] = True
        for path in (Path(__file__).resolve(), HERE / 'identity-verification-inputs.json'):
            current[str(path.relative_to(ROOT))] = digest(path)
        report['source_sha256'] = current
        previous = {'__name__': 'previous_identity_join', '__file__': PREVIOUS + ':' + relative}
        exec(compile(old_source, previous['__file__'], 'exec'), previous)
        metadata_source = subprocess.check_output(['git', 'show', METADATA_PREVIOUS + ':' + relative], cwd=ROOT)
        report['metadata_previous_revision'] = METADATA_PREVIOUS
        report['metadata_previous_checker_sha256'] = hashlib.sha256(metadata_source).hexdigest()
        metadata_previous = {'__name__': 'metadata_previous_identity_join', '__file__': METADATA_PREVIOUS + ':' + relative}
        exec(compile(metadata_source, metadata_previous['__file__'], 'exec'), metadata_previous)
        print('Direct inputs and unchanged producer verified; reading retained graph.', flush=True)
        gc.disable()
        base = read(paths['base']); graph = read(paths['extended']); witnesses = read(paths['witnesses'])
        selected = ('effects', 'effect_schedule', 'compile_calls', 'load_calls', 'effect_values', 'materialized', 'fasl_reads')
        streams = {}
        for name in ('build', 'cold'):
            data = read(paths[name]); streams[name] = {k: data[k] for k in selected}; del data
        streams['cold']['startup_calls'] = cold_calls(paths['cold_events'])
        print('Checking exact graph bounds and former insertion escapes.', flush=True)
        result = controls(base, graph, witnesses, streams, previous_checker=previous['check'],
                          metadata_checker=metadata_previous['check'])
        regressions = [r for r in result['controls'] if r.get('previous_checker') == 'ESCAPED']
        if len(regressions) != 5: raise ValueError('missing former-checker regression')
        metadata_regressions = [r for r in result['controls'] if r.get('metadata_checker') == 'ESCAPED']
        if len(metadata_regressions) != 6: raise ValueError('missing metadata-checker regression')
        save(output / 'controls.json', result)
        report.update(status='PASS', controls_rejected=len(result['controls']), previous_escapes_reproduced=len(regressions),
                      metadata_escapes_reproduced=len(metadata_regressions),
                      retained_graph_unchanged=True, elapsed_seconds=round(time.monotonic() - started, 3),
                      artifacts=[{'path': 'controls.json', 'sha256': digest(output / 'controls.json'),
                                  'bytes': (output / 'controls.json').stat().st_size}])
        return {k: report[k] for k in ('status', 'controls_rejected', 'previous_escapes_reproduced', 'metadata_escapes_reproduced', 'retained_graph_unchanged')}
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
