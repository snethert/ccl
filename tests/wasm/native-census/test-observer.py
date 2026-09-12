#!/usr/bin/env python3
"""Inject observer omissions in real native probe runs; retain every rejection."""
import argparse
import collections
import json
import os
from pathlib import Path
import shutil
import subprocess
from analyze import read_events, snapshot
from reversible import digest, save

HERE = Path(__file__).resolve().parent


def check_probe(events):
    snapshot(events)
    for kind in ['read', 'macroexpand', 'frontend', 'before-pass2', 'compile-initializer-enter',
                 'compile-initializer-return', 'load-initializer-emitted']:
        if not any(e['kind'] == kind for e in events): raise ValueError('missing phase: ' + kind)
    functions = {e['payload']['name']: e['payload'] for e in events if e['kind'] == 'before-pass2'}
    for name in ['LEAF', 'PARENT', 'INDIRECT', 'VALUES']:
        if 'COMMON-LISP-USER::CENSUS-PROBE-' + name not in functions:
            raise ValueError('missing independently named function: ' + name)
    if not any(c['target'] == 'COMMON-LISP-USER::CENSUS-PROBE-LEAF'
               for c in functions['COMMON-LISP-USER::CENSUS-PROBE-PARENT']['calls']):
        raise ValueError('required direct dependency missing')
    if not any(c['target'] is None for c in functions['COMMON-LISP-USER::CENSUS-PROBE-INDIRECT']['calls']):
        raise ValueError('unknown indirect call hidden')


def run(run_root, work, output):
    run_root, work, output = [p.resolve() for p in (run_root, work, output)]
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()): raise ValueError('control evidence must be new')
    source = work / 'ccl'; image = run_root / 'observed/build/dx86cl64.image'
    kernel = source / 'dx86cl64'
    shutil.copytree(HERE, output / 'runner', ignore=shutil.ignore_patterns('__pycache__'))
    fixture = output / 'runner'; probe = work / 'observer-control-probe.lisp'
    shutil.copyfile(fixture / 'probe.lisp', probe)
    # These edit only generated observer records. Native source and acode are
    # untouched, and every variant must still execute the original probe.
    helper = '''
      (defun census-field-tail (object key)
        (loop for tail on (cdr object) by #'cddr
              when (string= (car tail) key) return (cdr tail)))
    '''
    mutations = {
        'positive': '',
        'missing-pass2': '(when (string= kind "before-pass2") (return-from injected nil))',
        'missing-parent': '''(when (and (string= kind "before-pass2")
          (string= (car (census-field-tail payload "name")) "COMMON-LISP-USER::CENSUS-PROBE-PARENT"))
          (return-from injected nil))''',
        'hidden-unknown-call': '''(when (string= kind "before-pass2")
          (dolist (call (car (census-field-tail payload "calls")))
            (let ((target (census-field-tail call "target")))
              (when (eq (car target) :null) (setf (car target) "FABRICATED-CALLEE")))))''',
        'missing-reserved-slot': '''(when (string= kind "snapshot")
          (let ((ops (census-field-tail payload "operators")))
            (setf (car ops) (remove-if (lambda (o) (eq (car (census-field-tail o "name")) :null))
                                       (car ops) :count 1))))''',
        'corrupt-operator-flags': '''(when (string= kind "snapshot")
          (let* ((op (second (car (census-field-tail payload "operators"))))
                 (flags (census-field-tail op "flags"))) (incf (car flags))))''',
        'missing-completion': '(when (string= kind "complete") (return-from injected nil))'
    }
    results = []; expected_fasl = None
    for name, mutation in mutations.items():
        out = output / name; out.mkdir()
        inject = '' if not mutation else '''(let ((original (symbol-function 'ccl-startup-census::emit)))
          (setf (symbol-function 'ccl-startup-census::emit)
                (lambda (kind payload) (block injected ''' + mutation + ''' (funcall original kind payload)))))'''
        expr = '(progn ' + helper + inject + ''' (ccl-startup-census::start)
          (let ((*gensym-counter* 100000)) (load (compile-file ''' + json.dumps(str(probe)) + ''')))
          (assert (= 10 (cl-user::census-probe-parent 4)))
          (assert (= 14 (cl-user::census-probe-indirect #'cl-user::census-probe-leaf 7)))
          (assert (equal (multiple-value-list (cl-user::census-probe-values 7)) (list 7 8 -7)))
          (ccl-startup-census::finish) (format t "OBSERVER-CONTROL-COMPLETE~%") (ccl:quit))'''
        cmd = [str(kernel), '--image-name', str(image), '--no-init', '--batch',
               '--load', str(fixture / 'observer.lisp'), '--eval', expr]
        env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'C', 'LC_ALL': 'C',
               'CCL_DEFAULT_DIRECTORY': str(source), 'CCL_CENSUS_EVENTS': str(out / 'events.jsonl')}
        with (out / 'native.log').open('wb') as log:
            p = subprocess.run(cmd, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=45)
        if p.returncode or 'OBSERVER-CONTROL-COMPLETE' not in (out / 'native.log').read_text():
            raise ValueError('control native execution failed: ' + name)
        fasl = probe.with_suffix('.dx64fsl'); h = digest(fasl)
        if expected_fasl is None: expected_fasl = h
        if h != expected_fasl: raise ValueError('observer mutant changed native probe output: ' + name)
        shutil.copyfile(fasl, out / 'probe.dx64fsl')
        reason = None
        try: check_probe(read_events(out / 'events.jsonl'))
        except ValueError as exc: reason = str(exc)
        if (name == 'positive') != (reason is None): raise ValueError('unexpected oracle result: ' + name)
        results.append({'name': name, 'status': 'PASS' if reason is None else 'REJECTED',
                        'reason': reason, 'command': cmd, 'environment': env,
                        'native_exit_code': p.returncode, 'fasl_sha256': h})
        save(output / 'results.json', {'status': 'IN_PROGRESS', 'cases': results})
    save(output / 'results.json', {'status': 'PASS', 'cases': results,
        'scope': 'Real native observer omission/corruption controls; no complete census/closure claim',
        'inputs_sha256': {str(p): digest(p) for p in
                         [image, kernel, fixture / 'observer.lisp', fixture / 'probe.lisp', run_root / 'results.json']},
        'native_probe_fasl_identical_across_all_cases': expected_fasl})
    print(json.dumps({'status': 'PASS', 'positive': 1, 'rejected': len(results) - 1}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for f in ['run', 'work', 'output']: p.add_argument('--' + f, required=True, type=Path)
    a = p.parse_args(); run(a.run, a.work, a.output)
