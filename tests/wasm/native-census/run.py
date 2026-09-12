#!/usr/bin/env python3
"""Observe native U1 in a disposable tree and prove restoration/output equivalence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time
from reversible import ObservationUnit, digest, save

HERE = Path(__file__).resolve().parent
U1 = 'c994217adc56b3f8a564526cee4695893ac84d86'
TESTS = '561ab1be82fefd53a61089eaad4357023e1fa961'


def restore_clean_outputs(work):
    work = work.resolve(); source = work / 'ccl'
    manifest = json.loads((work / 'clean-baseline.json').read_text())
    # Verify every backup before restoring any output.
    for r in manifest['files']:
        if digest(Path(r['backup'])) != r['sha256']: raise ValueError('clean output backup changed')
        name = Path(r['path'])
        if name.is_absolute() or '..' in name.parts: raise ValueError('invalid clean output path')
    wanted = {r['path'] for r in manifest['files']}
    for p in source.rglob('*.dx64fsl'):
        if str(p.relative_to(source)) not in wanted: p.unlink()
    for r in manifest['files']:
        dest = source / r['path']; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(r['backup'], dest)
        if digest(dest) != r['sha256']: raise ValueError('clean output restoration failed')
    return {'status': 'PASS', 'files': len(manifest['files']),
            'source': 'unmodified native baseline; observed artifacts are evidence only'}


def run(inputs, work, output, observer_extension=None):
    inputs, work, output = [p.resolve() for p in (inputs, work, output)]
    if platform.system() != 'Darwin' or platform.machine() != 'x86_64':
        raise ValueError('requires the pinned macOS x86-64 native reference')
    if any(a == b or a in b.parents or b in a.parents
           for a, b in [(work, output), (inputs, work), (inputs, output)]):
        raise ValueError('inputs, disposable work and evidence must be separate')
    for p in [work, output]:
        p.mkdir(parents=True, exist_ok=True)
        if any(p.iterdir()): raise ValueError('work/output must be new and empty')
    source = work / 'ccl'; source.mkdir()
    save(work / 'disposable.json', {'purpose': 'native-census-disposable-U1', 'source': str(source)})
    shutil.copytree(HERE, output / 'runner', ignore=shutil.ignore_patterns('__pycache__'))
    fixture = output / 'runner'
    if observer_extension:
        extension = Path(observer_extension).resolve()
        shutil.copyfile(extension, fixture / 'observer-extension.lisp')
    pins = json.loads((inputs / 'pins.json').read_text())
    if pins['source_revision'] != U1 or pins['test_revision'] != TESTS:
        raise ValueError('source/test pins differ from accepted native U1')
    for name, expected in pins['inputs'].items():
        if digest(inputs / name) != expected: raise ValueError('input mismatch: ' + name)
    shutil.copyfile(inputs / 'pins.json', output / 'pins.json')
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin',
           'LANG': 'C', 'LC_ALL': 'C', 'CCL_DEFAULT_DIRECTORY': str(source)}
    commands = []

    def command(name, argv, extra=None, cwd=source, timeout=1800, marker=None, allow_failure=False):
        start = time.monotonic(); log = output / (name + '.log')
        record = {'name': name, 'argv': argv, 'cwd': str(cwd), 'environment': {**env, **(extra or {})},
                  'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'timeout': timeout}
        print('Running ' + name, flush=True)
        try:
            with log.open('wb') as f:
                r = subprocess.run(argv, cwd=cwd, env=record['environment'], stdout=f,
                                   stderr=subprocess.STDOUT, timeout=timeout)
            record['exit_code'] = r.returncode
            if not allow_failure and (r.returncode or (marker and marker not in log.read_text(errors='replace'))):
                raise RuntimeError(name + ' failed or missing completion marker; see ' + log.name)
            return record
        finally:
            record['seconds'] = time.monotonic() - start
            if log.exists(): record['log_sha256'] = digest(log)
            commands.append(record); save(output / 'commands.json', commands)

    def lisp(name, expression, observer=False, image=None, extra=None, marker='CENSUS-COMPLETE', timeout=1800):
        argv = [str(source / 'dx86cl64'), '--no-init', '--batch']
        if image: argv += ['--image-name', str(image)]
        if observer:
            argv += ['--load', str(fixture / 'observer.lisp')]
            if observer_extension: argv += ['--load', str(fixture / 'observer-extension.lisp')]
        argv += ['--eval', expression]
        return command(name, argv, extra={'CCL_CENSUS_EVENTS': str(output / (name + '.jsonl')), **(extra or {})}, marker=marker, timeout=timeout)

    def capture_build(label):
        dest = output / label; dest.mkdir()
        paths = sorted(source.rglob('*.dx64fsl'))
        hashes = {str(p.relative_to(source)): digest(p) for p in paths}
        for p in paths + [source / 'dx86cl64', source / 'dx86cl64.image', source / 'x86-boot64.image']:
            target = dest / 'build' / p.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(p, target)
        save(dest / 'fasls.json', hashes)
        return hashes

    def regression(label, observe):
        dest = output / label; dest.mkdir()
        command(label + '-clean', ['make', 'clean'], cwd=work / 'ccl-tests')
        driver = (HERE.parent / 'native-baseline/tests.lisp').read_text()
        if observe:
            driver = '(ccl-startup-census::start)\n' + driver.replace(
                '(ccl:quit (if success 0 1))', '(ccl-startup-census::finish) (ccl:quit (if success 0 1))')
        (dest / 'tests.lisp').write_text(driver)
        argv = [str(source / 'dx86cl64'), '--no-init', '--batch']
        if observe:
            argv += ['--load', str(fixture / 'observer.lisp')]
            if observer_extension: argv += ['--load', str(fixture / 'observer-extension.lisp')]
        argv += ['--load', str(dest / 'tests.lisp'), '--eval', '(cl-user::run-gate0-tests)']
        command(label, argv, cwd=work / 'ccl-tests', extra={
            'CCL_GATE0_TESTS': str(work / 'ccl-tests') + '/', 'CCL_GATE0_OUTPUT': str(dest) + '/',
            'CCL_CENSUS_EVENTS': str(dest / 'events.jsonl')}, marker='CCL-GATE0-TESTS-COMPLETE PASS')
        result = json.loads((dest / 'test-summary.json').read_text())
        if not result['success'] or result['passed'] != 21843: raise RuntimeError('native test inventory differs')
        return result

    report = {'version': 1, 'source_revision': U1, 'test_revision': TESTS,
              'scope': 'Reversible native startup/compiler observation before Wasm backend changes',
              'execution_status': 'FAIL', 'review_disposition': 'NOT_REVIEWED',
              'census_acceptance': 'BLOCKED', 'substitutions': [], 'normalizations': []}
    if observer_extension:
        report['observer_extension'] = {'path': 'runner/observer-extension.lisp',
                                       'sha256': digest(fixture / 'observer-extension.lisp')}
    originals = None; unit = None; baseline = None
    try:
        command('extract-source', ['tar', '-xf', str(inputs / 'source.tar'), '-C', str(source)])
        originals = {str(p.relative_to(source)): digest(p) for p in source.rglob('*') if p.is_file()}
        save(output / 'original-source-hashes.json', originals)
        (work / 'ccl-tests').mkdir()
        command('extract-tests', ['tar', '-xf', str(inputs / 'tests.tar'), '-C', str(work / 'ccl-tests')])
        command('extract-bootstrap', ['tar', '-xzf', str(inputs / 'bootstrap.tar.gz'), '-C', str(source)])
        for name, argv in [('host', ['uname', '-a']), ('os', ['sw_vers']),
                           ('cpu', ['sysctl', 'machdep.cpu.brand_string']), ('compiler', ['clang', '--version']),
                           ('sdk', ['xcrun', '--show-sdk-version']), ('m4', ['gm4', '--version'])]:
            command(name, argv)
        trace = command('external-trace-availability', ['/usr/bin/fs_usage', '-w', '-f', 'filesys', '-t', '1'],
                        timeout=10, allow_failure=True)
        report['external_trace'] = {'status': 'UNAVAILABLE' if trace['exit_code'] else 'AVAILABLE_NOT_CAPTURED',
                                    'log': 'external-trace-availability.log',
                                    'scope': 'Availability probe only; never substituted for a cold-start trace'}
        command('kernel-build', ['make', '-C', str(source / 'lisp-kernel/darwinx8664'),
                                'VC_REVISION="v1.13"', '-j2'])
        install = '(let ((*gensym-counter* *gensym-counter*) (ccl::*warn-if-redefine-kernel* nil) (ccl::*cerror-on-constant-redefinition* nil)) ' + ''.join(
            '(load (compile-file "ccl:' + r['path'].replace('/', ';') + '")) '
            for r in json.loads((fixture / 'patch.json').read_text())['files']) + ')'
        # Gensym state is an explicit compiler input, not output normalization.
        # Both variants use the same bootstrap and installation sequence.
        rebuild_body = '(let ((*gensym-counter* 100000)) (rebuild-ccl :clean t))'
        rebuild = '(progn ' + install + ' ' + rebuild_body + ' (format t "CENSUS-COMPLETE~%") (ccl:quit))'
        report['comparison_inputs'] = {'bootstrap': 'original pinned image for every build',
            'gensym_counter_at_rebuild': 100000, 'installation_gensym_counter': 'dynamically isolated',
            'gensym_counter_at_probe_compile': 100000,
            'same_installation_sequence': ['compiler/nx.lisp', 'lib/nfcomp.lisp', 'lib/dumplisp.lisp']}
        lisp('baseline-rebuild', rebuild, observer=True)
        baseline = capture_build('baseline')
        clean_files = list(baseline) + ['dx86cl64', 'dx86cl64.image', 'x86-boot64.image']
        save(work / 'clean-baseline.json', {'files': [
            {'path': n, 'backup': str(output / 'baseline/build' / n),
             'sha256': digest(output / 'baseline/build' / n)} for n in clean_files]})
        report['baseline_tests'] = regression('baseline-tests', False)
        snap = '(progn (ccl-startup-census::start) (ccl-startup-census::finish) (format t "CENSUS-COMPLETE~%") (ccl:quit))'
        lisp('baseline-snapshot', snap, observer=True)
        probe = str(work / 'probe.lisp'); shutil.copyfile(fixture / 'probe.lisp', probe)
        probe_expr = '(progn (let ((*gensym-counter* 100000)) (load (compile-file ' + json.dumps(probe) + '))) (assert (= 10 (cl-user::census-probe-parent 4))) (assert (equal (multiple-value-list (cl-user::census-probe-values 7)) (list 7 8 -7))) (format t "CENSUS-COMPLETE~%") (ccl:quit))'
        lisp('baseline-probe', probe_expr, observer=True)
        shutil.copyfile(work / 'probe.dx64fsl', output / 'baseline-probe.dx64fsl')
        command('observed-restore-bootstrap', ['tar', '-xzf', str(inputs / 'bootstrap.tar.gz'), '-C', str(source), 'dx86cl64.image'])
        unit = ObservationUnit(work, fixture)
        with unit:
            lisp('observed-rebuild', '(progn ' + install + ' (ccl-startup-census::start) ' + rebuild_body + ' (ccl-startup-census::finish) (format t "CENSUS-COMPLETE~%") (ccl:quit))', observer=True)
            observed = capture_build('observed')
            if baseline.keys() != observed.keys(): raise RuntimeError('native FASL inventory changed')
            changed = [n for n in baseline if baseline[n] != observed[n]]
            allowed = {'l1-fasls/nx.dx64fsl', 'bin/nfcomp.dx64fsl', 'bin/dumplisp.dx64fsl'}
            if set(changed) != allowed: raise RuntimeError('unexplained or missing intentional FASL differences: ' + repr(changed))
            report['fasl_comparison'] = {'total': len(baseline), 'raw_identical': len(baseline) - len(changed),
                                         'intentional_shared_artifacts': changed, 'unexplained': []}
            lisp('observed-probe', probe_expr.replace('(progn ', '(progn (ccl-startup-census::start) ', 1).replace(
                '(format t "CENSUS-COMPLETE', '(ccl-startup-census::finish) (format t "CENSUS-COMPLETE'), observer=True)
            shutil.copyfile(work / 'probe.dx64fsl', output / 'observed-probe.dx64fsl')
            if digest(output / 'baseline-probe.dx64fsl') != digest(output / 'observed-probe.dx64fsl'):
                raise RuntimeError('unchanged probe output differs')
            report['observed_tests'] = regression('observed-tests', True)
            lisp('observed-snapshot', snap, observer=True)
            image = output / 'observed-startup.image'
            # This image is evidence only and is never returned as a clean baseline.
            lisp('prepare-observed-startup', '(progn (format t "CENSUS-IMAGE-READY~%") (finish-output) (ccl-startup-census::prepare-observed-image ' + json.dumps(str(image)) + '))', observer=True, marker='CENSUS-IMAGE-READY')
            lisp('observed-cold-start', '(progn (ccl-startup-census::start) (ccl-startup-census::finish) (format t "CENSUS-COMPLETE~%") (ccl:quit))', image=image, timeout=30)
        report['source_restoration'] = json.loads((work / 'observation-state.json').read_text())
        # Rebuild from the original bootstrap after removal. No observed image
        # or FASL is allowed to be the implementation's clean starting point.
        command('restore-original-bootstrap', ['tar', '-xzf', str(inputs / 'bootstrap.tar.gz'), '-C', str(source), 'dx86cl64.image'])
        lisp('restored-clean-rebuild', rebuild, observer=True)
        restored = capture_build('restored-clean')
        if restored != baseline: raise RuntimeError('clean rebuild after reversal differs from baseline')
        lisp('restored-clean-start', '(progn (assert (not (find-symbol "*STARTUP-CENSUS-HOOK*" "CCL"))) (format t "CENSUS-COMPLETE~%") (ccl:quit))')
        report['restored_fasls_identical'] = len(restored)
        report['execution_status'] = 'PASS'
    except BaseException as exc:
        report['failure'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        if unit and unit.state.exists() and json.loads(unit.state.read_text())['active']:
            try: report['source_restoration'] = unit.restore()
            except Exception as exc: report['restoration_failure'] = str(exc)
        if originals:
            changed = [n for n, h in originals.items() if not (source / n).is_file() or digest(source / n) != h]
            report['all_archived_sources_restored'] = not changed
            if changed: report['execution_status'] = 'FAIL'; report['changed_source_files'] = changed
        if (work / 'clean-baseline.json').exists():
            try: report['clean_output_restoration'] = restore_clean_outputs(work)
            except Exception as exc:
                report['execution_status'] = 'FAIL'; report['output_restoration_failure'] = str(exc)
        report['completed_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        report['artifacts'] = [{'path': str(p.relative_to(output)), 'sha256': digest(p)}
                               for p in sorted(output.rglob('*')) if p.is_file()]
        save(output / 'results.json', report)
    print(json.dumps({k: v for k, v in report.items() if k != 'artifacts'}, indent=2), flush=True)
    return 0 if report['execution_status'] == 'PASS' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--restore', action='store_true')
    parser.add_argument('--observer-extension', type=Path)
    args = parser.parse_args()
    if args.restore:
        source_result = ObservationUnit(args.work, HERE).restore()
        outputs = restore_clean_outputs(args.work)
        print(json.dumps({'source': source_result, 'clean_outputs': outputs}, indent=2))
    else:
        if not args.inputs or not args.output: parser.error('--inputs and --output required')
        def interrupted(signum, _): raise InterruptedError('signal ' + str(signum))
        signal.signal(signal.SIGTERM, interrupted)
        sys.exit(run(args.inputs, args.work, args.output, args.observer_extension))
