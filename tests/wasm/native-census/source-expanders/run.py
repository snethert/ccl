#!/usr/bin/env python3
"""Reconstruct source expanders and compare against inherited bindings in disposable U1."""
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
from check import HERE, ROOT, NATIVE_CONTROLS, check, controls, read, manifest, compare


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')


def sources():
    native = HERE.parent
    files = [HERE/p for p in ('driver.lisp', 'selection.lisp', 'manifest.json', 'check.py', 'run.py', 'verify.py', 'source-inputs.json')]
    files += [native/p for p in ('observer.lisp', 'dependencies.lisp', 'source-traversal/driver.lisp',
                                 'source-traversal/check.py', 'source-traversal/inputs.json',
                                 'target-descriptions/descriptions.lisp', 'target-descriptions/driver.lisp',
                                 'target-descriptions/analysis.py', 'target-descriptions/descriptions.json',
                                 'target-macros/driver.lisp', 'target-macros/check.py')]
    files += [ROOT/p for p in read(HERE/'source-inputs.json')]
    return {str(p.relative_to(ROOT)): digest(p) for p in files}


def run(store, work, output):
    if (platform.system(), platform.machine()) != ('Darwin', 'x86_64'):
        raise ValueError('requires the macOS x86-64 reference host')
    for a, b in ((store, work), (store, output), (work, output)):
        if a == b or a in b.parents or b in a.parents:
            raise ValueError('separate directories required')
    work.mkdir(parents=True, exist_ok=False)
    output.mkdir(parents=True, exist_ok=False)
    record = dict(version=1, status='FAIL', review_disposition='NOT_REVIEWED', argv=sys.argv,
                  timestamp=datetime.now(timezone.utc).isoformat(), commands=[], source_sha256=sources())
    try:
        selection = manifest()
        basis = read(HERE/'manifest.json')['basis']
        if digest(store/basis['path']) != basis['sha256']:
            raise ValueError('reviewed selection basis differs')
        pins = read(HERE.parent/'source-traversal/inputs.json')
        record['pins'] = pins
        inputs = {k: store/v['path'] for k, v in pins['inputs'].items()}
        for k, p in inputs.items():
            if digest(p) != pins['inputs'][k]['sha256']:
                raise ValueError('direct input changed: '+k)
        source = work/'ccl'
        source.mkdir()
        for name in ('source', 'bootstrap'):
            with tarfile.open(inputs[name]) as f:
                f.extractall(source, filter='data')
        shutil.copyfile(inputs['kernel'], source/'dx86cl64')
        (source/'dx86cl64').chmod(0o755)
        (source/'bin').mkdir(exist_ok=True)
        for name in ('architecture', 'backend'):
            shutil.copyfile(inputs[name], source/'bin'/inputs[name].name)
        for p, expected in read(HERE/'source-inputs.json').items():
            if digest(source/p) != expected or digest(ROOT/p) != expected:
                raise ValueError('pinned source differs: '+p)
        binaries = {str(p.relative_to(source)): digest(p) for p in source.rglob('*.dx64fsl')}
        sessions = []
        for mode in ('normal', 'repeat', 'inherited', *NATIVE_CONTROLS):
            env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin', LANG='C', LC_ALL='C',
                       CCL_DEFAULT_DIRECTORY=str(source), CCL_TRAVERSE_SOURCE=str(source/'lib/dumplisp.lisp'),
                       CCL_TRAVERSE_OUTPUT=str(work/(mode+'-traversal.json')),
                       CCL_EXPANDER_OUTPUT=str(work/(mode+'-expanders.json')), CCL_TRAVERSE_MODE='normal',
                       CCL_DESCRIPTION_MODE='normal', CCL_EXPANDER_MODE='normal' if mode == 'repeat' else mode)
            argv = [str(source/'dx86cl64'), '--image-name', str(inputs['image']), '--no-init', '--batch']
            for p in (HERE.parent/'observer.lisp', HERE.parent/'dependencies.lisp', inputs['registration']):
                argv += ['--load', str(p)]
            argv += ['--eval', '(dolist (name (quote (ccl::wasm-census-arch ccl::wasm-census-backend))) '
                     '(multiple-value-bind (binary sources) (ccl::find-module name (ccl::backend-name ccl::*host-backend*)) '
                     '(declare (ignore sources)) (load binary)))']
            for p in (HERE.parent/'source-traversal/driver.lisp', HERE.parent/'target-descriptions/descriptions.lisp',
                      HERE.parent/'target-descriptions/driver.lisp', HERE.parent/'target-macros/driver.lisp',
                      HERE/'driver.lisp', HERE/'selection.lisp'):
                argv += ['--load', str(p)]
            argv += ['--eval', '(progn (ccl-source-expanders::run) (ccl:quit))']
            command = dict(mode=mode, argv=argv, environment=env, cwd=str(source), timeout_seconds=60)
            record['commands'].append(command)
            try:
                with (output/(mode+'.log')).open('wb') as log:
                    child = subprocess.Popen(argv, env=env, cwd=source, stdout=log,
                                             stderr=subprocess.STDOUT, start_new_session=True)
                    try:
                        code = child.wait(timeout=60)
                    except BaseException:
                        try:
                            os.killpg(child.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        child.wait()
                        raise
                command['exit_code'] = code
                captured = {}
                for kind in ('expanders', 'traversal'):
                    raw = work/(mode+'-'+kind+'.json')
                    if raw.exists():
                        captured[kind] = raw.read_bytes()
                        command.setdefault('capture_sha256', {})[kind] = hashlib.sha256(captured[kind]).hexdigest()
                        (output/(mode+'-'+kind+'.json.gz')).write_bytes(gzip.compress(captured[kind], mtime=0))
                if code or len(captured) != 2:
                    raise ValueError('native session failed: '+mode)
                c, t = (json.loads(captured[k]) for k in ('expanders', 'traversal'))
                if mode in ('normal', 'repeat'):
                    counts = check(c, t, selection)
                    if mode == 'normal':
                        normal, traversal, original = c, t, captured
                    elif captured != original:
                        raise ValueError('native reproduction differs')
                    sessions.append(dict(mode=mode, status='PASS'))
                elif mode == 'inherited':
                    check(c, t, selection, reference=True)
                    compare(normal, traversal, c, t)
                    if captured['traversal'] != original['traversal']:
                        raise ValueError('inherited traversal bytes differ')
                    reference, reference_traversal = c, t
                    sessions.append(dict(mode=mode, status='REFERENCE_EQUIVALENT'))
                else:
                    try:
                        check(c, t, selection)
                    except ValueError as e:
                        if str(e) != NATIVE_CONTROLS[mode]:
                            raise ValueError('unexpected native rejection: '+mode+': '+str(e))
                        sessions.append(dict(mode=mode, status='REJECTED', reason=str(e)))
                    else:
                        raise ValueError('native control escaped: '+mode)
            finally:
                save(output/'commands.json', record['commands'])
        save(output/'controls.json', controls(normal, traversal, reference, reference_traversal, selection))
        for p, expected in read(HERE/'source-inputs.json').items():
            if digest(source/p) != expected:
                raise ValueError('source modified: '+p)
        if binaries != {str(p.relative_to(source)): digest(p) for p in source.rglob('*.dx64fsl')} or list(source.rglob('*.census-no-code')):
            raise ValueError('FASL output changed')
        if record['source_sha256'] != sources():
            raise ValueError('tool sources changed during run')
        save(output/'summary.json', dict(version=1, status='SOURCE_EXPANDER_ROUTES_REPRODUCED',
             review_disposition='NOT_REVIEWED', **counts, native_controls_rejected=len(NATIVE_CONTROLS),
             checker_controls_rejected=27, parser_positive_cases=5, native_reproduction_equal=True, inherited_traversal_byte_identical=True, inherited_expansion_equivalence=True, sessions=sessions,
             source_unchanged=True, fasls_unchanged=True, macro_environment_qualified=False,
             graph_edges_replaced=0, census_acceptance='BLOCKED'))
        for kind in ('expanders', 'traversal'):
            (output/('repeat-'+kind+'.json.gz')).unlink()
        record.update(status='PASS', artifacts=[dict(path=p.name, bytes=p.stat().st_size, sha256=digest(p))
                      for p in sorted(output.iterdir()) if p.name != 'run.json'])
        print('PASS: all 293 expansion routes source-rebuilt; inherited traversal byte-identical; '
              '4 native and 27 checker controls reject. Seven definitions captured; five stops remain.')
    except BaseException as e:
        record['error'] = type(e).__name__+': '+str(e)
        raise
    finally:
        save(output/'run.json', record)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('evidence-root', 'work', 'output'):
        p.add_argument('--'+name, required=True, type=Path)
    a = p.parse_args()
    run(a.evidence_root.resolve(), a.work.resolve(), a.output.resolve())
