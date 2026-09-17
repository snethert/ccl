"""Generate an isolated cumulative backend from the reviewed LL05 source."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'b-call-errors/wasm32-backend.lisp'

def generate():
    data=BASE.read_bytes()
    if hashlib.sha256(data).hexdigest()!='68a5b4dbb1212bad052230a177f29fe2c64574aad1efffc86c47932379d016a0':
        raise ValueError('reviewed backend changed')
    layout=json.loads((HERE/'function-layout.json').read_text())
    d1=json.loads((HERE.parents[3]/'doc/WASM/contracts/wasm32-layout.v1.json').read_text())
    subtag=next(r['value'] for r in d1['subtags'] if r['name']=='subtag-function')
    expected={'code_id':4,'environment':8,'code_version':12,'arity_metadata':16,'debug_metadata':20,'constant_pool':24}
    if (layout['fields']!=expected or layout['bytes']!=32 or layout['elements']!=6 or
        layout['subtag']!=subtag or layout['header']!=(6<<8)|subtag):
        raise ValueError('function layout changed; regenerate the emitter sites')
    s=data.decode()
    def change(old,new,count=1):
        nonlocal s
        if s.count(old)!=count: raise ValueError(('compiler anchor',old,s.count(old),count))
        s=s.replace(old,new)
    change('(defvar *module-result-tag* nil)', '(defvar *pool-layouts* nil)\n(defvar *pool-current* nil)\n(defvar *module-result-tag* nil)')
    change('(defun b-one-module (afunc)\n  (let* (', '(defun b-one-module (afunc)\n  (let* ((*pool-current* afunc) ')
    change('(b-plan-local-environments)\n    (let ((modules', '(pool-plan)\n    (b-plan-local-environments)\n    (let ((modules')
    change('(*b-functions* nil) (*b-captured* nil)', '(*pool-layouts* nil) (*b-functions* nil) (*b-captured* nil)')
    change('(list :name *module-name* :arity arity :wat wat :imports', '(list :pool (cdr (assoc afunc *pool-layouts* :test #\'eq)) :name *module-name* :arity arity :wat wat :imports')
    change('(t (emit-expression ir))))\n      (ccl::%function', '((pool-literal-p (first args)) (pool-load (first args)))\n             (t (emit-expression ir))))\n      (ccl::%function')
    # Literal data graphs must never be walked as acode or executable source.
    change("(mapc #'walk args)))", "(unless (eq op 'ccl::immediate) (mapc #'walk args))))")
    change("(every #'walk a))))", "(or (eq op 'ccl::immediate) (every #'walk a)))))")
    change("(funcall fn x) (mapc (lambda (v) (visit v fn)) (ccl::acode-operands x))", "(funcall fn x) (unless (eq (ccl::acode-operator-name (ccl::acode-operator x)) 'ccl::immediate) (mapc (lambda (v) (visit v fn)) (ccl::acode-operands x)))")
    change('(when (consp node)\n          (when (gethash node seen)', "(when (and (consp node) (not (and (eq (car node) 'quote) (consp (cdr node)) (null (cddr node)))))\n          (when (gethash node seen)")
    change('(and (integerp x) (<= -536870912 x 536870911)) (member x vars)', '(and (integerp x) (<= -536870912 x 536870911)) (and (atom x) (pool-literal-p x)) (member x vars)')
    change('(quote (unless (and (= n 1) (or (assoc (second xs)', '(quote (unless (and (= n 1) (or (null (second xs)) (eq (second xs) t) (and (integerp (second xs)) (<= -536870912 (second xs) 536870911)) (pool-literal-p (second xs)) (assoc (second xs)')
    # Change only function-object fields and environment placement, not context records.
    change('(i32.const 24) (i32.const 1322)', '(i32.const 32) (i32.const 1578)',3)
    change('(bytes (+ 24 (if (zerop n)', '(bytes (+ 32 (if (zerop n)')
    change('(ceiling (+ 24 (if (zerop n)', '(ceiling (+ 32 (if (zerop n)',2)
    change('(i32.store ~a (i32.const 1322))', '(i32.store ~a (i32.const 1578))')
    change('(b-at base 30)', '(b-at base 38)')
    change('(format s "(i32.store offset=24 ~a (i32.const ~d))"', '(format s "(i32.store offset=32 ~a (i32.const ~d))"')
    change('(+ 28 (* 4 i)) base (b-cell-reference v)', '(+ 36 (* 4 i)) base (b-cell-reference v)')
    change('(+ 28 (* 4 n)) base', '(+ 36 (* 4 n)) base')
    change('base base base)\n          (when (plusp n)', 'base base base)\n          (format s "(i32.store offset=24 ~a ~a) (i32.store offset=28 ~a (i32.const 0))" base (pool-child-load afunc) base)\n          (when (plusp n)')
    change('(i32.add (local.get $dispatch_self) (i32.const 24))', '(i32.add (local.get $dispatch_self) (i32.const 32))')
    change('(defun b-signal (form fatal)\n', "(defun b-signal (form fatal)\n  (when (and (ccl::acode-p form) (eq (ccl::acode-operator-name (ccl::acode-operator form)) 'ccl::immediate) (stringp (first (ccl::acode-operands form)))) (refuse :b-signal-format-string))\n")
    start=s.index('(defun compile-call-module (source-text name links)')
    end=s.index(';;; Rest/APPLY sequences',start)
    s=s[:start]+s[end:]
    return s+'\n'+(HERE/'compiler-extension.lisp').read_text()

if __name__=='__main__':
    import sys
    Path(sys.argv[1]).write_text(generate())
