#!/usr/bin/env python3
"""Replay the four existing passes from one source tree; retain each invocation.

This does not add a resolver or publish acceptance. --stage permits a long run
to be executed in separate commands, each with fresh outputs and source pins.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STAGES = ('finite', 'lexical', 'lookup-native', 'lookups', 'constructor-inputs', 'constructor-native', 'constructor')


def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def inputs(a):
    """Re-derive only CONSTANTLY's required body witness from retained streams."""
    sys.path.insert(0, str(a.source_root / 'tests/wasm/native-census/registry-callees'))
    from payloads import capture, before_functions, correspondences, prefix_check, read, save as store, require
    root = a.evidence; out = a.output / 'constructor-inputs'; out.mkdir()
    correlated = root / '2026-09-15-correlated-query-base-r1/capture'
    prefix_check(correlated / 'build.jsonl.gz', root / '2026-09-14-resident-bodies-r1/first-prefix.jsonl.gz')
    definitions = [f for f in read(root / '2026-09-14-build-flow-r1/functions.json.gz') if f['name'] == 'COMMON-LISP::CONSTANTLY']
    require(len(definitions) == 1, 'CONSTRUCTOR_DEFINITION_POPULATION')
    def event(path, sequence):
        with gzip.open(path, 'rt') as stream:
            for i, line in enumerate(stream, 1):
                if i == sequence:
                    row = json.loads(line); require(row['sequence'] == sequence, 'CONSTRUCTOR_EVENT_SEQUENCE'); return row
        raise ValueError('CONSTRUCTOR_EVENT_MISSING')
    original = event(root / '2026-09-12-rich-census-r1/observed-r4.jsonl.gz', definitions[0]['event'])
    require(original['payload']['function']['function_id'] == definitions[0]['function_id'], 'CONSTRUCTOR_DEFINITION_ID')
    histories = [h for h in read(root / '2026-09-14-binding-versions-r1/histories.json.gz')
                 if any(d.get('name') == 'CONSTANTLY' and d.get('package') == 'COMMON-LISP' for d in h['descriptors'])]
    require(len(histories) == 1 and not histories[0]['macro_expander_codes'], 'CONSTRUCTOR_HISTORY')
    codes = set(histories[0]['ordinary_codes'])
    anchored = read(root / '2026-09-14-resident-bodies-r1/bodies.json.gz')
    requested = {'bodies': [b for b in anchored['bodies'] if b['code'] in codes]}
    require({b['code'] for b in requested['bodies']} == codes and codes, 'CONSTRUCTOR_ANCHORED_POPULATION')
    functions, emissions, _, wrappers, _ = capture(correlated / 'registries.jsonl.gz')
    before = before_functions(correlated / 'build.jsonl.gz', emissions)
    matches, missing = correspondences(functions, emissions, wrappers, requested, before)
    require(not missing and {m['bootstrap_code'] for m in matches} == codes, 'CONSTRUCTOR_BODY_MATCH')
    events = {r['before']['event'] for m in matches for r in m['compiler_records']}
    require(len(events) == 1, 'CONSTRUCTOR_COMPILER_EVENT_POPULATION')
    fresh = event(correlated / 'build.jsonl.gz', events.pop())
    store(out / 'provider-ir.json', original); store(out / 'correlated-ir.json', fresh)
    store(out / 'body-correspondences.json.gz', dict(matches=matches, support_matches=[]))
    store(out / 'summary.json', dict(status='PASS', requested_codes=sorted(codes), matched=len(matches),
          scope='Only the constructor provider required by this chain; no all-resident-body closure claim.'))


def invocation(a, stage):
    code = a.source_root / 'tests/wasm/native-census/finite-callees'; out = a.output
    ev = ['--evidence', str(a.evidence)]
    python = sys.executable
    if stage == 'finite':
        return [python, str(code / 'run.py'), '--output', str(out / stage), '--base', str(a.base),
                '--base-sha', '27cd554e4dce6160849ca390748f8e538c729f7ff06c83e418f2350fea5039b1', *ev]
    if stage == 'lexical':
        return [python, str(code / 'lexical_run.py'), 'run', '--output', str(out / stage), '--previous', str(out / 'finite'), *ev]
    if stage == 'lookup-native':
        census = code.parent
        argv = [str(out / 'finite/native/dx86cl64'), '--image-name', str(a.evidence / '2026-09-12-native-census-r7/baseline/build/dx86cl64.image'), '--no-init', '--batch']
        for name in ('observer.lisp', 'dependencies.lisp', 'rich-observation/observer.lisp',
                     'finite-callees/probes.lisp', 'finite-callees/lexical-probes.lisp', 'finite-callees/lookup-probes.lisp'):
            argv += ['--load', str(census / name)]
        return argv + ['--eval', '(progn (census-finite-probes::run) (ccl:quit))']
    if stage == 'lookups':
        return [python, str(code / 'lookup_run.py'), '--native', str(out / 'lookup-native/native.json'), '--finite', str(out / 'finite'),
                '--lexical', str(out / 'lexical'), '--base', str(out / 'lexical/census.json.gz'), '--output', str(out / stage), *ev]
    if stage == 'constructor-native':
        return [python, str(code / 'constructor_native.py'), '--source', str(out / 'finite/native'),
                '--image', str(a.evidence / '2026-09-12-native-census-r7/baseline/build/dx86cl64.image'), '--output', str(out / stage)]
    if stage == 'constructor':
        return [python, str(code / 'constructor_run.py'), '--native', str(out / 'constructor-native'),
                '--provider-ir', str(out / 'constructor-inputs/provider-ir.json'), '--correlated-ir', str(out / 'constructor-inputs/correlated-ir.json'),
                '--bodies', str(out / 'constructor-inputs'), '--finite', str(out / 'finite'), '--lookups', str(out / 'lookups'),
                '--base', str(out / 'lookups/census.json.gz'), '--output', str(out / stage), *ev]
    return None


def dependencies(a, stage):
    """Direct input files only; never scan the historical evidence repository."""
    ev = a.evidence; out = a.output
    names = ['2026-09-14-build-flow-r1/calls.json.gz', '2026-09-14-build-flow-r1/functions.json.gz',
             '2026-09-14-build-flow-r1/samples.json.gz', '2026-09-14-binding-versions-r1/histories.json.gz']
    if stage in ('finite', 'constructor-inputs'): names += ['2026-09-12-rich-census-r1/observed-r4.jsonl.gz']
    if stage == 'constructor-inputs':
        names += ['2026-09-15-correlated-query-base-r1/capture/build.jsonl.gz',
                  '2026-09-15-correlated-query-base-r1/capture/registries.jsonl.gz',
                  '2026-09-14-resident-bodies-r1/first-prefix.jsonl.gz', '2026-09-14-resident-bodies-r1/bodies.json.gz']
    if stage in ('finite', 'lexical', 'lookup-native', 'constructor-native'):
        spec = json.loads((a.source_root / 'tests/wasm/native-census/source-traversal/inputs.json').read_text())['inputs']
        for key in ('source', 'kernel', 'image'):
            path = ev / spec[key]['path']
            if sha(path) != spec[key]['sha256']: raise ValueError('native input identity: ' + key)
            names.append(spec[key]['path'])
    paths = {ev / name for name in names} | {a.base}
    for earlier in STAGES[:STAGES.index(stage)]:
        directory = out / earlier
        if directory.exists():
            paths |= {p for p in directory.iterdir() if p.is_file() and (p.name.endswith('.json') or p.name.endswith('.json.gz') or p.name.endswith('.jsonl.gz'))}
    return {str(p): sha(p) for p in sorted(paths)}


def run(a):
    a.output.mkdir(parents=True, exist_ok=True)
    # Inputs are hashed once per invocation, not against the whole catalog.
    paths = [a.base, a.evidence / '2026-09-15-correlated-query-base-r1/packet.json']
    source = a.source_root / 'tests/wasm/native-census'
    selected = set(source.rglob('*.py')) | set(source.rglob('*.lisp')) | set(source.rglob('*.json'))
    selected |= {a.source_root / 'doc/WASM/tools/check-census.py'}
    pins = {str(p.relative_to(a.source_root)): sha(p) for p in sorted(selected)}
    for earlier in a.output.glob('*-execution.json'):
        prior = json.loads(earlier.read_text())
        if prior.get('source_sha256') != pins:
            raise ValueError('analysis sources differ from an earlier stage: ' + earlier.name)
    for stage in STAGES if a.stage == 'all' else [a.stage]:
        if (a.output / stage).exists(): raise ValueError('preserve existing stage output: ' + stage)
        record = dict(version=1, stage=stage, status='RUNNING', source_root=str(a.source_root),
                      source_sha256=pins, driver_sha256=sha(Path(__file__)),
                      inputs={**{str(p): sha(p) for p in paths}, **dependencies(a, stage)}, argv=invocation(a, stage))
        record_path = a.output / (stage + '-execution.json'); save(record_path, record)
        snapshot = a.output / (stage + '-sources')
        snapshot.mkdir()
        shutil.copyfile(Path(__file__), snapshot / 'reproduce.py')
        for name in ('finite.py', 'integrate.py', 'lexical.py', 'lookups.py', 'constructors.py'):
            shutil.copyfile(source / 'finite-callees' / name, snapshot / name)
        try:
            if stage == 'constructor-inputs': inputs(a)
            else:
                env = dict(os.environ)
                if stage == 'lookup-native':
                    (a.output / stage).mkdir()
                    env.update(CCL_DEFAULT_DIRECTORY=str(a.output / 'finite/native'), FINITE_OUTPUT=str(a.output / stage / 'native.json'))
                with (a.output / (stage + '.log')).open('wb') as log:
                    p = subprocess.run(record['argv'], cwd=a.source_root, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
                record['exit_code'] = p.returncode
                if p.returncode: raise ValueError(stage + ' failed; see its log')
            if any(sha(a.source_root / name) != h for name, h in pins.items()): raise ValueError('source changed during stage')
            record['status'] = 'PASS'
            record['outputs'] = {str(p.relative_to(a.output / stage)): sha(p) for p in sorted((a.output / stage).iterdir()) if p.is_file()}
            print(stage, 'PASS', flush=True)
        except BaseException:
            record['status'] = 'FAIL'; record['failure'] = traceback.format_exc(); raise
        finally: save(record_path, record)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, default=ROOT)
    p.add_argument('--evidence', type=Path, default=ROOT.parent / 'ccl-evidence')
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--stage', choices=('all', *STAGES), default='all')
    a = p.parse_args()
    for name in ('source_root', 'evidence', 'base', 'output'): setattr(a, name, getattr(a, name).resolve())
    run(a)
