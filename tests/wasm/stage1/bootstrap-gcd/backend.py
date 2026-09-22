"""Numeric restart and GCD prerequisites over the accepted audit-159 tree."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PACKET = ROOT.parent / 'ccl-evidence/2026-09-22-stage1-bootstrap-limb-division-r1'
BACKEND = 'compiler/WASM32/wasm32-backend.lisp'
ARCH = 'compiler/WASM32/wasm32-arch.lisp'


def generate():
    text = (ROOT / BACKEND).read_text()
    old = '(defun bootstrap-signal (forms fatal)'
    assert text.count(old) == 1
    text = text.replace(old, '(defun bootstrap-signal (forms fatal &optional construct-only)')
    old = '(write-string (b-signal (make-b-raw-code :text condition) fatal) s)'
    assert text.count(old) == 1
    text = text.replace(old, """(write-string (if construct-only
                                  (b-multiple (make-b-raw-code :text condition))
                                  (b-signal (make-b-raw-code :text condition) fatal)) s)""")
    old = "    (cond ((member name '(ccl::%double-float-sign ccl::%short-float-sign))"
    assert text.count(old) == 1
    text = text.replace(old, """    (cond ((eq name 'make-condition)
           (multiple-value-bind (class constant) (bootstrap-immediate (car forms))
             (when (and constant (symbolp class))
               (unless class (refuse :bootstrap-condition-class))
               (bootstrap-signal forms nil t))))
          ((eq name 'ccl::condition-arg)
           (when (= (length forms) 3)
             (multiple-value-bind (class constant) (bootstrap-immediate (first forms))
               (multiple-value-bind (default defaultp) (bootstrap-immediate (third forms))
                 (when (and constant (symbolp class) defaultp
                            (member default '(simple-error simple-condition simple-warning)))
                   (unless class (refuse :bootstrap-condition-class))
                   (let ((args (second forms)))
                     (when (and (ccl::acode-p args)
                                (eq (ccl::acode-operator-name (ccl::acode-operator args)) 'ccl::list))
                       (bootstrap-signal (cons (first forms) (first (ccl::acode-operands args))) nil t))))))))
          ((member name '(ccl::%double-float-sign ccl::%short-float-sign))""")
    old = '(type-error 156 :datum :expected-type)'
    assert text.count(old) == 1
    text = text.replace(old, '(type-error 156 :datum :expected-type) (program-error 2076)')
    old = '(defun bootstrap-error-call (forms)'
    assert text.count(old) == 1
    text = text.replace(old, old + """
  (when (and (= (length forms) 1)
             (eql (ccl::acode-fixnum-form-p (first forms)) ccl::$xtminps))
    (return-from bootstrap-error-call
      (b-call (bootstrap-constant 'ccl::%wasm-too-many-arguments) '(nil nil))))""")
    old = '(function . functionp) (package . packagep)'
    assert text.count(old) == 1
    text = text.replace(old, '(function . functionp) (package . packagep) (restart . ccl::restartp)')
    start = text.index('(defun bootstrap-uvector-access ')
    end = text.index('(defun bootstrap-heap-block ', start)
    text = text[:start] + (HERE / 'uvector.lisp').read_text() + '\n' + text[end:]
    old = '(:unsigned-32-bit-vector 4 nil 167 0 536870911)'
    assert text.count(old) == 1
    text = text.replace(old, old + '\n                              (:bignum 4 nil 7 0 536870911)')
    return text


def arch():
    return (ROOT / ARCH).read_text()


def runtime_files():
    return {}


def source_files(root):
    unit = json.loads((PACKET / 'native/proposal/unit.json').read_text())
    result = {r['path']: (root / r['path']).read_text()
              for r in unit['added'] + unit['modified']
              if r['path'].startswith(('level-0/', 'level-1/'))}
    name = 'level-0/WASM32/w32-prims.lisp'
    old = '(defun %fixnum-gcd (a b)\n  (loop'
    assert result[name].count(old) == 1
    result[name] = result[name].replace(old, '(defun %fixnum-gcd (a b)\n  (declare (fixnum a b))\n  (loop')
    result['level-0/WASM32/w32-prims.lisp'] += '\n' + (HERE / 'primitives.lisp').read_text()
    name = 'level-1/l1-error-signal.lisp'
    text = (root / name).read_text()
    old = '  (%kernel-restart-internal error-type args (%get-frame-ptr)))'
    assert text.count(old) == 1
    result[name] = text.replace(old, '''  #+wasm32-target (%wasm-kernel-restart error-type args)
  #-wasm32-target
  (%kernel-restart-internal error-type args (%get-frame-ptr)))''')
    return result


def proposal(source, out):
    shutil.copytree(PACKET / 'native/proposal', out)
    unit = json.loads((out / 'unit.json').read_text())
    edits = {BACKEND: generate(), ARCH: arch(), **source_files(ROOT)}
    for row in unit['added'] + unit['modified']:
        name = row['path']
        text = edits.pop(name, (ROOT / name).read_text())
        path = out / 'files' / name
        path.write_text(text)
        row['sha256' if 'sha256' in row else 'after'] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name, text in edits.items():
        path = out / 'files' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        unit['modified'].append(dict(path=name, before=hashlib.sha256((source/name).read_bytes()).hexdigest(),
                                    after=hashlib.sha256(path.read_bytes()).hexdigest()))
    (out / 'unit.json').write_text(json.dumps(unit, indent=2, sort_keys=True) + '\n')
    return unit
