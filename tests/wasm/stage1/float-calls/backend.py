import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE='d328c6bc7882631d98bb49a878110c3b90b691583405a021e79ebef1f9192df4'
def replace(s,a,b,n=1):
 assert s.count(a)==n,(a,s.count(a),n);return s.replace(a,b)
def generate():
 s=(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text();assert hashlib.sha256(s.encode()).hexdigest()==BASE
 s=replace(s,'(defvar *b-integer-service* nil)','(defvar *b-integer-service* nil)\n(defvar *b-float-service* nil)\n(defvar *b-float-safety* 1)')
 s=replace(s,'                   ((+ - * ash integer-length truncate)', '''                   ((/ < <= = /= >= > float)
                    (if (and *b-float-service* (not (member (car x) symbol-access-shadows)))
                     (progn
                      (unless (= (length (cdr x)) 2) (refuse :float-arity))
                      (if (eq (car x) 'float)
                       (progn (unless (typep (third x) 'float) (refuse :float-prototype))
                        (cons (if (typep (third x) 'single-float) '%float-single '%float-double) (mapcar #'walk (cdr x))))
                       (cons (cdr (assoc (car x) '((/ . %float-div) (< . %float-lt) (<= . %float-le) (= . %float-eq) (/= . %float-ne) (>= . %float-ge) (> . %float-gt)))) (mapcar #'walk (cdr x)))))
                     (cons (car x) (mapcar #'walk (cdr x)))))
                   ((+ - * ash integer-length truncate)''')
 old="(cons (cdr (assoc (car x) '((+ . %integer-add)"
 new="(cons (or (and *b-float-service* (cdr (assoc (car x) '((+ . %float-add) (- . %float-sub) (* . %float-mul))))) (cdr (assoc (car x) '((+ . %integer-add)"
 s=replace(s,old,new)
 s=replace(s,"(truncate . %integer-truncate)))) (mapcar", "(truncate . %integer-truncate))))) (mapcar")
 floats='(%float-add %float-sub %float-mul %float-div %float-lt %float-le %float-eq %float-ne %float-ge %float-gt %float-single %float-double)'
 s=replace(s,"(and *b-integer-service* (member head '(%numeric-operation",f"(and *b-float-service* (member head '{floats})) (and *b-integer-service* (member head '(%numeric-operation")
 s=replace(s,'      (ccl::call\n       (when',f'''      (ccl::call
       (when (and *b-float-service* (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
         (member (first (ccl::acode-operands (first args))) '{floats}))
        (unless (and (null (third args)) (null (second (second args)))) (refuse :float-spread))
        (return-from b-multiple (b-float-call (first (ccl::acode-operands (first args))) (first (second args)))))
       (when''')
 s=replace(s,'             (when *b-integer-service* (write-string "(import', '             (when *b-float-service* (write-string "(import \\"floating\\" \\"calculate\\" (func $float_slow (param i32 i32 i32) (result i32)))" s))\n             (when *b-integer-service* (write-string "(import')
 s=replace(s,'             (write-string (b-object-runtime) s)','             (when *b-float-service* (write-string (b-float-runtime) s))\n             (write-string (b-object-runtime) s)')
 s=replace(s,'(division-by-zero . 32768)','(division-by-zero . 32768) (floating-point-invalid-operation . 65536) (floating-point-overflow . 131072) (floating-point-underflow . 262144) (floating-point-inexact . 524288)')
 # Admission remains opt-in, including quoted condition symbols.
 old='arithmetic-error division-by-zero))'
 s=replace(s,old,'arithmetic-error division-by-zero))',2) # Count-only guard; add opt-in adjacent alternatives below.
 s=replace(s,"(b-wat \"(i32.const ~d)\" (* 4 (b-condition-mask (first args)))))", "(b-wat \"(i32.const ~d)\" (* 4 (b-condition-mask (first args)))))\n             ((and *b-float-service* (member (first args) '(floating-point-invalid-operation floating-point-overflow floating-point-underflow floating-point-inexact))) (b-wat \"(i32.const ~d)\" (* 4 (b-condition-mask (first args)))))")
 s=replace(s,"(member (second xs) '(condition", "(and *b-float-service* (member (second xs) '(floating-point-invalid-operation floating-point-overflow floating-point-underflow floating-point-inexact))) (member (second xs) '(condition")
 s=replace(s,"(setq *b-restart-names* (if *b-integer-service*", "(setq *b-restart-names* (if *b-float-service* '(list cons function simple-vector integer fixnum or number real truncate + - * / < <= = /= >= > float) (if *b-integer-service*")
 s=replace(s,"'(list cons function simple-vector integer fixnum or)))\n  ;; Check", "'(list cons function simple-vector integer fixnum or))))\n  ;; Check")
 # Handler types must not widen default admission through the mask helper.
 s=replace(s,'(defun b-condition-mask (type)\n',"(defun b-condition-mask (type)\n  (when (and (member type '(floating-point-invalid-operation floating-point-overflow floating-point-underflow floating-point-inexact)) (not *b-float-service*)) (refuse :float-condition-mode))\n")
 for n in ['b-condition-runtime','b-implicit-runtime']:s=replace(s,'(defun '+n+' ', '(defun prior-float-'+n+' ')
 return s+'\n'+(HERE/'float.lisp').read_text()
