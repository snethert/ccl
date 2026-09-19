import sys
from pathlib import Path
import call_errors as errors
errors.SOURCES={
 'irq_gc':'(lambda () (values))','irq_service':'(lambda () (values))',
 'g_dead':'(lambda () (cons 997 991))',
 'g_cons':'(lambda () (let ((x (cons 7 11))) (g_dead) (g_dead) (ccl::%interrupt-poll) (values (car x) (cdr x))))',
 'g_cycle':'(lambda () (let ((x (cons 13 17))) (rplacd x x) (g_dead) (g_dead) (ccl::%interrupt-poll) (values (car (cdr x)) (eq x (cdr x)))))',
 'g_bind':'(lambda () (let ((dyn_a (cons 19 23))) (declare (special dyn_a)) (g_dead) (g_dead) (ccl::%interrupt-poll) (values (car dyn_a) (cdr dyn_a))))',
 'g_twice':'(lambda () (let ((dyn_a (cons 29 31))) (declare (special dyn_a)) (g_dead) (g_dead) (ccl::%interrupt-poll) (let ((dyn_b (cons 37 dyn_a))) (declare (special dyn_b)) (g_dead) (g_dead) (ccl::%interrupt-poll) (values (car dyn_a) (car dyn_b) (eq (cdr dyn_b) dyn_a)))))',
 'g_closure':'(lambda () (let ((x (cons 41 43))) (let ((f (lambda () (car x)))) (g_dead) (g_dead) (ccl::%interrupt-poll) (values (funcall f) (cdr x)))))',
 'g_retained':'(lambda () (multiple-value-prog1 (values (cons 47 53) 59) (g_dead) (g_dead) (ccl::%interrupt-poll)))',
 'g_retained_read':'(lambda () (multiple-value-bind (x y) (g_retained) (values (car x) (cdr x) y)))',
 'g_unwind':'(lambda (p) (let ((dyn_a (cons 61 67))) (declare (special dyn_a)) (catch :x (unwind-protect (progn (g_dead) (g_dead) (ccl::%interrupt-poll) (throw :x (car dyn_a))) (rplaca p (cdr dyn_a))))))',
 'g_rest':'(lambda (&rest xs) (g_dead) (g_dead) (ccl::%interrupt-poll) (values (car xs) (car (cdr xs)) (car (cdr (cdr xs)))))',
 'g_live_closure':'(lambda () (let ((x (cons 151 157))) (let ((f (lambda () (g_dead) (g_dead) (ccl::%interrupt-poll) (values (car x) (cdr x))))) (funcall f))))',
 'g_pending':'(lambda () (let ((x (catch :x (unwind-protect (throw :x (cons 163 167)) (g_dead) (g_dead) (ccl::%interrupt-poll))))) (values (car x) (cdr x))))',
 'g_recursive':'(lambda (xs) (let ((x (cons 211 223))) (labels ((walk (ys) (g_dead) (g_dead) (ccl::%interrupt-poll) (if ys (walk (cdr ys)) (values (car x) (cdr x))))) (walk xs))))',
 'g_first':'(lambda (x &rest other) (values (car x) (cdr x)))',
 'g_inline_pipeline':'(lambda () (multiple-value-call (function g_first) (multiple-value-prog1 (values (cons 173 179) 1 2 3) (g_dead) (g_dead) (ccl::%interrupt-poll))))',
 'g_arena_pipeline':'(lambda () (multiple-value-call (function g_first) (multiple-value-prog1 (values (cons 181 191) 1 2 3 4) (g_dead) (g_dead) (ccl::%interrupt-poll))))',
 'v_many':'(lambda (s xs vs) (progv xs vs (let ((dyn_b 79)) (declare (special dyn_b)) (values (symbol-value s) dyn_b))))',
}
def cases():
 rows=[]
 def add(name,args,values,nodes=None,after=None):
  nodes=nodes or [];rows.append(dict(id=name,function=name,args=args,nodes=nodes,bindings={},capacity=16,pending=1,pendingAfter=1,expected=dict(status='RETURN',values=values,nodes=nodes if after is None else after,specials=[101,103,'unbound'])))
 for name,values in [('g_cons',[7,11]),('g_cycle',[13,'t']),('g_bind',[19,23]),('g_twice',[29,37,'t']),('g_closure',[41,43]),('g_retained_read',[47,53,59]),('g_live_closure',[151,157]),('g_pending',[163,167]),('g_inline_pipeline',[173,179]),('g_arena_pipeline',[181,191])]:add(name,[],values)
 add('g_unwind',['n0'],[61],[[3,5]],[[67,5]])
 add('g_rest',[71,73,79],[71,73,79])
 add('g_recursive',['n0'],[211,223],[[0,'n1'],[0,'n2'],[0,'nil']])
 add('v_many',['s:dyn_a','n0','n2'],[83,79],[['s:dyn_a','n1'],['s:dyn_a','nil'],[81,'n3'],[83,'nil']])
 return rows
errors.cases=cases
if __name__=='__main__':errors.run(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
