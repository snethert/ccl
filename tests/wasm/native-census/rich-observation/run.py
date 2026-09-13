#!/usr/bin/env python3
"""Collect actual compiler/loader identities in an owned U1 copy; enforce R6."""
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
from unit import RichUnit
from install import write_install
sys.path.append(str(Path(__file__).resolve().parents[1]))
from reversible import digest, save

HERE = Path(__file__).resolve().parent
EXECUTION_FILES = ('run.py', 'unit.py', 'build_patch.py', 'install.py', 'observer.lisp',
                   'observation.patch', 'patch.json', 'probe-driver.lisp',
                   'probe-l0.lisp', 'probe-l1.lisp', 'probe-l2.lisp')
INTENTIONAL = {'level-0/l0-def.dx64fsl', 'level-0/nfasload.dx64fsl',
               'l1-fasls/l1-readloop.dx64fsl', 'l1-fasls/nx.dx64fsl',
               'bin/nx2.dx64fsl', 'bin/vinsn.dx64fsl', 'bin/nfcomp.dx64fsl', 'bin/dumplisp.dx64fsl'}
# nx0 is included by nx; it has no separate native FASL.


def run(inputs, kernel, work, output, resume=False):
    if platform.system() != 'Darwin' or platform.machine() != 'x86_64':
        raise ValueError('requires reference macOS x86-64')
    if any(a == b or a in b.parents or b in a.parents for a, b in
           [(inputs, work), (inputs, output), (work, output)]):
        raise ValueError('inputs, work and output must be separate')
    prior = None; attempt = 1
    if resume:
        prior = json.loads((output / 'run.json').read_text())
        if prior['execution_status'] != 'FAIL' or not prior.get('clean_outputs_restored'):
            raise ValueError('only a failed run with restored clean outputs may resume')
        attempt = prior.get('attempt', 1) + 1
        shutil.copyfile(output / 'run.json', output / ('failed-run-' + str(attempt - 1) + '.json'))
        shutil.copyfile(output / 'commands.json', output / ('failed-commands-' + str(attempt - 1) + '.json'))
    else:
        for p in (work, output): p.mkdir(parents=True, exist_ok=False)
    source = work / 'ccl'
    if not resume:
        source.mkdir()
        save(work / 'disposable.json', {'purpose': 'rich-census-disposable-U1', 'source': str(source)})
    else:
        RichUnit(work).check('original_sha256')
    pins = json.loads((inputs / 'pins.json').read_text())
    if (pins['source_revision'] != 'c994217adc56b3f8a564526cee4695893ac84d86' or
        pins['test_revision'] != '561ab1be82fefd53a61089eaad4357023e1fa961' or pins['native_target'] != 'macOS x86-64'):
        raise ValueError('requires pinned U1/test inputs')
    for name, expected in pins['inputs'].items():
        if digest(inputs / name) != expected: raise ValueError('changed direct input: ' + name)
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin', 'LANG': 'C', 'LC_ALL': 'C',
           'CCL_DEFAULT_DIRECTORY': str(source)}
    report = {'version': 1, 'attempt': attempt, 'execution_status': 'FAIL', 'review_disposition': 'NOT_REVIEWED',
              'source_revision': pins['source_revision'], 'inputs': pins,
              'kernel': {'path': str(kernel), 'sha256': digest(kernel)},
              'fixture_sha256': {name: digest(HERE / name) for name in EXECUTION_FILES},
              'fixture_scope': 'Only sources executed or read by this native runner. Postprocessing, inspection and checker commands bind their own sources separately.',
              'direct_dependencies_sha256': {str(p): digest(p) for p in [HERE.parent / 'observer.lisp',
                  HERE.parent / 'dependencies.lisp', HERE.parent / 'reversible.py', HERE.parents[1] / 'native-baseline/tests.lisp']},
              'normalizations': [], 'skips': [], 'commands': []}
    for name in ('patch.json', 'observation.patch'): shutil.copyfile(HERE / name, output / name)
    if prior:
        report['reused_clean_baseline'] = {'run': 'failed-run-' + str(attempt - 1) + '.json',
                                          'reason': 'Only observation code changed; retained clean build and tests reused.'}
        if prior['inputs'] != pins or prior['kernel'] != report['kernel']:
            raise ValueError('cannot reuse a baseline with different native inputs')
    unit = None; baseline = None

    def command(name, argv, extra=None, cwd=source, marker=None, allow_failure=False, timeout=3600):
        record = {'name': name, 'argv': argv, 'cwd': str(cwd), 'environment': {**env, **(extra or {})},
                  'timeout_seconds': timeout,
                  'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        print('Running ' + name, flush=True); started = time.monotonic()
        path = output / (name + '.log'); path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open('wb') as log:
                child = subprocess.Popen(argv, cwd=cwd, env=record['environment'], stdout=log,
                                         stderr=subprocess.STDOUT, start_new_session=True)
                try: exit_code = child.wait(timeout=timeout)
                except BaseException:
                    # Stop owned descendants before restoring their input/output
                    # files; a boot-image subprocess must not outlive recovery.
                    try: os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    child.wait(); raise
            record['exit_code'] = exit_code
            if not allow_failure and (exit_code or marker and marker not in path.read_text(errors='replace')):
                raise ValueError(name + ' failed; see retained log')
            return exit_code
        finally:
            record['seconds'] = round(time.monotonic() - started, 3)
            report['commands'].append(record); save(output / 'commands.json', report['commands'])

    def lisp(name, expr, loads=(), **kwargs):
        argv = [str(source / 'dx86cl64'), '--no-init', '--batch']
        for p in loads: argv += ['--load', str(p)]
        return command(name, argv + ['--eval', expr], **kwargs)

    def helper_loads(install=False):
        return [HERE.parent / 'observer.lisp', HERE.parent / 'dependencies.lisp'] + (
            [work / 'install.lisp'] if install else []) + [HERE / 'observer.lisp']

    def bootstrap():
        with tarfile.open(inputs / 'bootstrap.tar.gz') as t: t.extract(t.getmember('dx86cl64.image'), source)

    def fasls():
        return {str(p.relative_to(source)): digest(p) for p in sorted(source.rglob('*.dx64fsl'))}

    def compress_events(name):
        path = output / (name + '.jsonl')
        with path.open('rb') as src, gzip.open(str(path) + '.gz', 'wb', compresslevel=6) as dst:
            shutil.copyfileobj(src, dst)
        path.unlink()

    def rebuild(name, observed):
        write_install(source, work / 'install.lisp')
        # Install selected definitions under an isolated gensym counter. The
        # same native installation recipe is used before and after reversal.
        expr = '(progn (let ((*gensym-counter* *gensym-counter*)) (load ' + json.dumps(str(work / 'install.lisp')) + ')) '
        if observed: expr += '(ccl-rich-census::start ' + json.dumps(str(output / (name + '.jsonl'))) + ') '
        expr += '(let ((*gensym-counter* 100000)) (rebuild-ccl :clean t)) '
        if observed: expr += '(ccl-rich-census::finish) '
        expr += '(format t "RICH-BUILD-PASS~%") (ccl:quit))'
        lisp(name, expr, helper_loads(), marker='RICH-BUILD-PASS', timeout=14400 if observed else 3600)
        if observed: compress_events(name)
        rows = fasls(); save(output / (name + '-fasls.json'), rows)
        return rows

    def tests(name, observed):
        dest = output / name; dest.mkdir()
        command(name + '-clean', ['make', 'clean'], cwd=work / 'ccl-tests')
        # Run the installed hooks as well; collect only the small explicit probe
        # here, since logging the regression harness itself is not census input.
        loads = helper_loads(True) if observed else []
        lisp(name, '(cl-user::run-gate0-tests)', loads + [HERE.parents[1] / 'native-baseline/tests.lisp'],
             extra={'CCL_GATE0_TESTS': str(work / 'ccl-tests') + '/', 'CCL_GATE0_OUTPUT': str(dest) + '/'},
             cwd=work / 'ccl-tests', marker='CCL-GATE0-TESTS-COMPLETE PASS')
        data = json.loads((dest / 'test-summary.json').read_text())
        if not data['success'] or data['passed'] != 21843 or data['upstream_disabled'] != 75:
            raise ValueError('native test outcome/inventory differs')
        return data

    def probe(name, observed, mode='normal'):
        loads = helper_loads(True) if observed else []
        expr = '(progn '
        if observed: expr += '(ccl-rich-census::start ' + json.dumps(str(output / (name + '.jsonl'))) + ') '
        expr += '(cl-user::run-rich-probe #p' + json.dumps(str(work) + '/') + ' ' + json.dumps(mode) + ') '
        if observed: expr += '(ccl-rich-census::finish) '
        expr += '(ccl:quit))'
        rc = lisp(name, expr, loads + [HERE / 'probe-driver.lisp'], marker='RICH-PROBE-PASS', allow_failure=mode != 'normal')
        if mode != 'normal':
            if not rc or "(:L1 :L0)" not in (output / (name + '.log')).read_text():
                raise ValueError('real initializer control escaped or failed for unrelated reason')
            compress_events(name)
            return {'mode': mode, 'status': 'REJECTED', 'oracle': 'native assertion on prerequisite state'}
        if observed: compress_events(name)
        hashes = {}
        for p in sorted(work.glob('probe-l*.dx64fsl')):
            dest = output / (name + '-' + p.name); shutil.copyfile(p, dest); hashes[p.name] = digest(dest)
        return hashes

    try:
        if not resume:
            for name, dest in [('source.tar', source), ('tests.tar', work / 'ccl-tests'), ('bootstrap.tar.gz', source)]:
                dest.mkdir(exist_ok=True)
                with tarfile.open(inputs / name) as t: t.extractall(dest)
            shutil.copyfile(kernel, source / 'dx86cl64'); (source / 'dx86cl64').chmod(0o755)
        for p in HERE.glob('probe-l*.lisp'): shutil.copyfile(p, work / p.name)
        if resume:
            baseline = json.loads((output / 'baseline-fasls.json').read_text())
            if fasls() != baseline: raise ValueError('restored baseline outputs differ before resume')
            report['baseline_tests'] = prior['baseline_tests']
            before_probe = {p.name.removeprefix('baseline-probe-'): digest(p) for p in output.glob('baseline-probe-probe-l*.dx64fsl')}
            for path in output.glob('*.jsonl'): compress_events(path.stem)
        else:
            baseline = rebuild('baseline', False)
            with tarfile.open(output / 'baseline-fasls.tar.gz', 'w:gz') as t:
                for name in baseline: t.add(source / name, arcname=name)
            clean = work / 'clean-images'; clean.mkdir()
            for name in ('dx86cl64.image', 'x86-boot64.image'): shutil.copyfile(source / name, clean / name)
            report['baseline_tests'] = tests('baseline-tests', False)
            before_probe = probe('baseline-probe', False)
        bootstrap(); unit = RichUnit(work)
        with unit:
            observed = rebuild('observed' + (('-r' + str(attempt)) if resume else ''), True)
            if baseline.keys() != observed.keys(): raise ValueError('native FASL inventory differs')
            changed = sorted(n for n in baseline if baseline[n] != observed[n])
            for name in changed:
                dest = output / 'changed-fasls' / name; dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / name, dest)
            report['r6'] = {'fasls': len(baseline), 'byte_identical': len(baseline) - len(changed),
                            'intentional_shared_artifacts': sorted(set(changed) & INTENTIONAL),
                            'unexplained': sorted(set(changed) - INTENTIONAL)}
            if set(changed) != INTENTIONAL: raise ValueError('unexpected changed FASL set: ' + repr(changed))
            with (source / 'dx86cl64.image').open('rb') as src, gzip.open(output / 'observed-tests.image.gz', 'wb') as dst:
                shutil.copyfileobj(src, dst)
            report['observed_test_image'] = {'artifact': 'observed-tests.image.gz',
                                            'uncompressed_sha256': digest(source / 'dx86cl64.image')}
            if probe('observed-probe', True) != before_probe: raise ValueError('unchanged probe FASLs differ')
            report['observed_tests'] = tests('observed-tests', True)
            report['state_controls'] = [probe('control-' + mode, True, mode) for mode in ('omit-l1', 'reorder')]
            image = output / 'observed-startup.image'
            lisp('prepare-startup', '(progn (format t "IMAGE-READY~%") (finish-output) (ccl-rich-census::prepare-image ' +
                 json.dumps(str(image)) + '))', helper_loads(True), marker='IMAGE-READY')
            command('cold-start', [str(source / 'dx86cl64'), '--image-name', str(image), '--no-init', '--batch',
                    '--eval', '(progn (ccl-rich-census::finish) (ccl:quit))'],
                    extra={'CCL_RICH_EVENTS': str(output / 'cold-start.jsonl')}, marker='RICH-CENSUS-COMPLETE')
            compress_events('cold-start')
        report['restoration'] = json.loads(unit.state.read_text())
        bootstrap(); restored = rebuild('restored', False)
        if restored != baseline: raise ValueError('restored native outputs differ')
        report['restored_fasls_equal'] = len(restored)
        report['execution_status'] = 'PASS'
    except BaseException as exc:
        report['failure'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        if unit and unit.state.exists() and json.loads(unit.state.read_text())['active']:
            try: report['restoration'] = unit.restore()
            except Exception as exc: report['restoration_failure'] = str(exc)
        if baseline:
            # Even an unsuccessful observation leaves this disposable copy with
            # clean executable outputs. It is never the port's starting image.
            for p in source.rglob('*.dx64fsl'): p.unlink()
            with tarfile.open(output / 'baseline-fasls.tar.gz') as t: t.extractall(source)
            for name in ('dx86cl64.image', 'x86-boot64.image'):
                shutil.copyfile(work / 'clean-images' / name, source / name)
            report['clean_outputs_restored'] = True
        report['completed_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        save(output / 'run.json', report)
    print(json.dumps({k: report[k] for k in ('execution_status', 'failure', 'r6', 'restored_fasls_equal') if k in report}), flush=True)
    return 0 if report['execution_status'] == 'PASS' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inputs', 'kernel', 'work', 'output'): parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--resume', action='store_true', help='Reuse the clean baseline of a failed, fully restored run.')
    args = parser.parse_args()
    def interrupted(signum, _): raise InterruptedError('signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    sys.exit(run(*(getattr(args, name).resolve() for name in ('inputs', 'kernel', 'work', 'output')), resume=args.resume))
