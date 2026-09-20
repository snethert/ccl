"""Opt-in integer calls over the accepted LL11-b compiler; disposable U1 only."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE='bd608480264e7090684c5bfce52de083ec9ef0e1800f7d548a253ca79adea956'
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def generate():
 s=(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text();assert hashlib.sha256(s.encode()).hexdigest()==BASE
 s=replace(s,'(defvar *b-allocation-retry* nil)','(defvar *b-allocation-retry* nil)\n(defvar *b-integer-service* nil)')
 s=replace(s,'                   ((symbol-value set)', '''                   ((+ - * ash integer-length truncate)
                    (if (and *b-integer-service* (not (member (car x) symbol-access-shadows)))
                      (progn
                        (unless (= (length (cdr x)) (if (eq (car x) 'integer-length) 1 2)) (refuse :integer-arity))
                        (cons (cdr (assoc (car x) '((+ . %integer-add) (- . %integer-sub) (* . %integer-mul) (ash . %integer-ash) (integer-length . %integer-length) (truncate . %integer-truncate)))) (mapcar #'walk (cdr x))))
                      (cons (car x) (mapcar #'walk (cdr x)))))
                   ((symbol-value set)''')
 s=replace(s,"(member head '(%wasm-symbol-value", "(and *b-integer-service* (member head '(%integer-add %integer-sub %integer-mul %integer-ash %integer-length %integer-truncate))) (member head '(%wasm-symbol-value")
 s=replace(s,"      (ccl::call\n       (when", """      (ccl::call
       (when (and *b-integer-service* (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
                  (member (first (ccl::acode-operands (first args))) '(%integer-add %integer-sub %integer-mul %integer-ash %integer-length %integer-truncate)))
         (unless (and (null (third args)) (null (second (second args)))) (refuse :integer-spread))
         (return-from b-multiple (b-integer-call (first (ccl::acode-operands (first args))) (first (second args)))))
       (when""")
 anchor='             (when *b-allocation-retry* (write-string "(import'
 s=replace(s,anchor,'             (when *b-integer-service* (write-string "(import \\"integer\\" \\"calculate\\" (func $integer_slow (param i32 i32) (result i32)))" s))\n'+anchor)
 s=replace(s,'             (write-string (b-object-runtime) s)','             (when *b-integer-service* (write-string (b-integer-runtime) s))\n             (write-string (b-object-runtime) s)')
 s+='\n'+(HERE/'integer.lisp').read_text()
 return s
