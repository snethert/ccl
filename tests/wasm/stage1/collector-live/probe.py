import sys
from pathlib import Path
import call_errors as errors
errors.SOURCES={
 'irq_gc':'(lambda () (values))','irq_service':'(lambda () (values))',
 'dead':'(lambda () (cons 997 991))',
 'move':'(lambda (x) (dead) (dead) (ccl::%interrupt-poll) x)',
 'first_arg':'(lambda (a b) a)',
 'restart_live':'(lambda () (restart-case (progn (move nil) (invoke-restart (quote use-it) 37)) (use-it (x) x)))',
 'restart_identity':'(lambda () (restart-case (let ((r (find-restart (quote use-it)))) (move nil) (invoke-restart r (if (eq r (find-restart (quote use-it))) 41 0))) (use-it (x) x)))',
 'restart_closure':'(lambda () (let ((x (cons 43 47))) (restart-bind ((use-it (lambda () (values (car x) (cdr x))))) (move nil) (invoke-restart (quote use-it)))))',
 'restart_nested':'(lambda () (restart-case (restart-case (progn (move nil) (invoke-restart (quote outer) 53)) (inner (x) x)) (outer (x) x)))',
 'restart_handler':'(lambda (bad) (restart-case (handler-bind ((type-error (lambda (c) (move c) (invoke-restart (quote recover) 59)))) (car bad)) (recover (x) x)))',
 'restart_pending':'(lambda (p) (restart-case (unwind-protect (invoke-restart (quote recover) (cons 61 67)) (move nil) (rplaca p 71)) (recover (x) (values (car x) (cdr x)))))',
 'restart_expired':'(lambda () (let ((r (restart-case (find-restart (quote expired)) (expired () 1)))) (move nil) (handler-case (invoke-restart r) (control-error () 73))))',
 'restart_repeat':'(lambda () (restart-bind ((again (lambda () 79))) (move nil) (move nil) (invoke-restart (quote again))))',
 'eq_left':'(lambda () (let ((x (cons 83 89))) (eq x (move x))))',
 'eq_distinct':'(lambda () (let ((x (cons 83 89)) (y (cons 83 89))) (eq x (move y))))',
 'eq_order':'(lambda (p) (let ((x (cons 1 2))) (values (eq (progn (rplaca p 3) x) (progn (move nil) (rplacd p (car p)) x)) (car p) (cdr p))))',
 'captured_let':'(lambda () (let* ((x (move (cons 97 101))) (f (lambda () (car x)))) (funcall f)))',
 'captured_optional':'(lambda (&optional (x (move (cons 103 107)))) (let ((f (lambda () (car x)))) (funcall f)))',
 'captured_key':'(lambda (&key (x (move (cons 109 113)))) (let ((f (lambda () (car x)))) (funcall f)))',
 'captured_setq':'(lambda () (let ((x (cons 127 131))) (let ((f (lambda () (setq x (move (cons 137 139)))))) (funcall f) (values (car x) (cdr x)))))',
 'cons_operands':'(lambda () (let* ((x (cons 149 151)) (y (cons x (move x)))) (values (eq (car y) (cdr y)) (car (car y)))))',
 'rplaca_operand':'(lambda () (let ((x (cons 157 163))) (rplaca x (move (cons 167 173))) (values (car (car x)) (cdr (car x)) (cdr x))))',
 'rplacd_operand':'(lambda () (let ((x (cons 179 181))) (rplacd x (move (cons 191 193))) (values (car x) (car (cdr x)))))',
 'call_argument':'(lambda () (let ((x (cons 197 199))) (car (first_arg x (move nil)))))',
 'callable':'(lambda () (let ((x (cons 211 223))) (let ((f (lambda (ignored) (car x)))) (funcall f (move nil)))))',
 'apply_prefix':'(lambda () (let ((x (cons 227 229))) (car (apply (function first_arg) x (move (cons nil nil))))))',
 'values_operands':'(lambda () (let ((x (cons 233 239))) (multiple-value-bind (a b) (values x (move x)) (values (eq a b) (car a) (cdr b)))))',
 'throw_tag':'(lambda () (let ((tag (cons 241 251))) (catch tag (throw tag (car (move (cons 257 263)))))))',
 'special_rhs':'(lambda () (let ((dyn_a (cons 269 271))) (declare (special dyn_a)) (setq dyn_a (move (cons 277 281))) (car dyn_a)))',
 'progv_values':'(lambda (symbols) (progv symbols (move (cons (cons 283 293) nil)) (car (symbol-value (car symbols)))) )',
 'inline_apply':'(lambda () (let ((x (cons 307 311))) (apply (lambda (ignored) (car x)) (move (cons nil nil)))))',
 'inline_mvc':'(lambda () (let ((x (cons 313 317))) (multiple-value-call (lambda (ignored) (car x)) (move nil))))',
 'd_condition_decline':'(lambda (bad) (catch :x (let ((*debugger-hook* (lambda (c h) (throw :x (type-error-datum c))))) (handler-bind ((type-error (lambda (c) (move c) (values)))) (car bad)))))',
 'condition_next_handler':'(lambda (bad) (catch :x (handler-bind ((type-error (lambda (c) (move c) (values))) (type-error (lambda (c) (throw :x (type-error-datum c))))) (car bad))))',
 'rest_move':'(lambda (&rest xs) (move nil) (values (car xs) (car (cdr xs))))',
}
def cases():
 rows=[]
 def add(name,values,args=None,nodes=None,after=None):
  ns=nodes or [];rows.append(dict(id=name,function=name,args=args or [],nodes=ns,bindings={},capacity=16,pending=1,pendingAfter=1,expected=dict(status='RETURN',values=values,nodes=ns if after is None else after,specials=[101,103,'unbound'])))
 for n,v in [('restart_live',[37]),('restart_identity',[41]),('restart_closure',[43,47]),('restart_nested',[53]),('restart_expired',[73]),('restart_repeat',[79]),('eq_left',['t']),('eq_distinct',['nil']),('captured_let',[97]),('captured_optional',[103]),('captured_key',[109]),('captured_setq',[137,139]),('cons_operands',['t',149]),('rplaca_operand',[167,173,163]),('rplacd_operand',[179,191]),('call_argument',[197]),('callable',[211]),('apply_prefix',[227]),('values_operands',['t',233,239]),('throw_tag',[257]),('special_rhs',[277]),('inline_apply',[307]),('inline_mvc',[313])]:add(n,v)
 add('restart_handler',[59],['t'])
 add('restart_pending',[61,67],['n0'],[[0,0]],[[71,0]])
 add('eq_order',['t',3,3],['n0'],[[0,0]],[[3,3]])
 add('progv_values',[283],['n0'],[['s:dyn_a','nil']])
 add('d_condition_decline',[347],[347])
 add('condition_next_handler',[349],[349])
 add('rest_move',[331,337],[331,337])
 return rows
errors.cases=cases
if __name__=='__main__':errors.run(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
