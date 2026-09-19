import sys
from pathlib import Path
import call_errors as errors
errors.SOURCES={
 'irq_gc':'(lambda () (values))','irq_service':'(lambda () (values))',
 'dead':'(lambda () (cons 997 991))',
 'move':'(lambda (x) (dead) (dead) (ccl::%interrupt-poll) x)',
 'closed':'(lambda (p) (tagbody (funcall (lambda () (move nil) (go done))) (rplaca p 99) done (rplaca p 17)) (car p))',
 'handler':'(lambda (p) (tagbody (handler-bind ((type-error (lambda (c) (move nil) (go done)))) (rplaca 1 2)) (rplaca p 99) done (rplaca p 19)) (car p))',
 'restart':'(lambda (p) (tagbody (restart-case (invoke-restart (quote jump)) (jump () (move nil) (go done))) (rplaca p 99) done (rplaca p 23)) (car p))',
}
errors.SOURCES.update({
 'local_cleanup':'(lambda (p) (tagbody (unwind-protect (go done) (move nil) (rplaca p 191)) (rplaca p 99) done) (car p))',
 'local_binding':'(lambda () (let ((dyn_a 193)) (declare (special dyn_a)) (tagbody (let ((dyn_a 197)) (declare (special dyn_a)) (go done)) done (move nil)) dyn_a))',
 'closed_cleanup':'(lambda (p) (tagbody (unwind-protect (funcall (lambda () (move nil) (go done))) (move nil) (rplaca p 29)) (rplaca p 99) done) (car p))',
 'closed_binding':'(lambda () (let ((dyn_a 31)) (declare (special dyn_a)) (tagbody (let ((dyn_a 37)) (declare (special dyn_a)) (funcall (lambda () (move nil) (go done)))) done) dyn_a))',
 'closed_shadow':'(lambda (p) (tagbody done (tagbody (funcall (lambda () (move nil) (go done))) (rplaca p 99) done (rplaca p 41))) (car p))',
 'closed_outer':'(lambda (p) (tagbody (tagbody (funcall (lambda () (move nil) (go outer))) (rplaca p 99)) (rplaca p 98) outer (rplaca p 43)) (car p))',
 'closed_mutable':'(lambda () (let ((x (cons 47 53))) (tagbody (let ((f (lambda () (setq x (move (cons 59 61))) (go done)))) (move nil) (funcall f)) done) (car x)))',
 'closed_grandchild':'(lambda (p) (tagbody (funcall (funcall (lambda () (lambda () (move nil) (go done))))) (rplaca p 99) done (rplaca p 67)) (car p))',
 'closed_flet':'(lambda (p) (tagbody (flet ((leave () (move nil) (go done))) (leave)) (rplaca p 99) done (rplaca p 71)) (car p))',
 'closed_labels':'(lambda (xs) (let ((v 0)) (tagbody (labels ((walk (ys) (if ys (progn (setq v (car ys)) (walk (cdr ys))) (progn (move nil) (go done))))) (walk xs)) (setq v 99) done) v))',
 'closed_replace':'(lambda (p) (tagbody (unwind-protect (funcall (lambda () (go first))) (move nil) (go second)) first (rplaca p 99) (go end) second (rplaca p 73) end) (car p))',
 'closed_cancel':'(lambda (p) (tagbody (unwind-protect (rplaca 1 2) (funcall (lambda () (move nil) (go done)))) (rplaca p 99) done (rplaca p 79)) (car p))',
 'closed_expired':'(lambda () (let ((f nil)) (tagbody (setq f (lambda () (go done))) done) (move nil) (handler-case (funcall f) (control-error () 83))))',
 'closed_nearest':'(lambda () (let ((seen 0)) (tagbody (let ((outer (lambda () (go done)))) (tagbody (let ((inner (lambda () (go inner)))) (move nil) (funcall outer) (funcall inner)) inner) (setq seen 99)) done) seen))',
 'handler_cleanup':'(lambda (p) (tagbody (unwind-protect (handler-bind ((type-error (lambda (c) (move nil) (go done)))) (rplaca 1 2)) (move nil) (rplaca p 97)) (rplaca p 99) done) (car p))',
 'restart_binding':'(lambda () (let ((dyn_a 101)) (declare (special dyn_a)) (tagbody (let ((dyn_a 103)) (declare (special dyn_a)) (restart-case (invoke-restart (quote jump)) (jump () (move nil) (go done)))) done) dyn_a))',
 'go_test':'(lambda (p) (tagbody (if (progn (move nil) (go done)) (rplaca p 99) nil) done (rplaca p 107)) (car p))',
 'go_operand':'(lambda (p) (tagbody (cons (move (cons 109 113)) (go done)) (rplaca p 99) done (rplaca p 127)) (car p))',
 'go_pending':'(lambda (p) (tagbody (prog1 (move (cons 131 137)) (go done)) (rplaca p 99) done (rplaca p 139)) (car p))',
 'fast_loop':'(lambda (xs) (let ((v 0)) (tagbody next (if xs (progn (setq v (car xs)) (setq xs (cdr xs)) (go next)) nil)) v))',
 'fast_choices':'(lambda (x p) (tagbody (if x (go yes) (go no)) yes (rplaca p 149) (go end) no (rplaca p 151) end) (car p))',
 'fast_fallthrough':'(lambda (p) (tagbody a (rplaca p 157) b (rplacd p 163)) (values (car p) (cdr p)))',
 'fast_nested':'(lambda (p) (tagbody (tagbody (go inner) (rplaca p 99) inner (rplaca p 167)) (go end) (rplaca p 98) end) (car p))',
 'fast_pending':'(lambda (xs) (let ((x (cons 173 179))) (car (prog1 x (tagbody next (if xs (progn (setq x (move (cons (car xs) 181))) (setq xs (cdr xs)) (go next)) nil))))))',
})
def cases():
 rows=[]
 def add(name,values,args=None,nodes=None,after=None,id=None):
  ns=nodes or [];rows.append(dict(id=id or name,function=name,args=args or [],nodes=ns,bindings={},capacity=16,pending=1,pendingAfter=1,expected=dict(status='RETURN',values=values,nodes=ns if after is None else after,specials=[101,103,'unbound'])))
 for name,n in [('local_cleanup',191),('closed',17),('handler',19),('restart',23),('closed_cleanup',29),('closed_shadow',41),('closed_outer',43),('closed_grandchild',67),('closed_flet',71),('closed_replace',73),('closed_cancel',79),('handler_cleanup',97),('go_test',107),('go_operand',127),('go_pending',139),('fast_nested',167)]:
  add(name,[n],['n0'],[[0,0]],[[n,0]])
 for name,n in [('local_binding',193),('closed_binding',31),('closed_mutable',59),('closed_expired',83),('closed_nearest',0),('restart_binding',101)]:add(name,[n])
 xs=[[i+1,'n'+str(i+1) if i<39 else 'nil'] for i in range(40)]
 add('closed_labels',[40],['n0'],xs)
 add('fast_pending',[173],['n0'],xs)
 for n in [0,1,4000]:
  ns=[[i+1,'n'+str(i+1) if i<n-1 else 'nil'] for i in range(n)]
  add('fast_loop',[n],['n0' if n else 'nil'],ns,id='fast_loop_'+str(n))
 for x,n in [('t',149),('nil',151)]:add('fast_choices',[n],[x,'n0'],[[0,0]],[[n,0]],id='fast_choices_'+x)
 add('fast_fallthrough',[157,163],['n0'],[[0,0]],[[157,163]])
 return rows
errors.cases=cases
if __name__=='__main__':errors.run(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
