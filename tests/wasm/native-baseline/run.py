#!/usr/bin/env python3
"""Build and test unchanged U1 on macOS twice from one pinned bootstrap.

Run with --inputs, --work and --output absolute directories. Inputs contain
source.tar, tests.tar, bootstrap.tar.gz and pins.json. No network is used.
Work/output must be empty; the second rebuild restores the bootstrap image.
"""
import argparse
import platform
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

parser = argparse.ArgumentParser(description=__doc__)
for name in ('inputs', 'work', 'output'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
INPUTS, WORK, OUT = (p.resolve() for p in (args.inputs, args.work, args.output))
RUNNER = Path(__file__).resolve().parent
if platform.system() != 'Darwin' or platform.machine() != 'x86_64':
    parser.error('the U1 native reference is macOS x86-64')
if WORK == OUT or WORK in OUT.parents or OUT in WORK.parents:
    parser.error('work and output must be separate directories')
for directory in (WORK, OUT):
    directory.mkdir(parents=True, exist_ok=True)
SOURCE = WORK / 'ccl'
COMMANDS = []


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def command(name, argv, cwd=WORK, extra_env=None, timeout=1800, marker=None):
    record = {'name': name, 'argv': argv, 'cwd': str(cwd),
              'environment': {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin', 'HOME': str(WORK), 'LANG': 'C', 'LC_ALL': 'C', **(extra_env or {})}, 'timeout_seconds': timeout,
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    log = OUT / (name + '.log')
    started = time.monotonic()
    print('Running ' + name, flush=True)
    try:
        with log.open('wb') as output:
            proc = subprocess.run(argv, cwd=str(cwd), env={'PATH': '/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin',
                                       'HOME': str(WORK), 'LANG': 'C', 'LC_ALL': 'C',
                                       **(extra_env or {})},
                                  stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
        record['returncode'] = proc.returncode
        if proc.returncode != 0:
            raise RuntimeError('%s exited %s; see %s' % (name, proc.returncode, log.name))
        if marker and marker not in log.read_text(errors='replace'):
            raise RuntimeError('%s did not emit its completion marker' % name)
    except Exception as exc:
        record['error'] = str(exc)
        raise
    finally:
        record['seconds'] = time.monotonic() - started
        record['log_sha256'] = digest(log)
        COMMANDS.append(record)
        save(OUT / 'commands.json', COMMANDS)


def run():
    if any(WORK.iterdir()) or any(OUT.iterdir()):
        raise RuntimeError('/work and /output must be empty; old evidence is never overwritten')
    pins = json.loads((INPUTS / 'pins.json').read_text())
    for filename, expected in pins['inputs'].items():
        if digest(INPUTS / filename) != expected:
            raise RuntimeError('input hash mismatch: ' + filename)
    shutil.copy2(INPUTS / 'pins.json', OUT / 'pins.json')
    shutil.copytree(RUNNER, OUT / 'runner', ignore=shutil.ignore_patterns('__pycache__'))
    report = {'version': 1, 'evidence_kind': 'NATIVE BASELINE EXECUTION',
              'source_revision': pins['source_revision'], 'test_revision': pins['test_revision'],
              'review_disposition': 'NOT_REVIEWED', 'execution_status': 'FAIL',
              'gate0_status': 'NOT_ACCEPTED', 'runs': [], 'substitutions': [],
              'scope': 'Unchanged U1 macOS x86-64 kernel, clean Lisp rebuild, upstream tests and same-host raw repeatability.'}
    try:
        for name, argv in [('uname', ['/usr/bin/uname', '-a']),
                           ('macos', ['/usr/bin/sw_vers']),
                           ('hardware', ['/usr/sbin/sysctl', 'machdep.cpu.brand_string', 'hw.ncpu']),
                           ('compiler', ['/usr/bin/clang', '--version']),
                           ('sdk', ['/usr/bin/xcrun', '--show-sdk-version']),
                           ('linker', ['/usr/bin/xcrun', 'ld', '-v']),
                           ('make', ['/usr/bin/make', '--version']),
                           ('m4', ['gm4', '--version']), ('python', [sys.executable, '--version'])]:
            command(name, argv)
        SOURCE.mkdir()
        (WORK / 'ccl-tests').mkdir()
        command('extract-source', ['tar', '-xf', str(INPUTS / 'source.tar'), '-C', str(SOURCE)])
        command('extract-tests', ['tar', '-xf', str(INPUTS / 'tests.tar'), '-C', str(WORK / 'ccl-tests')])
        source_inputs = {str(p.relative_to(SOURCE)): digest(p) for p in sorted(SOURCE.rglob('*')) if p.is_file()}
        save(OUT / 'source-inputs.json', source_inputs)
        command('extract-bootstrap', ['tar', '-xzf', str(INPUTS / 'bootstrap.tar.gz'), '-C', str(SOURCE)])
        # Stable metadata for a source archive without .git; no source is patched.
        make_args = ['/usr/bin/make', '-C', str(SOURCE / 'lisp-kernel/darwinx8664'), 'VC_REVISION="v1.13"']
        manifests = []
        for number in (1, 2):
            label = 'run-%d' % number
            directory = OUT / label
            directory.mkdir()
            # Do not seed the second build from the first build's saved heap.
            command(label + '-restore-image', ['tar', '-xzf', str(INPUTS / 'bootstrap.tar.gz'),
                                               '-C', str(SOURCE), 'dx86cl64.image'])
            command(label + '-kernel-clean', make_args + ['clean'])
            command(label + '-kernel-build', make_args + ['-j2'])
            command(label + '-clean-rebuild', ['./dx86cl64', '--no-init', '--batch', '--eval',
                    '(progn (rebuild-ccl :clean t) (format t "~&CCL-GATE0-REBUILD-COMPLETE~%") (finish-output) (quit))'],
                    cwd=SOURCE, marker='CCL-GATE0-REBUILD-COMPLETE')
            command(label + '-rebuilt-start', ['./dx86cl64', '--no-init', '--batch', '--eval',
                    '(progn (format t "~&CCL-GATE0-REBUILT ~a~%" (lisp-implementation-version)) (finish-output) (quit))'],
                    cwd=SOURCE, marker='CCL-GATE0-REBUILT')
            files = sorted(SOURCE.rglob('*.dx64fsl'))
            if not files:
                raise RuntimeError('clean rebuild produced no FASLs')
            manifest = {str(p.relative_to(SOURCE)): digest(p) for p in files}
            save(directory / 'fasls.json', manifest)
            manifests.append(manifest)
            for path in files + [SOURCE / 'dx86cl64', SOURCE / 'dx86cl64.image']:
                dest = directory / 'build' / path.relative_to(SOURCE)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
            command(label + '-tests-clean', ['make', 'clean'], cwd=WORK / 'ccl-tests')
            command(label + '-tests', [str(SOURCE / 'dx86cl64'), '--no-init', '--batch',
                                      '--load', str(RUNNER / 'tests.lisp'),
                                      '--eval', '(cl-user::run-gate0-tests)'], cwd=WORK / 'ccl-tests',
                    extra_env={'CCL_GATE0_OUTPUT': str(directory) + '/', 'CCL_GATE0_TESTS': str(WORK / 'ccl-tests') + '/'},
                    marker='CCL-GATE0-TESTS-COMPLETE PASS')
            stats = json.loads((directory / 'test-summary.json').read_text())
            if not stats['success'] or stats['passed'] != stats['eligible']:
                raise RuntimeError('test summary is incomplete')
            report['runs'].append({'id': label, 'tests': stats, 'fasl_count': len(files),
                                   'kernel_sha256': digest(SOURCE / 'dx86cl64'),
                                   'image_sha256': digest(SOURCE / 'dx86cl64.image')})
        if manifests[0].keys() != manifests[1].keys():
            raise RuntimeError('clean rebuilds have different FASL inventories')
        different = [p for p in manifests[0] if manifests[0][p] != manifests[1][p]]
        report['repeatability'] = {'total': len(manifests[0]), 'identical': len(manifests[0]) - len(different),
                                   'different': different, 'normalizations': [],
                                   'status': 'UNEXPLAINED_VARIANCE' if different else 'RAW_IDENTICAL'}
        changed = [p for p, expected in source_inputs.items() if not (SOURCE / p).is_file() or digest(SOURCE / p) != expected]
        if changed:
            raise RuntimeError('tracked source changed: ' + repr(changed))
        report['source_preservation'] = 'ALL_ARCHIVED_SOURCE_FILES_UNCHANGED'
        report['execution_status'] = 'PASS'
        report['gate0_status'] = 'EXECUTED_NOT_ACCEPTED'
    except Exception as exc:
        report['failure'] = str(exc)
    report['completed_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    report['artifacts'] = [{'path': str(p.relative_to(OUT)), 'sha256': digest(p)}
                           for p in sorted(OUT.rglob('*')) if p.is_file()]
    save(OUT / 'results.json', report)
    print(json.dumps({k: v for k, v in report.items() if k != 'artifacts'}, indent=2), flush=True)
    return 0 if report['execution_status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(run())
