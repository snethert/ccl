#!/usr/bin/env python3
"""Traverse the first U1 source module using the accepted census registration."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
from check import SOURCE_SHA256, check_capture, project, check_projection
from test_controls import run as controls

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def digest(p):
    with p.open('rb') as s:
        return hashlib.file_digest(s, 'sha256').hexdigest()


def save(p, obj):
    data = (json.dumps(obj, indent=2, ensure_ascii=False) + '\n').encode()
    p.write_bytes(gzip.compress(data, mtime=0) if p.suffix == '.gz' else data)


def run(store, work, output):
    if platform.system() != 'Darwin' or platform.machine() != 'x86_64':
        raise ValueError('requires macOS x86-64 reference host')
    for a, b in [(store, work), (store, output), (work, output)]:
        if a == b or a in b.parents or b in a.parents:
            raise ValueError('separate evidence/work/output directories required')
    work.mkdir(parents=True, exist_ok=False); output.mkdir(parents=True, exist_ok=False)
    record = {'version': 1, 'status': 'FAIL', 'review_disposition': 'NOT_REVIEWED',
              'command': sys.argv, 'commands': [], 'time': datetime.now(timezone.utc).isoformat(),
              'scope': 'First-module traversal and partial source facts, with explicit target gaps. No shared-source edits or native rebuild.'}
    try:
        pins = json.loads((HERE/'inputs.json').read_text()); record['pins'] = pins
        paths = {k: store/p['path'] for k, p in pins['inputs'].items()}
        for k, p in paths.items():
            if digest(p) != pins['inputs'][k]['sha256']:
                raise ValueError('direct input changed: ' + k)
        sources = [HERE/n for n in ('driver.lisp', 'run.py', 'check.py', 'test_controls.py', 'inputs.json')]
        sources += [HERE.parent/'observer.lisp', HERE.parent/'dependencies.lisp']
        sources += [ROOT/p for p in ('lib/dumplisp.lisp', 'lib/nfcomp.lisp', 'lib/macros.lisp')]
        record['source_sha256'] = {str(p.relative_to(ROOT)): digest(p) for p in sources}
        source = work/'ccl'; source.mkdir()
        for key in ('source', 'bootstrap'):
            with tarfile.open(paths[key]) as archive:
                archive.extractall(source, filter='data')
        shutil.copyfile(paths['kernel'], source/'dx86cl64'); (source/'dx86cl64').chmod(0o755)
        (source/'bin').mkdir(exist_ok=True)
        for key in ('architecture', 'backend'):
            shutil.copyfile(paths[key], source/'bin'/paths[key].name)
        target_source = source/'lib/dumplisp.lisp'
        if digest(target_source) != SOURCE_SHA256:
            raise ValueError('first-module source differs from pinned U1')
        pristine = {p: digest(source/p) for p in ('lib/dumplisp.lisp', 'lib/systems.lisp')}
        binaries = {str(p.relative_to(source)): digest(p) for p in source.rglob('*.dx64fsl')}
        results = []
        for mode in ('normal', 'repeat', 'stop-after-first-capture', 'host-reader'):
            capture_path = work/(mode+'.json')
            env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin', 'LANG': 'C', 'LC_ALL': 'C',
                   'CCL_DEFAULT_DIRECTORY': str(source), 'CCL_TRAVERSE_SOURCE': str(target_source),
                   'CCL_TRAVERSE_OUTPUT': str(capture_path),
                   'CCL_TRAVERSE_MODE': 'normal' if mode == 'repeat' else mode}
            argv = [str(source/'dx86cl64'), '--image-name', str(paths['image']), '--no-init', '--batch']
            for p in [HERE.parent/'observer.lisp', HERE.parent/'dependencies.lisp', paths['registration']]:
                argv += ['--load', str(p)]
            argv += ['--eval', '(dolist (name (quote (ccl::wasm-census-arch ccl::wasm-census-backend))) '
                     '(multiple-value-bind (binary sources) (ccl::find-module name (ccl::backend-name ccl::*host-backend*)) '
                     '(declare (ignore sources)) (load binary)))', '--load', str(HERE/'driver.lisp'),
                     '--eval', '(progn (ccl-source-traversal::run) (ccl:quit))']
            command = {'mode': mode, 'argv': argv, 'cwd': str(source), 'environment': env, 'timeout_seconds': 60}
            record['commands'].append(command)
            try:
                with (output/(mode+'.log')).open('wb') as log:
                    child = subprocess.Popen(argv, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                    try:
                        code = child.wait(timeout=60)
                    except BaseException:
                        try: os.killpg(child.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                        child.wait(); raise
                command['exit_code'] = code
                if code or not capture_path.exists():
                    raise ValueError('native capture failed: ' + mode)
                # Retain raw native output before any analysis failure.
                raw = capture_path.read_bytes()
                (output/(mode+'.json.gz')).write_bytes(gzip.compress(raw, mtime=0))
                command['capture_sha256'] = hashlib.sha256(raw).hexdigest()
                c = json.loads(raw)
                if mode in ('normal', 'repeat'):
                    counts = check_capture(c, target_source.read_bytes())
                    if mode == 'normal': capture, original_raw = c, raw
                    elif raw != original_raw: raise ValueError('fresh native capture bytes differ')
                    results.append({'mode': mode, 'status': 'PASS', 'counts': counts})
                else:
                    try: check_capture(c, target_source.read_bytes())
                    except ValueError as e:
                        expected = 'FORM_COVERAGE' if mode == 'stop-after-first-capture' else 'TARGET_CONTEXT'
                        if str(e) != expected: raise ValueError('unexpected native control rejection: ' + str(e))
                        results.append({'mode': mode, 'status': 'REJECTED', 'reason': str(e)})
                    else: raise ValueError('native control escaped: ' + mode)
            finally:
                save(output/'commands.json', record['commands'])
        facts = project(capture); check_projection(facts, capture)
        tests = controls(capture, facts, target_source.read_bytes()); save(output/'controls.json', tests)
        save(output/'facts.json.gz', facts)
        if pristine != {p: digest(source/p) for p in pristine}:
            raise ValueError('pristine source changed')
        after = {str(p.relative_to(source)): digest(p) for p in source.rglob('*.dx64fsl')}
        if binaries != after or list(source.rglob('*.census-no-code')):
            raise ValueError('traversal wrote a FASL')
        summary = {'version': 1, 'status': 'TRAVERSED_WITH_EXPLICIT_GAPS', 'review_disposition': 'NOT_REVIEWED',
                   **counts, 'analysis_controls_rejected': tests['controls_rejected'], 'native_controls_rejected': 2,
                   'native_reproduction_equal': True, 'source_unchanged': True, 'fasls_unchanged': True,
                   'sessions': results, 'macro_environment_qualified': False, 'graph_edges_replaced': 0,
                   'census_acceptance': 'BLOCKED', 'stage0_gate': {'accepted': 28, 'missing': 20, 'unreviewed': 0,
                    'new_credit': 0, 'basis': 'Accepted aggregate unchanged; gate not rerun.'}}
        save(output/'summary.json', summary)
        # Successful duplicate transport is unnecessary: the original bytes and
        # recorded equality are retained. Native mutants remain separate.
        (output/'repeat.json.gz').unlink()
        record.update(status='PASS', artifacts=[{'path': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)}
                      for p in sorted(output.iterdir()) if p.name != 'run.json'])
        print(json.dumps(summary, indent=2))
    except BaseException as e:
        record['error'] = type(e).__name__ + ': ' + str(e)
        raise
    finally:
        save(output/'run.json', record)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('evidence-root', 'work', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); run(a.evidence_root.resolve(), a.work.resolve(), a.output.resolve())
