#!/usr/bin/env python3
"""Run early-boot observation in disposable U1 and check native R6."""
import argparse
import gzip
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from analyze import analyze, read, bind_files
from unit import BootUnit
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reversible import digest, save

HERE = Path(__file__).resolve().parent
U1 = 'c994217adc56b3f8a564526cee4695893ac84d86'
INTENTIONAL = {'level-0/l0-def.dx64fsl', 'level-0/nfasload.dx64fsl', 'level-1.dx64fsl'}


def run(mode, inputs, kernel, work, output):
    if platform.system() != 'Darwin' or platform.machine() != 'x86_64': raise ValueError('requires macOS x86-64')
    if any(a == b or a in b.parents or b in a.parents for a, b in
           [(inputs, work), (inputs, output), (work, output)]): raise ValueError('inputs/work/output must be separate')
    output.mkdir(parents=True, exist_ok=False)
    source = work / 'ccl'; report = {'version': 1, 'mode': mode, 'status': 'FAIL', 'commands': [],
                                    'review_disposition': 'NOT_REVIEWED', 'source_revision': U1}
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin', 'LANG': 'C', 'LC_ALL': 'C',
           'CCL_DEFAULT_DIRECTORY': str(source)}
    unit = None; baseline = None
    def command(name, argv, *, cwd=source, extra=None, marker=None, stdin=None, timeout=1800):
        row = {'name': name, 'argv': argv, 'cwd': str(cwd), 'environment': {**env, **(extra or {})},
               'input': stdin, 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'timeout_seconds': timeout}
        print('Running ' + name, flush=True); started = time.monotonic()
        try:
            with (output / (name + '.log')).open('wb') as log:
                child = subprocess.Popen(argv, cwd=cwd, env=row['environment'], stdout=log,
                                         stderr=subprocess.STDOUT, stdin=subprocess.PIPE, start_new_session=True)
                try: child.communicate(None if stdin is None else stdin.encode(), timeout=timeout)
                except BaseException:
                    try: os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    child.wait(); raise
            row['exit_code'] = child.returncode
            if child.returncode or marker and marker not in (output / (name + '.log')).read_text(errors='replace'):
                raise ValueError(name + ' failed; see retained log')
        finally:
            row['seconds'] = round(time.monotonic() - started, 3); report['commands'].append(row)
            save(output / 'commands.json', report['commands'])
    def lisp(name, expr, loads=(), **kw):
        argv = [str(source / 'dx86cl64'), '--no-init', '--batch']
        for p in loads: argv += ['--load', str(p)]
        command(name, argv + ['--eval', expr], **kw)
    def fasls(): return {str(p.relative_to(source)): digest(p) for p in sorted(source.rglob('*.dx64fsl'))}
    def bootstrap():
        with tarfile.open(inputs / 'bootstrap.tar.gz') as archive: archive.extract(archive.getmember('dx86cl64.image'), source)
    def build(name):
        bootstrap()
        lisp(name, '(progn (let ((*gensym-counter* 100000)) (rebuild-ccl :clean t)) (format t "BOOT-BUILD-PASS~%") (ccl:quit))', marker='BOOT-BUILD-PASS')
        result = fasls(); save(output / (name + '-fasls.json'), result); return result
    def tests(name):
        dest = output / name; dest.mkdir()
        command(name + '-clean', ['make', 'clean'], cwd=work / 'ccl-tests')
        lisp(name, '(cl-user::run-gate0-tests)', [HERE.parents[1] / 'native-baseline/tests.lisp'], cwd=work / 'ccl-tests',
             extra={'CCL_GATE0_TESTS': str(work / 'ccl-tests') + '/', 'CCL_GATE0_OUTPUT': str(dest) + '/'}, marker='CCL-GATE0-TESTS-COMPLETE PASS')
        result = json.loads((dest / 'test-summary.json').read_text())
        if not result['success'] or result['passed'] != 21843 or result['upstream_disabled'] != 75:
            raise ValueError('native test inventory/result changed')
        return result
    def snapshot(name):
        dest = output / (name + '.json')
        lisp(name, '(progn (cl-user::boot-native-snapshot) (ccl:quit))',
             [HERE.parent / 'observer.lisp', HERE / 'snapshot.lisp'],
             extra={'CCL_BOOT_SNAPSHOT_OUTPUT': str(dest)}, marker='BOOT-SNAPSHOT-COMPLETE')
        return json.loads(dest.read_text())
    def restore_outputs():
        for p in source.rglob('*.dx64fsl'): p.unlink()
        with tarfile.open(work / 'baseline-fasls.tar.gz') as archive: archive.extractall(source)
        for name in ('dx86cl64.image', 'x86-boot64.image'): shutil.copyfile(work / 'clean-images' / name, source / name)
        if fasls() != baseline: raise ValueError('clean output restoration failed')
    try:
        pins = json.loads((inputs / 'pins.json').read_text())
        if (pins['source_revision'] != U1 or pins['test_revision'] != '561ab1be82fefd53a61089eaad4357023e1fa961'
                or pins['native_target'] != 'macOS x86-64'): raise ValueError('wrong native inputs')
        report['inputs'] = pins; report['kernel'] = {'path': str(kernel), 'sha256': digest(kernel)}
        report['source_sha256'] = {str(p): digest(p) for p in [HERE / 'run.py', HERE / 'unit.py',
                                  HERE.parent / 'reversible.py', HERE.parents[1] / 'native-baseline/tests.lisp']}
        if mode == 'prepare':
            work.mkdir(parents=True, exist_ok=False); source.mkdir()
            save(work / 'disposable.json', {'purpose': 'boot-census-disposable-U1', 'source': str(source)})
            for name, expected in pins['inputs'].items():
                if digest(inputs / name) != expected: raise ValueError('changed direct input: ' + name)
            for name, dest in [('source.tar', source), ('bootstrap.tar.gz', source), ('tests.tar', work / 'ccl-tests')]:
                dest.mkdir(exist_ok=True)
                with tarfile.open(inputs / name) as archive: archive.extractall(dest)
            shutil.copyfile(kernel, source / 'dx86cl64'); (source / 'dx86cl64').chmod(0o755)
            baseline = build('baseline')
            with tarfile.open(work / 'baseline-fasls.tar.gz', 'w:gz') as archive:
                for name in baseline: archive.add(source / name, arcname=name)
            (work / 'clean-images').mkdir()
            for name in ('dx86cl64.image', 'x86-boot64.image'): shutil.copyfile(source / name, work / 'clean-images' / name)
            report['native_tests'] = tests('baseline-tests')
            save(work / 'baseline.json', {'fasls': baseline, 'preparation': str(output), 'inputs': pins,
                                         'kernel_sha256': report['kernel']['sha256']})
        else:
            saved = json.loads((work / 'baseline.json').read_text()); baseline = saved['fasls']
            before = json.loads((Path(saved['preparation']) / 'run.json').read_text())
            if before['status'] != 'PASS' or saved['inputs'] != pins or saved['kernel_sha256'] != report['kernel']['sha256']:
                raise ValueError('baseline is not a successful matching preparation')
            if digest(source / 'dx86cl64') != report['kernel']['sha256'] or fasls() != baseline:
                raise ValueError('disposable baseline changed')
            report['baseline'] = {'run': str(Path(saved['preparation']) / 'run.json'), 'sha256': digest(Path(saved['preparation']) / 'run.json')}
            for name in ('observation.patch', 'patch.json', 'export.lisp', 'build_patch.py', 'snapshot.lisp', 'analyze.py'):
                report['source_sha256'][str(HERE / name)] = digest(HERE / name)
            for name in ('observer.lisp',):
                report['source_sha256'][str(HERE.parent / name)] = digest(HERE.parent / name)
            report['source_sha256'][str(source / 'xdump/faslenv.lisp')] = digest(source / 'xdump/faslenv.lisp')
            native_before = snapshot('baseline-snapshot')
            unit = BootUnit(work)
            with unit:
                observed = build('observed')
                if observed.keys() != baseline.keys(): raise ValueError('changed FASL inventory')
                changed = {p for p in baseline if baseline[p] != observed[p]}
                report['r6'] = {'total': len(baseline), 'identical': len(baseline) - len(changed), 'changed': sorted(changed),
                                'unexplained': sorted(changed - INTENTIONAL)}
                for name in changed:
                    dest = output / 'changed-fasls' / name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source / name, dest)
                if changed != INTENTIONAL: raise ValueError('unexpected changed FASLs: ' + repr(sorted(changed)))
                for name in ('dx86cl64.image', 'x86-boot64.image'):
                    with (source / name).open('rb') as src, gzip.open(output / (name + '.gz'), 'wb') as dst: shutil.copyfileobj(src, dst)
                report['images'] = {name: digest(source / name) for name in ('dx86cl64.image', 'x86-boot64.image')}
                lisp('export', '(progn (cl-user::export-boot-census) (ccl:quit))', [HERE.parent / 'observer.lisp',
                     HERE / 'export.lisp'], extra={'CCL_BOOT_CENSUS_OUTPUT': str(output / 'events.jsonl')}, marker='BOOT-CENSUS-EXPORTED')
                with (output / 'events.jsonl').open('rb') as src, gzip.open(output / 'events.jsonl.gz', 'wb') as dst: shutil.copyfileobj(src, dst)
                (output / 'events.jsonl').unlink()
                joined = analyze(read(output / 'events.jsonl.gz'))
                with gzip.open(output / 'joins.json.gz', 'wt') as stream: json.dump(joined, stream, separators=(',', ':')); stream.write('\n')
                save(output / 'summary.json', joined['summary']); report['observation'] = joined['summary']
                save(output / 'files.json', bind_files(joined, source))
                if snapshot('observed-snapshot') != native_before: raise ValueError('native evaluated tables changed')
                report['native_snapshot_identical'] = True
                report['native_tests'] = tests('observed-tests')
            restored = build('restored')
            if restored != baseline: raise ValueError('restored FASLs differ from baseline')
            report['restored_fasls_identical'] = len(restored)
        report['status'] = 'PASS'
    except BaseException as exc:
        report['error'] = type(exc).__name__ + ': ' + str(exc)
        if mode == 'capture' and baseline:
            # Preserve partial native outputs before the finally block restores
            # clean executables. A failed boot is evidence, not a successful run.
            try:
                partial = output / 'failed-outputs'; partial.mkdir()
                for name, value in fasls().items():
                    if baseline.get(name) != value:
                        dest = partial / name; dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(source / name, dest)
                image = source / 'x86-boot64.image'
                if image.exists():
                    with image.open('rb') as src, gzip.open(partial / 'x86-boot64.image.gz', 'wb') as dst: shutil.copyfileobj(src, dst)
            except Exception as retention_error: report['failure_retention_error'] = str(retention_error)
    finally:
        if unit and unit.state.exists() and json.loads(unit.state.read_text())['active']:
            try: report['source_restoration'] = unit.restore()
            except Exception as exc: report['restoration_error'] = str(exc)
        if baseline and (work / 'baseline-fasls.tar.gz').exists() and (work / 'clean-images').exists():
            try: restore_outputs(); report['clean_outputs_restored'] = True
            except Exception as exc: report['restoration_error'] = str(exc); report['status'] = 'FAIL'
        report['completed_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()); save(output / 'run.json', report)
    print(json.dumps({k: report[k] for k in ('status', 'error', 'r6', 'restored_fasls_identical') if k in report}), flush=True)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=['prepare', 'capture'])
    for name in ('inputs', 'kernel', 'work', 'output'): p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    def interrupted(signum, _): raise InterruptedError('signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    sys.exit(run(a.mode, *(getattr(a, name).resolve() for name in ('inputs', 'kernel', 'work', 'output'))))
