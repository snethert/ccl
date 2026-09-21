"""Mechanical integration of audit 148's reviewed dispatcher additions.

The retained proposal is the input, independently of the shared compiler.
No lowering or fallback order changes. This also runs on the integrated tree.
"""
import argparse
import hashlib
from pathlib import Path

REVIEWED = '2e5134b2bc3f609d26e024d2899db5b1311a5b6a5a1d3417aba453f73febf7b1'


def fold(source):
    assert hashlib.sha256(source.encode()).hexdigest() == REVIEWED

    def edit(old, new):
        nonlocal source
        assert source.count(old) == 1, old
        source = source.replace(old, new)

    edit('  (let ((code (bootstrap-dependency-call name forms)))\n'
         '    (when code (return-from bootstrap-numeric-call code)))\n', '')
    edit('  (let ((code (bootstrap-dependency-operator ir)))\n'
         '    (when code (return-from bootstrap-operator code)))\n', '')

    # These six names have no prior fallback except -, LOGAND and LOGIOR.
    # Subtraction returns NIL only at arity zero, where the old dispatcher
    # also returned NIL; logical operations always return generated code.
    edit('    (cond           ((member name', '''    (cond ((eq name 'ldb) (bootstrap-ldb forms))
          ((eq name 'ccl::assq) (bootstrap-assq forms))
          ((member name '(logand logior)) (bootstrap-logical-call name forms))
          ((eq name '-) (bootstrap-subtract forms))
          ((member name '(typep ccl::require-type)) (bootstrap-type-call name forms))
          ((eq name 'ccl::%err-disp) (bootstrap-error-call forms))
          ((member name''')

    start = source.index('(defun bootstrap-operator (ir)')
    pos = source.index('    (case op\n', start)
    source = source[:pos] + source[pos:].replace('    (case op\n', '''    (case op
      ((ccl::logand2 ccl::logior2)
       (bootstrap-primary (bootstrap-logical-call (if (eq op 'ccl::logand2) 'logand 'logior) args)))
''', 1)
    # The existing %ERR-DISP fallback remains in the same clause. Unlike
    # the other dependency operators, an unsupported code needs that call.
    edit('''       (let ((name (case op (ccl::%badarg2 'ccl::%badarg)
                           (ccl::%debug-trap 'ccl::dbg) (t 'ccl::%err-disp))))''', '''       (let ((code (and (eq op 'ccl::%err-disp)
                        (bootstrap-error-call (first (first args))))))
         (when code (return-from bootstrap-operator (bootstrap-primary code))))
       (let ((name (case op (ccl::%badarg2 'ccl::%badarg)
                           (ccl::%debug-trap 'ccl::dbg) (t 'ccl::%err-disp))))''')
    start = source.index('(defun bootstrap-dependency-call ')
    assert source[start:].count('(defun ') == 2
    source = source[:start].rstrip() + '\n'
    assert 'bootstrap-dependency-call' not in source
    assert 'bootstrap-dependency-operator' not in source
    for name in ('bootstrap-operator', 'bootstrap-numeric-call'):
        assert source.count('(defun ' + name + ' ') == 1
    return source


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('reviewed', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    args.output.write_text(fold(args.reviewed.read_text()))
