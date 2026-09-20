"""Generated numeric condition proposal over accepted integer calls."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE='03b812512f6234269ac7d6c2d13dfbd612aa0cb8ee89634d89cdca9d68b2f11c'
def replace(s,a,b,n=1):
 assert s.count(a)==n,(a,s.count(a),n);return s.replace(a,b)
def generate():
 s=(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text();assert hashlib.sha256(s.encode()).hexdigest()==BASE
 s=replace(s,'(ccl::no-applicable-method-exists . 8192)','(ccl::no-applicable-method-exists . 8192) (arithmetic-error . 16384) (division-by-zero . 32768)')
 s=replace(s,'storage-condition ccl::no-applicable-method-exists)','storage-condition ccl::no-applicable-method-exists arithmetic-error division-by-zero)',2)
 s=replace(s,"'(list cons function simple-vector integer fixnum or)","'(list cons function simple-vector integer fixnum or number real truncate)")
 anchor='                   ((type-error-datum type-error-expected-type cell-error-name)'
 s=replace(s,anchor,"                   ((arithmetic-error-operation arithmetic-error-operands) (cons (if (eq (car x) 'arithmetic-error-operation) '%numeric-operation '%numeric-operands) (mapcar #'walk (cdr x))))\n"+anchor)
 s=replace(s,"(and *b-integer-service* (member head '(%integer-add", "(and *b-integer-service* (member head '(%numeric-operation %numeric-operands %integer-add")
 anchor='      (ccl::call\n       (when'
 s=replace(s,anchor,"""      (ccl::call
       (when (and *b-integer-service* (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
                  (member (first (ccl::acode-operands (first args))) '(%numeric-operation %numeric-operands)))
         (return-from b-multiple (b-numeric-field (first (ccl::acode-operands (first args))) (first (second args)))))
       (when""")
 for name in ['b-condition-runtime','b-implicit-runtime']:
  s=replace(s,'(defun '+name+' ', '(defun prior-numeric-'+name+' ')
 s+='\n'+(HERE/'conditions.lisp').read_text()
 return s
