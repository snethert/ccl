import sys
from pathlib import Path
import inherited_retry_probe as inherited
errors=inherited.errors
errors.SOURCES.update({
 'grow_value':'(lambda () (let* ((x (cons 211 223)) (dyn_a x)) (declare (special dyn_a)) (values (eq x dyn_a) (car dyn_a))))',
 'grow_twice':'(lambda () (let* ((dyn_a (cons 227 229)) (dyn_b (cons 233 239))) (declare (special dyn_a dyn_b)) (values (car dyn_a) (cdr dyn_b))))',
 'grow_progv':'(lambda (a b) (let ((names (cons a (cons b nil))) (vals (cons (cons 241 251) (cons (cons 257 263) nil)))) (progv names vals (values (car (symbol-value a)) (cdr (symbol-value b))))))',
 'grow_repeat':'(lambda (a) (progv (cons a (cons a nil)) (cons (cons 269 271) (cons (cons 277 281) nil)) (car (symbol-value a))))',
 'grow_missing':'(lambda (a b) (progv (cons a (cons b nil)) (cons 283 nil) (handler-case (symbol-value b) (unbound-variable () (symbol-value a)))))',
 'grow_cleanup':'(lambda () (let ((dyn_a (cons 293 307))) (declare (special dyn_a)) (catch :x (unwind-protect (let ((dyn_b (cons 311 313))) (declare (special dyn_b)) (throw :x (car dyn_b))) (rplaca dyn_a 317))) (car dyn_a)))',
 'restart_value':'(lambda () (restart-case (invoke-restart (quote use-it) 331) (use-it (x) x)))',
 'restart_closure':'(lambda () (let ((x (cons 337 347))) (restart-bind ((use-it (lambda () (values (car x) (cdr x))))) (pair nil nil) (invoke-restart (quote use-it)))))',
 'restart_nested':'(lambda () (restart-case (restart-case (invoke-restart (quote outer) 349) (inner (x) x)) (outer (x) x)))',
 'restart_identity':'(lambda () (restart-case (let ((r (find-restart (quote use-it)))) (pair nil nil) (invoke-restart r (if (eq r (find-restart (quote use-it))) 353 0))) (use-it (x) x)))',
 'condition_simple':'(lambda (bad) (handler-case (car bad) (type-error (c) (type-error-datum c))))',
 'condition_heap':'(lambda () (let ((bad (lambda () 1))) (handler-case (car bad) (type-error (c) (eq bad (type-error-datum c))))))',
 'condition_restart':'(lambda (bad) (restart-case (handler-bind ((type-error (lambda (c) (invoke-restart (quote recover) (type-error-datum c))))) (car bad)) (recover (x) x)))',
 'condition_decline':'(lambda (bad) (catch :x (handler-bind ((type-error (lambda (c) (pair nil nil) (values))) (type-error (lambda (c) (throw :x (type-error-datum c))))) (car bad))))',
 'condition_cleanup':'(lambda (bad p) (handler-case (unwind-protect (car bad) (pair nil nil) (rplaca p 359)) (type-error (c) (values (type-error-datum c) (car p)))) )',
 'restart_expired':'(lambda () (let ((r (restart-case (find-restart (quote expired)) (expired () 1)))) (handler-case (invoke-restart r) (control-error () 367))))',
})
def cases():
 rows=inherited.cases()
 def add(name,values,args=None,nodes=None,after=None):
  ns=nodes or [];rows.append(dict(id=name,function=name,args=args or [],nodes=ns,bindings={},capacity=16,expected=dict(status='RETURN',values=values,nodes=ns if after is None else after,specials=[101,103,'unbound'])))
 for name,values in [('grow_value',['t',211]),('grow_twice',[227,239]),('grow_cleanup',[317]),('restart_value',[331]),('restart_closure',[337,347]),('restart_nested',[349]),('restart_identity',[353]),('condition_heap',['t']),('restart_expired',[367])]:add(name,values)
 add('grow_progv',[241,263],['s:dyn_a','s:dyn_b']);add('grow_repeat',[277],['s:dyn_a']);add('grow_missing',[283],['s:dyn_a','s:dyn_b'])
 add('condition_simple',[373],[373]);add('condition_restart',[379],[379]);add('condition_decline',[383],[383]);add('condition_cleanup',[389,359],[389,'n0'],[[7,11]],[[359,11]])
 return rows
errors.cases=cases
if __name__=='__main__':errors.compile_suite(*map(Path,sys.argv[1:4]))
