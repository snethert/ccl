#!/usr/bin/env python3
"""Run the census file sink in disposable U1 sessions; preserve each attempt."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
import platform
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LOADS = ('source-traversal/driver.lisp', 'target-descriptions/descriptions.lisp',
         'target-descriptions/driver.lisp', 'target-macros/driver.lisp',
         'source-expanders/driver.lisp', 'source-expanders/selection.lisp',
         'target-helpers/driver.lisp', 'target-types/driver.lisp',
         'target-predicates/driver.lisp', 'target-aliases/driver.lisp',
         'target-dispatch/driver.lisp', 'target-setf/driver.lisp',
         'lexical-callbacks/driver.lisp', 'source-closure/driver.lisp', 'source-closure/layout.lisp')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')


def prepare(store, work):
    if (platform.system(),platform.machine()) != ('Darwin','x86_64'):
        raise ValueError('MACOS_X86_64_REFERENCE_REQUIRED')
    if work == ROOT or ROOT in work.parents or work == store or store in work.parents:
        raise ValueError('DISPOSABLE_WORK_REQUIRED')
    work.mkdir(parents=True, exist_ok=False)
    pins = json.loads((HERE.parent/'source-traversal/inputs.json').read_text())['inputs']
    for p in pins.values():
        if digest(store/p['path']) != p['sha256']:
            raise ValueError('INPUT '+p['path'])
    source = work/'ccl'; source.mkdir()
    for name in ('source', 'bootstrap'):
        with tarfile.open(store/pins[name]['path']) as archive:
            archive.extractall(source, filter='data')
    shutil.copyfile(store/pins['kernel']['path'], source/'dx86cl64')
    (source/'dx86cl64').chmod(0o755)
    (source/'bin').mkdir(exist_ok=True)
    for name in ('architecture', 'backend'):
        p = store/pins[name]['path']
        shutil.copyfile(p, source/'bin'/p.name)
    save(work/'inputs.json', pins)
    save(work/'baseline.json', {str(p.relative_to(source)):digest(p) for p in sorted(source.rglob('*'))
                               if p.is_file()})


def session(store, work, out, filename, mode, timeout):
    if out == ROOT or ROOT in out.parents or out == work or out in work.parents or work in out.parents:
        raise ValueError('SEPARATE_OUTPUT_REQUIRED')
    out.mkdir(parents=True, exist_ok=False)
    pins = json.loads((work/'inputs.json').read_text())
    source = work/'ccl'
    paths = [HERE/'run.py', *(HERE.parent/n for n in LOADS)]
    record = dict(status='FAIL', timestamp=datetime.now(timezone.utc).isoformat(),
                  source_sha256={str(p.relative_to(ROOT)): digest(p) for p in paths},
                  input=str(filename), input_sha256=digest(filename), mode=mode)
    (out/'source').mkdir()
    for name in ('run.py', 'driver.lisp', 'layout.lisp'):
        shutil.copyfile(HERE/name, out/'source'/name)
    try:
        env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin', LANG='C', LC_ALL='C',
                   CCL_DEFAULT_DIRECTORY=str(source), CCL_CLOSURE_SOURCE=str(filename),
                   CCL_CLOSURE_OUTPUT=str(out/'capture.json'), CCL_CLOSURE_MODE=mode,
                   CCL_CLOSURE_CORPUS='yes' if filename==HERE/'corpus.lisp' else 'no')
        argv = [str(source/'dx86cl64'), '--image-name', str(store/pins['image']['path']), '--no-init', '--batch']
        if mode == 'native':
            record['native_environment_sha256'] = digest(source/'lib/x8664env.lisp')
            argv += ['--load', str(source/'lib/x8664env.lisp')]
        for p in (HERE.parent/'observer.lisp', HERE.parent/'dependencies.lisp', store/pins['registration']['path']):
            argv += ['--load', str(p)]
        argv += ['--eval', '(dolist (name (quote (ccl::wasm-census-arch ccl::wasm-census-backend))) '
                 '(multiple-value-bind (binary sources) '
                 '(ccl::find-module name (ccl::backend-name ccl::*host-backend*)) '
                 '(declare (ignore sources)) (load binary)))']
        for n in LOADS: argv += ['--load', str(HERE.parent/n)]
        argv += ['--eval', '(progn (ccl-source-closure::run) (ccl:quit))']
        record.update(argv=argv, environment=env, timeout_seconds=timeout)
        with (out/'command.log').open('wb') as log:
            child = subprocess.Popen(argv, env=env, cwd=source, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            try: record['exit_code'] = child.wait(timeout=timeout)
            except BaseException:
                try: os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                child.wait(); raise
        if record['exit_code'] != 0: raise ValueError('NATIVE_SESSION_FAILED')
        captured = (out/'capture.json').read_bytes()
        record['capture_sha256'] = hashlib.sha256(captured).hexdigest()
        result = json.loads(captured)
        record['read_inputs'] = []
        for entry in result.get('read_inputs',[]):
            p = Path(entry['filename'])
            record['read_inputs'].append(dict(**entry,sha256=digest(p)))
        # Read-only source observation cannot publish a target FASL, including
        # through a compiler effect that bypassed the normal outer caller.
        if list(source.rglob('*.census-no-code')): raise ValueError('TARGET_FASL_WRITTEN')
        record['status'] = 'EXECUTED'
        print(json.dumps(dict(status=result['status'], captures=len(result['captures']),
                              native_compilations=len(result.get('native_compilations',[])),
                              forms=len(result['forms']), problem=result['problem'])))
    except BaseException as e:
        record['error'] = type(e).__name__+': '+str(e)
        raise
    finally:
        if (out/'capture.json').exists():
            (out/'capture.json.gz').write_bytes(gzip.compress((out/'capture.json').read_bytes(), mtime=0))
            (out/'capture.json').unlink()
        save(out/'run.json', record)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence-root', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--prepare', action='store_true')
    p.add_argument('--output', type=Path)
    p.add_argument('--source', type=Path, default=HERE/'corpus.lisp')
    p.add_argument('--mode', default='normal')
    p.add_argument('--timeout', type=int, default=90)
    a = p.parse_args()
    if a.prepare: prepare(a.evidence_root.resolve(), a.work.resolve())
    else:
        if not a.output: p.error('--output required')
        session(a.evidence_root.resolve(), a.work.resolve(), a.output.resolve(), a.source.resolve(), a.mode, a.timeout)
