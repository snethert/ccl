#!/usr/bin/env python3
"""Run only the census description extension in a disposable pristine U1 copy."""
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
from analysis import HERE, ROOT, NATIVE_CONTROLS, check_descriptions, check_capture, project, check_projection
from controls import run as run_controls


def digest(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()


def save(p, data):
    raw = (json.dumps(data, indent=2, ensure_ascii=False)+'\n').encode()
    p.write_bytes(gzip.compress(raw, mtime=0) if p.suffix == '.gz' else raw)


def run(store, work, output):
    if platform.system() != 'Darwin' or platform.machine() != 'x86_64':
        raise ValueError('requires the macOS x86-64 reference host')
    for a, b in ((store, work), (store, output), (work, output)):
        if a == b or a in b.parents or b in a.parents: raise ValueError('separate directories required')
    work.mkdir(parents=True, exist_ok=False); output.mkdir(parents=True, exist_ok=False)
    record = dict(version=1, status='FAIL', review_disposition='NOT_REVIEWED', command=sys.argv,
                  timestamp=datetime.now(timezone.utc).isoformat(), commands=[])
    try:
        d = json.loads((HERE/'descriptions.json').read_text()); check_descriptions(d)
        save(output/'descriptions.json', d)
        pins = json.loads((HERE.parent/'source-traversal/inputs.json').read_text())
        record['pins'] = pins
        inputs = {k: store/v['path'] for k, v in pins['inputs'].items()}
        for k, p in inputs.items():
            if digest(p) != pins['inputs'][k]['sha256']: raise ValueError('direct input changed: '+k)
        sources = [HERE/p for p in ('descriptions.lisp', 'driver.lisp', 'descriptions.json',
                                    'analysis.py', 'controls.py', 'run.py', 'verify.py')]
        sources += [HERE.parent/p for p in ('observer.lisp', 'dependencies.lisp',
                    'source-traversal/driver.lisp', 'source-traversal/check.py', 'source-traversal/inputs.json')]
        sources += [ROOT/p for p in d['source_sha256']]
        record['source_sha256'] = {str(p.relative_to(ROOT)): digest(p) for p in sources}
        source = work/'ccl'; source.mkdir()
        for name in ('source', 'bootstrap'):
            with tarfile.open(inputs[name]) as f: f.extractall(source, filter='data')
        shutil.copyfile(inputs['kernel'], source/'dx86cl64'); (source/'dx86cl64').chmod(0o755)
        (source/'bin').mkdir(exist_ok=True)
        for name in ('architecture', 'backend'):
            shutil.copyfile(inputs[name], source/'bin'/inputs[name].name)
        for p, expected in d['source_sha256'].items():
            if digest(source/p) != expected: raise ValueError('archive source differs: '+p)
        binaries = {str(p.relative_to(source)): digest(p) for p in source.rglob('*.dx64fsl')}
        sessions = []
        for mode in ('normal', 'repeat', *NATIVE_CONTROLS):
            raw_path = work/(mode+'.json')
            env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin', LANG='C', LC_ALL='C',
                       CCL_DEFAULT_DIRECTORY=str(source), CCL_TRAVERSE_SOURCE=str(source/'lib/dumplisp.lisp'),
                       CCL_TRAVERSE_OUTPUT=str(raw_path), CCL_TRAVERSE_MODE='normal',
                       CCL_DESCRIPTION_MODE='normal' if mode == 'repeat' else mode)
            argv = [str(source/'dx86cl64'), '--image-name', str(inputs['image']), '--no-init', '--batch']
            for p in (HERE.parent/'observer.lisp', HERE.parent/'dependencies.lisp', inputs['registration']):
                argv += ['--load', str(p)]
            argv += ['--eval', '(dolist (name (quote (ccl::wasm-census-arch ccl::wasm-census-backend))) '
                     '(multiple-value-bind (binary sources) (ccl::find-module name (ccl::backend-name ccl::*host-backend*)) '
                     '(declare (ignore sources)) (load binary)))']
            for p in (HERE.parent/'source-traversal/driver.lisp', HERE/'descriptions.lisp', HERE/'driver.lisp'):
                argv += ['--load', str(p)]
            argv += ['--eval', '(progn (ccl-census-descriptions::run) (ccl:quit))']
            command = dict(mode=mode, argv=argv, environment=env, cwd=str(source), timeout_seconds=60)
            record['commands'].append(command)
            try:
                with (output/(mode+'.log')).open('wb') as log:
                    child = subprocess.Popen(argv, env=env, cwd=source, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                    try: code = child.wait(timeout=60)
                    except BaseException:
                        try: os.killpg(child.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                        child.wait(); raise
                command['exit_code'] = code
                if raw_path.exists():
                    raw = raw_path.read_bytes()
                    (output/(mode+'.json.gz')).write_bytes(gzip.compress(raw, mtime=0))
                    command['capture_sha256'] = hashlib.sha256(raw).hexdigest()
                if code or not raw_path.exists(): raise ValueError('native session failed: '+mode)
                capture = json.loads(raw)
                if mode in ('normal', 'repeat'):
                    counts = check_capture(capture, (source/'lib/dumplisp.lisp').read_bytes(), d)
                    if mode == 'normal': normal, original = capture, raw
                    elif raw != original: raise ValueError('native reproduction differs')
                    sessions.append(dict(mode=mode, status='PASS'))
                else:
                    try: check_capture(capture, (source/'lib/dumplisp.lisp').read_bytes(), d)
                    except ValueError as e:
                        if str(e) != NATIVE_CONTROLS[mode]: raise ValueError('unexpected rejection: '+mode+': '+str(e))
                        sessions.append(dict(mode=mode, status='REJECTED', reason=str(e)))
                    else: raise ValueError('native control escaped: '+mode)
            finally: save(output/'commands.json', record['commands'])
        facts = project(normal, d); check_projection(facts, normal, d)
        controls = run_controls(normal, facts, d, (source/'lib/dumplisp.lisp').read_bytes())
        save(output/'facts.json.gz', facts); save(output/'controls.json', controls)
        for p, expected in d['source_sha256'].items():
            if digest(source/p) != expected: raise ValueError('source modified: '+p)
        if binaries != {str(p.relative_to(source)): digest(p) for p in source.rglob('*.dx64fsl')} or list(source.rglob('*.census-no-code')):
            raise ValueError('FASL output changed')
        save(output/'summary.json', dict(version=1, status='TRAVERSED_WITH_EXPLICIT_GAPS',
             review_disposition='NOT_REVIEWED', **counts, analysis_controls_rejected=controls['controls_rejected'],
             native_controls_rejected=len(NATIVE_CONTROLS), sessions=sessions, native_reproduction_equal=True,
             source_unchanged=True, fasls_unchanged=True, macro_environment_qualified=False,
             graph_edges_replaced=0, census_acceptance='BLOCKED'))
        (output/'repeat.json.gz').unlink()
        record.update(status='PASS', artifacts=[dict(path=p.name, bytes=p.stat().st_size, sha256=digest(p))
                      for p in sorted(output.iterdir()) if p.name != 'run.json'])
        print(json.dumps(json.loads((output/'summary.json').read_text()), indent=2))
    except BaseException as e:
        record['error'] = type(e).__name__+': '+str(e); raise
    finally: save(output/'run.json', record)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('evidence-root', 'work', 'output'): p.add_argument('--'+name, required=True, type=Path)
    a = p.parse_args(); run(a.evidence_root.resolve(), a.work.resolve(), a.output.resolve())
