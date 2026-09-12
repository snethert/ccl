#!/usr/bin/env python3
"""Qualify reversible census registration with native R6 and clean target sessions."""
import argparse
import json
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from registration import Registration
from check import check
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reversible import digest, save

HERE = Path(__file__).resolve().parent
U1 = 'c994217adc56b3f8a564526cee4695893ac84d86'
TESTS = '561ab1be82fefd53a61089eaad4357023e1fa961'


def run(inputs, kernel, work, output, failures=None):
    if platform.system() != 'Darwin' or platform.machine() != 'x86_64':
        raise ValueError('requires the macOS x86-64 reference host')
    for p in (work, output):
        if p.exists(): raise ValueError('work/output must be new')
        p.mkdir(parents=True)
    source = work / 'ccl'; source.mkdir()
    save(work / 'disposable.json', {'purpose': 'census-stub-disposable-U1', 'source': str(source)})
    pins = json.loads((inputs / 'pins.json').read_text())
    if pins['source_revision'] != U1 or pins['test_revision'] != TESTS or pins['native_target'] != 'macOS x86-64':
        raise ValueError('requires the reviewed U1 macOS inputs')
    for name, expected in pins['inputs'].items():
        if digest(inputs / name) != expected: raise ValueError('changed direct input: ' + name)
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin', 'LANG': 'C', 'LC_ALL': 'C',
           'CCL_DEFAULT_DIRECTORY': str(source)}
    commands = []
    report = {'version': 1, 'source_revision': U1, 'test_revision': TESTS, 'execution_status': 'FAIL',
              'review_disposition': 'NOT_REVIEWED', 'evidence_kind': 'HOST COMPILATION',
              'scope': 'Reversible observation-only registration, native R6 and fourteen front-end cases. No target executable/FASL, full source census or foreign/lowering implementation.',
              'inputs': {'directory': str(inputs), 'pins': pins, 'kernel': str(kernel), 'kernel_sha256': digest(kernel)},
              'fixture_sha256': {str(p.relative_to(HERE)): digest(p) for p in sorted(HERE.rglob('*'))
                                 if p.is_file() and '__pycache__' not in p.parts},
              'shared_dependencies_sha256': {str(p): digest(p) for p in [HERE.parent / 'observer.lisp', HERE.parent / 'dependencies.lisp',
                                                                         HERE.parent / 'reversible.py', HERE.parent / 'probe.lisp',
                                                                         HERE.parents[1] / 'native-baseline/tests.lisp']},
              'substitutions': [], 'normalizations': [], 'skips': ['Target code emission and execution are outside this observation-only registration slice.']}
    unit = None; baseline = None; originals = None
    if failures: shutil.copytree(failures, output / 'development-failures')
    for name in ('patch.json', 'registration.patch'): shutil.copyfile(HERE / name, output / name)

    def command(name, argv, extra=None, cwd=source, marker=None, allowed_failure=False, timeout=1800):
        start = time.monotonic(); path = output / (name + '.log')
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {'name': name, 'argv': argv, 'cwd': str(cwd), 'environment': {**env, **(extra or {})},
                  'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        print('Running ' + name, flush=True)
        try:
            with path.open('wb') as log:
                child = subprocess.run(argv, cwd=cwd, env=record['environment'], stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
            record['exit_code'] = child.returncode
            if not allowed_failure and (child.returncode or marker and marker not in path.read_text(errors='replace')):
                raise ValueError(name + ' failed; see retained log')
            return child.returncode
        finally:
            record['seconds'] = round(time.monotonic() - start, 3); commands.append(record)
            save(output / 'commands.json', commands)

    def lisp(name, expr=None, loads=(), extra=None, marker=None, allowed_failure=False, cwd=source):
        argv = [str(source / 'dx86cl64'), '--no-init', '--batch']
        for p in loads: argv += ['--load', str(p)]
        if expr: argv += ['--eval', expr]
        return command(name, argv, extra, cwd, marker, allowed_failure)

    def fasls(): return {str(p.relative_to(source)): digest(p) for p in sorted(source.rglob('*.dx64fsl'))
                         if p.name not in ('wasm-census-arch.dx64fsl', 'wasm-census-backend.dx64fsl')}

    def bootstrap():
        with tarfile.open(inputs / 'bootstrap.tar.gz') as archive:
            member = archive.getmember('dx86cl64.image'); archive.extract(member, source)

    def snapshot(name, registered):
        loads = ([HERE / 'load-registration.lisp'] if registered else []) + [HERE.parent / 'observer.lisp', HERE / 'snapshot.lisp']
        lisp(name, loads=loads, extra={'CCL_CENSUS_REPORT': str(output / (name + '.json'))}, marker='CENSUS-SNAPSHOT-COMPLETE')
        return json.loads((output / (name + '.json')).read_text())

    def tests(name, registered):
        dest = output / name; dest.mkdir()
        command(name + '-clean', ['make', 'clean'], cwd=work / 'ccl-tests')
        loads = ([HERE / 'load-registration.lisp'] if registered else []) + [HERE.parents[1] / 'native-baseline/tests.lisp']
        lisp(name, '(cl-user::run-gate0-tests)', loads, {'CCL_GATE0_TESTS': str(work / 'ccl-tests') + '/',
             'CCL_GATE0_OUTPUT': str(dest) + '/'}, 'CCL-GATE0-TESTS-COMPLETE PASS', cwd=work / 'ccl-tests')
        data = json.loads((dest / 'test-summary.json').read_text())
        if not data['success'] or data['passed'] != 21843 or data['upstream_disabled'] != 75:
            raise ValueError('native test inventory/result differs')
        return data

    def probe(name, registered):
        path = work / 'probe.lisp'; shutil.copyfile(HERE.parent / 'probe.lisp', path)
        loads = [HERE / 'load-registration.lisp'] if registered else []
        expr = '(progn (let ((*gensym-counter* 100000)) (load (compile-file ' + json.dumps(str(path)) + '))) (assert (= 10 (cl-user::census-probe-parent 4))) (assert (equal (multiple-value-list (cl-user::census-probe-values 7)) (list 7 8 -7))) (format t "PROBE-PASS~%") (ccl:quit))'
        lisp(name, expr, loads, marker='PROBE-PASS')
        shutil.copyfile(work / 'probe.dx64fsl', output / (name + '.dx64fsl'))
        return digest(output / (name + '.dx64fsl'))

    install = '(let ((*gensym-counter* *gensym-counter*)) (load (compile-file "ccl:lib;systems.lisp")))'
    rebuild = '(let ((*gensym-counter* 100000)) (rebuild-ccl :clean t))'
    try:
        for filename, dest in [('source.tar', source), ('tests.tar', work / 'ccl-tests')]:
            dest.mkdir(exist_ok=True)
            with tarfile.open(inputs / filename) as archive: archive.extractall(dest)
        originals = {str(p.relative_to(source)): digest(p) for p in source.rglob('*') if p.is_file()}
        with tarfile.open(inputs / 'bootstrap.tar.gz') as archive: archive.extractall(source)
        shutil.copyfile(kernel, source / 'dx86cl64'); (source / 'dx86cl64').chmod(0o755)
        bootstrap()
        command('host', ['sw_vers']); command('compiler', ['clang', '--version'])
        lisp('baseline-rebuild', '(progn ' + install + rebuild + '(format t "BUILD-PASS~%") (ccl:quit))', marker='BUILD-PASS')
        baseline = fasls(); save(output / 'baseline-fasls.json', baseline)
        backup = work / 'clean-images'; backup.mkdir()
        for name in ('dx86cl64.image', 'x86-boot64.image'):
            shutil.copyfile(source / name, backup / name)
        # Store the baseline once; subsequent stages retain only changed binaries.
        with tarfile.open(output / 'baseline-fasls.tar.gz', 'w:gz') as archive:
            for name in baseline: archive.add(source / name, arcname=name)
        before = snapshot('baseline-snapshot', False)
        report['baseline_tests'] = tests('baseline-tests', False)
        probe_before = probe('baseline-probe', False)
        bootstrap(); unit = Registration(work, HERE)
        with unit:
            lisp('registered-rebuild', '(progn ' + install + '(load ' + json.dumps(str(HERE / 'load-registration.lisp')) + ')' + rebuild + '(format t "BUILD-PASS~%") (ccl:quit))', marker='BUILD-PASS')
            registered = fasls(); save(output / 'registered-fasls.json', registered)
            if registered.keys() != baseline.keys(): raise ValueError('native FASL inventory changed')
            differences = sorted(n for n in baseline if baseline[n] != registered[n])
            if differences != ['bin/systems.dx64fsl']: raise ValueError('unexplained native FASL differences: ' + repr(differences))
            shutil.copyfile(source / differences[0], output / 'registered-systems.dx64fsl')
            after = snapshot('registered-snapshot', True)
            if before['snapshot'] != after['snapshot']: raise ValueError('native evaluated snapshot changed')
            added_names = {'CCL::WASM-CENSUS-ARCH', 'CCL::WASM-CENSUS-BACKEND'}
            if [r for r in after['modules'] if r['name'] not in added_names] != before['modules']:
                raise ValueError('existing module registration changed')
            if {r['name'] for r in after['modules']} - {r['name'] for r in before['modules']} != added_names:
                raise ValueError('new registration entries differ')
            report['registered_tests'] = tests('registered-tests', True)
            if probe('registered-probe', True) != probe_before: raise ValueError('unchanged native probe differs')
            report['r6'] = {'native_fasls': len(baseline), 'byte_identical': len(baseline) - 1,
                            'intentional_shared_artifacts': differences,
                            'change': 'Two *CCL-SYSTEM* module data entries; every existing entry is unchanged.',
                            'evaluated_native_snapshot_equal': True, 'unchanged_probe_equal': True}
            target = output / 'target-sessions'; target.mkdir()
            modes = ['clean-1', 'clean-2', 'late-package', 'host-features', 'host-backend', 'wrong-args',
                     'wrong-width', 'cached-host-macro', 'dirty-features', 'missing-registration']
            outcomes = []; positives = []
            for mode in modes:
                filename = target / (mode + '.json')
                rc = lisp('target-sessions/' + mode, loads=[HERE.parent / 'observer.lisp', HERE.parent / 'dependencies.lisp', HERE / 'session.lisp'],
                          extra={'CCL_CENSUS_FIXTURE': str(HERE), 'CCL_CENSUS_REPORT': str(filename),
                                 'CCL_CENSUS_MODE': 'normal' if mode.startswith('clean-') else mode,
                                 'CCL_CENSUS_CACHE': str(target / 'host-macro.dx64fsl')}, allowed_failure=True)
                if mode == 'missing-registration':
                    if rc == 0 or 'Module WASM-CENSUS-ARCH not defined' not in (target / (mode + '.log')).read_text():
                        raise ValueError('missing registration control escaped')
                    outcomes.append({'mode': mode, 'status': 'REJECTED', 'reason': 'registered module lookup failed'}); continue
                if rc or not filename.exists(): raise ValueError(mode + ' failed before the semantic oracle')
                data = json.loads(filename.read_text())
                try: count = check(data)
                except ValueError as exc:
                    if mode.startswith('clean-'): raise
                    outcomes.append({'mode': mode, 'status': 'REJECTED', 'reason': str(exc)})
                else:
                    if not mode.startswith('clean-'): raise ValueError('target-state control escaped: ' + mode)
                    if data['native_snapshot_after'] != before['snapshot']:
                        # Dependency extension adds its own fields; compare all original snapshot fields.
                        if any(data['native_snapshot_after'][k] != v for k, v in before['snapshot'].items()):
                            raise ValueError('target session corrupted native snapshot')
                    positives.append(data); outcomes.append({'mode': mode, 'status': 'PASS', 'cases': count})
            if positives[0] != positives[1]: raise ValueError('clean target sessions differ')
            save(output / 'target-results.json', {'status': 'PASS', 'outcomes': outcomes, 'clean_sessions_equal': True})
            report['target_cases'] = 28; report['target_controls_rejected'] = 8
            for name in ('wasm-census-arch.dx64fsl', 'wasm-census-backend.dx64fsl'):
                shutil.copyfile(source / 'bin' / name, output / name)
        report['registration_restoration'] = json.loads((work / 'registration-state.json').read_text())
        for name in ('wasm-census-arch.dx64fsl', 'wasm-census-backend.dx64fsl'): (source / 'bin' / name).unlink(missing_ok=True)
        bootstrap()
        lisp('restored-rebuild', '(progn ' + install + rebuild + '(format t "BUILD-PASS~%") (ccl:quit))', marker='BUILD-PASS')
        restored = fasls(); save(output / 'restored-fasls.json', restored)
        if restored != baseline: raise ValueError('reversed native build differs')
        lisp('restored-start', '(progn (assert (not (find-package "WASM-CENSUS"))) (assert (not (ccl::find-backend :wasm32-census))) (assert (not (assoc (quote ccl::wasm-census-arch) ccl::*ccl-system*))) (format t "CLEAN-START-PASS~%") (ccl:quit))', marker='CLEAN-START-PASS')
        report['restored_fasls_equal'] = len(restored)
        report['execution_status'] = 'PASS'
    except BaseException as exc:
        report['failure'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        if unit and unit.state.exists() and json.loads(unit.state.read_text())['active']:
            try: report['registration_restoration'] = unit.restore()
            except Exception as exc: report['restoration_failure'] = str(exc)
        if originals:
            changed = [name for name, h in originals.items() if not (source / name).is_file() or digest(source / name) != h]
            report['all_archived_sources_restored'] = not changed
            if changed: report.update(execution_status='FAIL', changed_source_files=changed)
        if baseline and report['execution_status'] != 'PASS':
            # Restore clean outputs even if a later proof fails. Evidence logs
            # retain the failure; the disposable tree is never left as a port baseline.
            try:
                for p in source.rglob('*.dx64fsl'): p.unlink()
                with tarfile.open(output / 'baseline-fasls.tar.gz') as archive: archive.extractall(source)
                for name in ('dx86cl64.image', 'x86-boot64.image'):
                    shutil.copyfile(work / 'clean-images' / name, source / name)
                report['failure_output_recovery'] = 'baseline FASLs and images restored'
            except Exception as exc: report['output_recovery_failure'] = str(exc)
        report['completed_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        report['artifacts'] = [{'path': str(p.relative_to(output)), 'bytes': p.stat().st_size, 'sha256': digest(p)}
                               for p in sorted(output.rglob('*')) if p.is_file() and p != output / 'results.json']
        save(output / 'results.json', report)
    print(json.dumps({k: v for k, v in report.items() if k in ['execution_status', 'failure', 'r6', 'target_cases', 'target_controls_rejected', 'restored_fasls_equal', 'all_archived_sources_restored']}, indent=2), flush=True)
    return 0 if report['execution_status'] == 'PASS' else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('inputs', 'kernel', 'work', 'output'): p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--failures', type=Path)
    a = p.parse_args()
    def interrupted(signum, _): raise InterruptedError('signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    sys.exit(run(*(getattr(a, n).resolve() for n in ('inputs', 'kernel', 'work', 'output')), failures=a.failures))
