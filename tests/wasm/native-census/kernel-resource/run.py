#!/usr/bin/env python3
"""Qualify one explicit startup source replacement in a disposable U1 copy."""
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
from analysis import HERE, ROOT, check, controls, joins, read, require


# Each edit changes the service body, never the caller or expected values.
MUTANTS = {
    'missing-ready-guard': ('  (unless *kernel-resource-ready*\n    (error "KERNEL-RESOURCE-NOT-INSTALLED"))\n', '', 'before-install'),
    'input-alias': ('(copy-seq resource)', 'resource', 'caller-input-mutated'),
    'output-alias': ('(copy-seq *kernel-resource-name*)', '*kernel-resource-name*', 'returned-string-mutated'),
    'reinstall': ('  (when *kernel-resource-ready*\n    (error "KERNEL-RESOURCE-ALREADY-INSTALLED"))\n', '', 'second-install'),
    'missing-string-test': ('(stringp resource)', 't', 'invalid-number'),
    'empty-name': ('(plusp (length resource))', 't', 'invalid-empty'),
    'nul-name': ('(not (find (code-char 0) resource))', 't', 'invalid-nul'),
    'premature-ready': ('  (unless (and', '  (setq *kernel-resource-ready* t)\n  (unless (and', 'invalid-number'),
}


def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def save(p, data):
    raw = (json.dumps(data, indent=2, ensure_ascii=False)+'\n').encode()
    p.write_bytes(gzip.compress(raw, mtime=0) if p.suffix == '.gz' else raw)


def mutant(text, name):
    old, new, _ = MUTANTS[name]
    require(text.count(old) == 1, 'MUTANT_SITE '+name)
    return text.replace(old, new)


def assess_mutant(capture, normal, name, service):
    require({k:v for k,v in capture.items() if k not in ('service_text', 'reference_cases')} ==
            {k:v for k,v in normal.items() if k not in ('service_text', 'reference_cases')}, 'MUTANT_CONTAINMENT '+name)
    try:
        check(capture, service)
    except ValueError as e:
        require(str(e) == 'REFERENCE_CASE '+MUTANTS[name][2], 'MUTANT_REASON '+name+': '+str(e))
        return dict(mode=name, status='REJECTED', reason=str(e))
    raise ValueError('MUTANT_ESCAPED '+name)


def artifacts(output):
    return [dict(path=str(p.relative_to(output)), bytes=p.stat().st_size, sha256=digest(p))
            for p in sorted(output.rglob('*')) if p.is_file() and p != output/'run.json']


def run(store, work, output):
    require(platform.system() == 'Darwin' and platform.machine() == 'x86_64', 'MACOS_X86_64_REFERENCE_REQUIRED')
    for a, b in ((store, work), (store, output), (work, output)):
        require(a != b and a not in b.parents and b not in a.parents, 'SEPARATE_DIRECTORIES_REQUIRED')
    work.mkdir(parents=True, exist_ok=False)
    output.mkdir(parents=True, exist_ok=False)
    record = dict(version=1, status='FAIL', review_disposition='NOT_REVIEWED', command=sys.argv,
                  timestamp=datetime.now(timezone.utc).isoformat(), commands=[])
    try:
        sources = [HERE/name for name in ('run.py', 'analysis.py', 'driver.lisp', 'contract.json', 'replacement.lisp', 'service.lisp')]
        (output/'source').mkdir()
        for p in sources:
            shutil.copyfile(p, output/'source'/p.name)
        descriptions = read(HERE.parent/'target-descriptions/descriptions.json')
        sources += [HERE.parent/p for p in ('observer.lisp', 'dependencies.lisp', 'source-traversal/inputs.json',
                    'source-traversal/driver.lisp', 'source-traversal/check.py', 'target-descriptions/descriptions.lisp',
                    'target-descriptions/descriptions.json', 'target-macros/driver.lisp')]
        sources += [ROOT/p for p in descriptions['source_sha256']]
        sources.append(ROOT/'lib/macros.lisp')
        record['source_sha256'] = {str(p.relative_to(ROOT)): digest(p) for p in sources}
        pins = read(HERE.parent/'source-traversal/inputs.json')
        record['pins'] = pins
        inputs = {k: store/v['path'] for k,v in pins['inputs'].items()}
        for k, p in inputs.items():
            require(digest(p) == pins['inputs'][k]['sha256'], 'DIRECT_INPUT_CHANGED '+k)
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
        for p, expected in descriptions['source_sha256'].items():
            require(digest(source/p) == expected, 'ARCHIVE_SOURCE_CHANGED '+p)
        binaries = {str(p.relative_to(source)): digest(p) for p in source.rglob('*.dx64fsl')}
        original_service = (HERE/'service.lisp').read_text()
        (output/'mutants').mkdir()
        sessions = []
        for mode in ('normal', 'repeat', *MUTANTS):
            service = HERE/'service.lisp'
            if mode in MUTANTS:
                service = output/'mutants'/(mode+'.lisp')
                service.write_text(mutant(original_service, mode))
            raw_path = work/(mode+'.json')
            env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin', LANG='C', LC_ALL='C',
                       CCL_DEFAULT_DIRECTORY=str(source), CCL_TRAVERSE_SOURCE=str(source/'lib/dumplisp.lisp'),
                       CCL_TRAVERSE_MODE='normal', CCL_DESCRIPTION_MODE='normal',
                       CCL_RESOURCE_REPLACEMENT=str(HERE/'replacement.lisp'), CCL_RESOURCE_SERVICE=str(service),
                       CCL_RESOURCE_OUTPUT=str(raw_path))
            argv = [str(source/'dx86cl64'), '--image-name', str(inputs['image']), '--no-init', '--batch']
            for p in (HERE.parent/'observer.lisp', HERE.parent/'dependencies.lisp', inputs['registration']):
                argv += ['--load', str(p)]
            argv += ['--eval', '(dolist (name (quote (ccl::wasm-census-arch ccl::wasm-census-backend))) '
                     '(multiple-value-bind (binary sources) (ccl::find-module name (ccl::backend-name ccl::*host-backend*)) '
                     '(declare (ignore sources)) (load binary)))']
            for p in (HERE.parent/'source-traversal/driver.lisp', HERE.parent/'target-descriptions/descriptions.lisp',
                      HERE.parent/'target-macros/driver.lisp', HERE/'driver.lisp'):
                argv += ['--load', str(p)]
            argv += ['--eval', '(progn (ccl-kernel-resource::run) (ccl:quit))']
            command = dict(mode=mode, argv=argv, environment=env, cwd=str(source), timeout_seconds=60)
            record['commands'].append(command)
            try:
                with (output/(mode+'.log')).open('wb') as log:
                    child = subprocess.Popen(argv, env=env, cwd=source, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
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
                if raw_path.exists():
                    raw = raw_path.read_bytes()
                    (output/(mode+'.json.gz')).write_bytes(gzip.compress(raw, mtime=0))
                    command['capture_sha256'] = hashlib.sha256(raw).hexdigest()
                require(code == 0 and raw_path.exists(), 'NATIVE_SESSION_FAILED '+mode)
                require('KERNEL-RESOURCE-COMPLETE 14' in (output/(mode+'.log')).read_text(), 'NATIVE_COMPLETION '+mode)
                capture = json.loads(raw)
                if mode in ('normal', 'repeat'):
                    counts = check(capture)
                    if mode == 'normal':
                        normal, original = capture, raw
                    else:
                        require(raw == original, 'NATIVE_REPRODUCTION_DIFFERS')
                    sessions.append(dict(mode=mode, status='PASS'))
                else:
                    sessions.append(assess_mutant(capture, normal, mode, service.read_text()))
            finally:
                save(output/'commands.json', record['commands'])
        save(output/'joins.json', joins(normal))
        checked = controls(normal)
        save(output/'controls.json', checked)
        for p, expected in descriptions['source_sha256'].items():
            require(digest(source/p) == expected, 'SOURCE_MODIFIED '+p)
        require(binaries == {str(p.relative_to(source)): digest(p) for p in source.rglob('*.dx64fsl')}
                and not list(source.rglob('*.census-no-code')), 'FASL_OUTPUT_CHANGED')
        save(output/'summary.json', dict(version=1, status='SOURCE_REPLACEMENT_AND_NATIVE_REFERENCE_QUALIFIED',
             review_disposition='NOT_REVIEWED', **counts, analysis_controls_rejected=len(checked),
             native_controls_rejected=len(MUTANTS), sessions=sessions, native_reproduction_equal=True,
             source_unchanged=True, fasls_unchanged=True, graph_edges_replaced=0, census_acceptance='BLOCKED'))
        record['status'] = 'PASS'
        print(f'PASS: one target source replacement, 14 reference cases, 8 native mutants and {len(checked)} checker controls; no census gate credit')
    except BaseException as e:
        record['error'] = type(e).__name__+': '+str(e)
        raise
    finally:
        record['artifacts'] = artifacts(output)
        save(output/'run.json', record)


def verify(output):
    record = read(output/'run.json')
    require(record['status'] == 'PASS' and record['review_disposition'] == 'NOT_REVIEWED', 'RUN_STATUS')
    require(artifacts(output) == record['artifacts'], 'ARTIFACT_IDENTITIES')
    for p, expected in record['source_sha256'].items():
        require(digest(ROOT/p) == expected, 'SOURCE_IDENTITY '+p)
    require(record['pins'] == read(HERE.parent/'source-traversal/inputs.json'), 'INPUT_PINS')
    normal = read(output/'normal.json.gz')
    counts = check(normal)
    require((output/'normal.json.gz').read_bytes() == (output/'repeat.json.gz').read_bytes(), 'REPRODUCTION')
    sessions = [dict(mode=k, status='PASS') for k in ('normal', 'repeat')]
    service = (HERE/'service.lisp').read_text()
    for name in MUTANTS:
        changed = (output/'mutants'/(name+'.lisp')).read_text()
        require(changed == mutant(service, name), 'MUTANT_SOURCE '+name)
        sessions.append(assess_mutant(read(output/(name+'.json.gz')), normal, name, changed))
    checked = controls(normal)
    require(read(output/'controls.json') == checked and read(output/'joins.json') == joins(normal), 'DERIVED_RECORDS')
    summary = read(output/'summary.json')
    require(summary == dict(version=1, status='SOURCE_REPLACEMENT_AND_NATIVE_REFERENCE_QUALIFIED',
            review_disposition='NOT_REVIEWED', **counts, analysis_controls_rejected=len(checked),
            native_controls_rejected=len(MUTANTS), sessions=sessions, native_reproduction_equal=True,
            source_unchanged=True, fasls_unchanged=True, graph_edges_replaced=0, census_acceptance='BLOCKED'), 'SUMMARY')
    require(record['commands'] == read(output/'commands.json') and len(record['commands']) == len(sessions), 'COMMANDS')
    for command, session in zip(record['commands'], sessions):
        require(command['mode'] == session['mode'] and command['exit_code'] == 0, 'COMMAND_EXIT')
        raw = gzip.decompress((output/(session['mode']+'.json.gz')).read_bytes())
        require(hashlib.sha256(raw).hexdigest() == command['capture_sha256'], 'COMMAND_CAPTURE')
    print('PASS: retained sources, ten captures, reference cases, native mutants, joins and checker controls')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', type=Path)
    for name in ('evidence-root', 'work', 'output'):
        parser.add_argument('--'+name, type=Path)
    args = parser.parse_args()
    if args.verify:
        verify(args.verify.resolve())
    else:
        if not all((args.evidence_root, args.work, args.output)):
            parser.error('--evidence-root, --work and --output required')
        run(args.evidence_root.resolve(), args.work.resolve(), args.output.resolve())
