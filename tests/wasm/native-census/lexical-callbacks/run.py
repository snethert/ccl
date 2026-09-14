#!/usr/bin/env python3
"""Capture lexical callback bindings in two source expanders without changing compiler IR."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
from analysis import HERE, ROOT, check, controls, joins, read, require
sys.path.insert(0, str(HERE.parent/'source-expanders'))
spec = importlib.util.spec_from_file_location('previous_runner', HERE.parent/'source-expanders/run.py')
previous = importlib.util.module_from_spec(spec); spec.loader.exec_module(previous)
digest, save = previous.digest, previous.save


NATIVE_SOURCES = ('compiler/arch.lisp', 'compiler/X86/X8632/x8632-arch.lisp',
                  'compiler/X86/X8664/x8664-arch.lisp', 'level-1/l1-typesys.lisp', 'lib/setf.lisp', 'level-1/l1-utils.lisp', 'level-1/l1-clos-boot.lisp', 'compiler/nxenv.lisp')
LOADS = ('source-traversal/driver.lisp', 'target-descriptions/descriptions.lisp',
    'target-descriptions/driver.lisp', 'target-macros/driver.lisp', 'source-expanders/driver.lisp',
    'source-expanders/selection.lisp', 'target-helpers/driver.lisp', 'target-types/driver.lisp',
    'target-predicates/driver.lisp', 'target-aliases/driver.lisp', 'target-dispatch/driver.lisp', 'target-setf/driver.lisp', 'lexical-callbacks/driver.lisp')


def sources():
    result = previous.sources()
    for p in [HERE/n for n in ('driver.lisp', 'analysis.py', 'run.py')] + [
            *(HERE.parent/n for n in LOADS), HERE.parent/'target-setf/analysis.py', *(ROOT/n for n in NATIVE_SOURCES)]:
        result[str(p.relative_to(ROOT))] = digest(p)
    return result


def run(store, work, out):
    require((platform.system(), platform.machine()) == ('Darwin', 'x86_64'), 'MACOS_REFERENCE_REQUIRED')
    require(all(p != ROOT and ROOT not in p.parents for p in (work,out)), 'DISPOSABLE_PATHS_REQUIRED')
    for a, b in ((store, work), (store, out), (work, out)):
        require(a != b and a not in b.parents and b not in a.parents, 'SEPARATE_PATHS')
    work.mkdir(parents=True, exist_ok=False); out.mkdir(parents=True, exist_ok=False)
    record = dict(version=1, status='FAIL', argv=sys.argv, timestamp=datetime.now(timezone.utc).isoformat(),
                  review_disposition='NOT_REVIEWED', source_sha256=sources(), commands=[])
    try:
        (out/'source').mkdir()
        for name in ('driver.lisp', 'analysis.py', 'run.py'): shutil.copyfile(HERE/name, out/'source'/name)
        pins = read(HERE.parent/'source-traversal/inputs.json'); record['pins'] = pins
        inputs = {k: store/v['path'] for k, v in pins['inputs'].items()}
        for k, p in inputs.items(): require(digest(p) == pins['inputs'][k]['sha256'], 'INPUT '+k)
        source = work/'ccl'; source.mkdir()
        for name in ('source', 'bootstrap'):
            with tarfile.open(inputs[name]) as f: f.extractall(source, filter='data')
        shutil.copyfile(inputs['kernel'], source/'dx86cl64'); (source/'dx86cl64').chmod(0o755)
        (source/'bin').mkdir(exist_ok=True)
        for name in ('architecture', 'backend'): shutil.copyfile(inputs[name], source/'bin'/inputs[name].name)
        native_pins = read(HERE.parent/'source-expanders/source-inputs.json')
        for path in NATIVE_SOURCES:
            native_pins[path] = digest(ROOT/path)
        for path, expected in native_pins.items(): require(digest(source/path) == expected and digest(ROOT/path) == expected, 'U1_SOURCE '+path)
        binaries = {str(p.relative_to(source)): digest(p) for p in source.rglob('*.dx64fsl')}
        outcomes = []
        for mode in ('normal', 'repeat'):
            env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin', LANG='C', LC_ALL='C',
                       CCL_DEFAULT_DIRECTORY=str(source), CCL_TRAVERSE_SOURCE=str(source/'lib/dumplisp.lisp'),
                       CCL_TRAVERSE_OUTPUT=str(work/(mode+'-traversal.json')), CCL_SETF_OUTPUT=str(work/(mode+'-setf.json')),
                       CCL_SETF_MODE='normal', CCL_FLOW_OUTPUT=str(work/(mode+'-flow.json')), CCL_TRAVERSE_MODE='normal', CCL_DESCRIPTION_MODE='normal')
            argv = [str(source/'dx86cl64'), '--image-name', str(inputs['image']), '--no-init', '--batch']
            for p in (HERE.parent/'observer.lisp', HERE.parent/'dependencies.lisp', inputs['registration']): argv += ['--load', str(p)]
            argv += ['--eval', '(dolist (name (quote (ccl::wasm-census-arch ccl::wasm-census-backend))) '
                '(multiple-value-bind (binary sources) (ccl::find-module name (ccl::backend-name ccl::*host-backend*)) '
                '(declare (ignore sources)) (load binary)))']
            for name in LOADS: argv += ['--load', str(HERE.parent/name)]
            argv += ['--eval', '(progn (ccl-lexical-callbacks::run) (ccl:quit))']
            command = dict(mode=mode, argv=argv, environment=env, cwd=str(source), timeout_seconds=60)
            record['commands'].append(command)
            with (out/(mode+'.log')).open('wb') as log:
                child = subprocess.Popen(argv, env=env, cwd=source, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                try: command['exit_code'] = child.wait(timeout=60)
                except BaseException:
                    try: os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    child.wait(); raise
            captured = {}
            for kind in ('flow', 'setf', 'traversal'):
                p = work/(mode+'-'+kind+'.json')
                if p.exists():
                    captured[kind] = p.read_bytes()
                    (out/(mode+'-'+kind+'.json.gz')).write_bytes(gzip.compress(captured[kind], mtime=0))
            command['capture_sha256'] = {k: hashlib.sha256(v).hexdigest() for k, v in captured.items()}
            save(out/'commands.json', record['commands'])
            require(command['exit_code'] == 0 and len(captured) == 3, 'NATIVE_SESSION '+mode)
            c = {k:json.loads(v) for k,v in captured.items()}; t = c['traversal']
            counts = check(c, t)
            if mode == 'normal': original, normal, traversal = captured, c, t
            else: require(captured == original, 'REPRODUCTION')
            outcomes.append(dict(mode=mode, status='PASS'))
        checks = controls(normal, traversal); save(out/'controls.json', checks); save(out/'joins.json', joins(normal))
        for path, expected in native_pins.items(): require(digest(source/path) == expected, 'SOURCE_MODIFIED '+path)
        require(binaries == {str(p.relative_to(source)): digest(p) for p in source.rglob('*.dx64fsl')} and
                not list(source.rglob('*.census-no-code')), 'FASL_CHANGED')
        require(record['source_sha256'] == sources(), 'TOOL_SOURCE_CHANGED')
        save(out/'summary.json', dict(version=1, status='TWO_LEXICAL_CALLBACK_BOUNDS', review_disposition='NOT_REVIEWED',
             **counts, checker_controls_rejected=len(checks),
             source_reproduction_byte_identical=True, 
             source_unchanged=True, fasls_unchanged=True, gate_credit=False, sessions=outcomes))
        for kind in ('flow', 'setf', 'traversal'): (out/('repeat-'+kind+'.json.gz')).unlink()
        record.update(status='PASS', artifacts=[dict(path=p.relative_to(out).as_posix(), bytes=p.stat().st_size, sha256=digest(p))
                      for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'run.json'])
        print('PASS: two lexical callback bounds, eight target-front-end probes, 21 rejected checker mutations; unchanged source and FASLs. No gate credit.')
    except BaseException as e:
        record['error'] = type(e).__name__+': '+str(e); raise
    finally: save(out/'run.json', record)


def verify(packet):
    record = read(packet/'run.json'); require(record['status'] == 'PASS', 'RUN_STATUS')
    for path, expected in record['source_sha256'].items(): require(digest(ROOT/path) == expected, 'SOURCE_PIN '+path)
    for a in record['artifacts']: require(digest(packet/a['path']) == a['sha256'], 'ARTIFACT '+a['path'])
    c = {k:read(packet/('normal-'+k+'.json.gz')) for k in ('flow', 'setf', 'traversal')}; t = c['traversal']
    counts = check(c, t); s = read(packet/'summary.json'); require(all(s[k] == v for k, v in counts.items()), 'SUMMARY')
    require(controls(c, t) == read(packet/'controls.json'), 'CONTROLS')
    require([r['mode'] for r in record['commands']] == ['normal', 'repeat'] and
            all(r['exit_code'] == 0 for r in record['commands']), 'SESSION_BOUND')
    commands = {r['mode']: r for r in record['commands']}
    require(commands['normal']['capture_sha256'] == commands['repeat']['capture_sha256'], 'REPEAT_IDENTITY')
    require(joins(c) == read(packet/'joins.json'), 'JOINS')
    print('PASS: two source callback bounds, eight target-front-end probes, checker controls and direct pins.')



if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify', type=Path)
    for name in ('evidence-root', 'work', 'output'): p.add_argument('--'+name, type=Path)
    a = p.parse_args()
    if a.verify: verify(a.verify.resolve())
    else:
        if not all((a.evidence_root, a.work, a.output)): p.error('run requires --evidence-root, --work and --output')
        run(a.evidence_root.resolve(), a.work.resolve(), a.output.resolve())
