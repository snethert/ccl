#!/usr/bin/env python3
"""Reproduce the boot analysis and controls using its retained native image."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile
from analyze import analyze, bind_files, read
from test_controls import controls, file_controls

HERE = Path(__file__).resolve().parent


def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, data): p.write_text(json.dumps(data, indent=2) + '\n')


def verify(capture, baseline, kernel, output):
    output.mkdir(parents=True, exist_ok=False)
    report = {'version': 1, 'status': 'FAIL', 'review_disposition': 'NOT_REVIEWED', 'commands': [],
              'inputs': {str(p): digest(p) for p in [capture / n for n in ('events.jsonl.gz', 'joins.json.gz', 'files.json', 'run.json', 'dx86cl64.image.gz')] + [baseline, kernel]},
              'source_sha256': {str(p): digest(p) for p in [HERE / n for n in ('verify.py', 'analyze.py', 'test_controls.py', 'native-controls.lisp', 'export.lisp')] + [HERE.parent / 'observer.lisp']}}
    try:
        # Inputs are our explicitly supplied unit archive, not an arbitrary
        # extraction destination or the project checkout.
        source = output / 'ccl'; source.mkdir()
        with tarfile.open(baseline) as archive: archive.extractall(source, filter='data')
        overrides = {str(p.relative_to(capture / 'changed-fasls')): p for p in (capture / 'changed-fasls').rglob('*.dx64fsl')}
        rows = read(capture / 'events.jsonl.gz'); joined = analyze(rows)
        with gzip.open(capture / 'joins.json.gz', 'rt') as stream:
            if joined != json.load(stream): raise ValueError('analysis reproduction differs')
        capture_run = json.loads((capture / 'run.json').read_text())
        recorded_root = next(r['cwd'] for r in capture_run['commands'] if r['name'] == 'observed')
        files, outcomes = file_controls(rows, source, overrides, recorded_root)
        if files != json.loads((capture / 'files.json').read_text()): raise ValueError('file joins differ')
        outcomes = controls(rows) + outcomes
        save(output / 'controls.json', {'status': 'PASS', 'positive_cases': 2, 'controls_rejected': len(outcomes), 'outcomes': outcomes})
        image = output / 'observed.image'
        with gzip.open(capture / 'dx86cl64.image.gz', 'rb') as src, image.open('wb') as dst: shutil.copyfileobj(src, dst)
        executable = source / 'dx86cl64'
        shutil.copyfile(kernel, executable); executable.chmod(0o755)
        if digest(executable) != report['inputs'][str(kernel)]: raise ValueError('kernel copy differs')
        native = []
        for mode in ('active', 'foreign-owner', 'omit-cold-return', 'unaltered'):
            events = output / (mode + '.jsonl'); log = output / (mode + '.log')
            env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin', 'LANG': 'C', 'LC_ALL': 'C',
                   'CCL_DEFAULT_DIRECTORY': str(source), 'CCL_BOOT_CENSUS_OUTPUT': str(events), 'CCL_BOOT_CONTROL': mode}
            argv = [str(executable), '--image-name', str(image), '--no-init', '--batch', '--load', str(HERE.parent / 'observer.lisp'), '--load', str(HERE / 'export.lisp')]
            if mode != 'unaltered': argv += ['--load', str(HERE / 'native-controls.lisp')]
            argv += ['--eval', '(progn (cl-user::' + ('export-boot-census' if mode == 'unaltered' else 'boot-observation-control') + ') (ccl:quit))']
            with log.open('wb') as stream:
                child = subprocess.Popen(argv, env=env, cwd=source, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                try: code = child.wait(timeout=60)
                except BaseException:
                    try: os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    child.wait(); raise
            report['commands'].append({'mode': mode, 'argv': argv, 'environment': env, 'cwd': str(source), 'exit_code': code, 'timeout_seconds': 60})
            text = log.read_text(errors='replace')
            if mode in ('active', 'foreign-owner'):
                if not (code and 'BOOT-CONTROL-MUTATED ' + mode in text and 'assertion' in text.lower() and not events.exists()):
                    raise ValueError('native refusal did not reach the exporter guard: ' + mode)
                native.append({'name': mode, 'status': 'REJECTED', 'oracle': 'exporter state assertion'})
            else:
                if code or 'BOOT-CENSUS-EXPORTED' not in text: raise ValueError('native export failed: ' + mode)
                if mode == 'unaltered':
                    if events.read_bytes() != gzip.decompress((capture / 'events.jsonl.gz').read_bytes()):
                        raise ValueError('fresh export differs from retained capture')
                    native.append({'name': mode, 'status': 'PASS', 'oracle': 'byte-identical fresh export'})
                else:
                    try: analyze(read(events))
                    except ValueError as exc:
                        if str(exc) != 'COLD_QUEUE_ORDER': raise
                        native.append({'name': mode, 'status': 'REJECTED', 'oracle': str(exc)})
                    else: raise ValueError('native omission escaped')
                with events.open('rb') as src, gzip.open(output / (mode + '.jsonl.gz'), 'wb') as dst: shutil.copyfileobj(src, dst)
                events.unlink()
        save(output / 'native-controls.json', {'status': 'PASS', 'positive_cases': 1, 'controls_rejected': 3, 'outcomes': native})
        report.update(status='PASS', analysis_identical=True, file_joins_identical=True,
                      controls_rejected=len(outcomes), native_controls_rejected=3, fresh_export_identical=True)
    except BaseException as exc: report['error'] = type(exc).__name__ + ': ' + str(exc)
    finally: save(output / 'run.json', report)
    print(json.dumps({k: v for k, v in report.items() if k not in ('inputs', 'source_sha256', 'commands')}))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('capture', 'baseline', 'kernel', 'output'): p.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args(); raise SystemExit(verify(*(getattr(a, n).resolve() for n in ('capture', 'baseline', 'kernel', 'output'))))
