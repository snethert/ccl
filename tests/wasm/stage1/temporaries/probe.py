import sys
from pathlib import Path
import call_errors as errors
errors.SOURCES={
 'irq_gc':'(lambda () (values))','irq_service':'(lambda () (values))',
 'dead':'(lambda () (cons 997 991))',
 'move':'(lambda (x) (dead) (dead) (ccl::%interrupt-poll) x)',
 'p1':'(lambda () (let ((x (cons 1 2))) (car (prog1 x (setq x (move (cons 3 4)))))))',
 'p2':'(lambda () (let ((x (cons 5 6))) (car (prog2 (move nil) x (setq x (move (cons 7 8)))))))',
 'loop_list':'(lambda (xs) (let ((last nil)) (tagbody again (if xs (progn (setq last (move (car xs))) (setq xs (cdr xs)) (go again)) nil)) last))',
 'go_cleanup':'(lambda (p) (tagbody (unwind-protect (go done) (move nil) (rplaca p 11)) (rplaca p 99) done) (car p))',
 'go_binding':'(lambda () (let ((dyn_a 13)) (declare (special dyn_a)) (tagbody (let ((dyn_a 17)) (declare (special dyn_a)) (move nil) (go done)) done) dyn_a))',
 'go_outer':'(lambda (p) (tagbody start (tagbody start (move nil) (rplaca p 19) (go outer)) (rplaca p 99) outer) (car p))',
 'go_replace':'(lambda (p) (tagbody (unwind-protect (go first) (move nil) (go second)) first (rplaca p 99) (go end) second (rplaca p 23) end) (car p))',
}
errors.SOURCES.update({
 'keep_first':'(lambda (a b) a)',
 'nested_prog':'(lambda (p) (let ((x (cons 37 41))) (values (car (prog1 x (prog2 (rplaca p 43) (prog1 (setq x (move (cons 47 53))) (rplacd p (car p))) (setq x (cons 59 61))))) (car x) (car p) (cdr p))))',
 'prog2_order':'(lambda (p) (values (prog2 (rplaca p 67) (car p) (move nil) (rplaca p 71)) (car p)))',
 'parallel_let':'(lambda () (let ((x (cons 73 79)) (y (move (cons 83 89)))) (values (car x) (cdr y))))',
 'sequential_let':'(lambda () (let* ((x (cons 97 101)) (y (move x))) (values (eq x y) (car x))))',
 'assigned':'(lambda () (let ((x (cons 103 107))) (let ((a (prog1 x (setq x (move (cons 109 113)))))) (values (car a) (car x)))))',
 'conditional_yes':'(lambda () (let ((x (cons 127 131))) (values (car (if (move t) x (cons 0 0))) (car x))))',
 'conditional_no':'(lambda () (let ((x (cons 137 139))) (car (if (move nil) (cons 0 0) x))))',
 'call_order':'(lambda (p) (values (car (keep_first (prog1 (cons 149 151) (rplaca p 157)) (progn (rplacd p (car p)) (move nil)))) (car p) (cdr p)))',
 'pending_values':'(lambda () (multiple-value-bind (a b) (multiple-value-prog1 (values (cons 163 167) (cons 173 179)) (move nil)) (values (car a) (cdr b))))',
 'throw_retention':'(lambda () (multiple-value-bind (a b) (catch :x (unwind-protect (throw :x (values (cons 181 191) (cons 193 197))) (move nil))) (values (car a) (cdr b))))',
 'error_retention':'(lambda (bad p) (handler-case (prog1 (cons 199 211) (unwind-protect (progn (move nil) (rplaca bad 0)) (move nil) (rplaca p 223))) (type-error () (car p))))',
 'go_values':'(lambda () (let ((x (cons 227 229))) (values (car (prog1 x (tagbody (setq x (move (cons 233 239))) (go out) (setq x nil) out))) (car x))))',
 'go_outer_cleanup':'(lambda (p) (tagbody (tagbody (unwind-protect (go out) (move nil) (rplaca p 241))) (rplaca p 99) out) (car p))',
 'go_shadow':'(lambda (p) (tagbody same (tagbody (go same) (rplaca p 99) same (move nil) (rplaca p 251)) (go end) end) (car p))',
 'go_error':'(lambda (bad p) (handler-case (tagbody (unwind-protect (go out) (move nil) (rplaca bad 0)) out (rplaca p 99)) (type-error () (rplaca p 257))) (car p))',
 'go_cancel':'(lambda (bad p) (tagbody (unwind-protect (rplaca bad 0) (move nil) (go out)) (rplaca p 99) out (rplaca p 263)) (car p))',
 'loop_capture':'(lambda (xs) (let ((last (cons 269 271))) (let ((get (lambda () (car last)))) (tagbody top (if xs (progn (setq last (move (cons (car xs) 277))) (setq xs (cdr xs)) (go top)))) (funcall get))))',
 'loop_pending':'(lambda (xs) (let ((x (cons 281 283))) (car (prog1 x (tagbody top (if xs (progn (setq x (move (cons (car xs) 293))) (setq xs (cdr xs)) (go top))))))))',
 'loop_binding':'(lambda (xs) (let ((dyn_a 307)) (declare (special dyn_a)) (tagbody top (if xs (let ((dyn_a (car xs))) (declare (special dyn_a)) (move nil) (setq xs (cdr xs)) (go top)))) dyn_a))',
 'nil_integer_tags':'(lambda (p) (tagbody (go nil) 1 (move nil) (rplaca p 311) (go done) nil (go 1) done) (car p))',
 'fatal_cleanup':'(lambda (bad p) (let ((dyn_a (cons 317 331))) (declare (special dyn_a)) (unwind-protect (progn (move nil) (prog1 dyn_a (rplaca bad 0))) (move nil) (rplaca p 337))))',
 'empty_tagbody':'(lambda () (values (tagbody) (tagbody 1 2 nil)))',
 'fallthrough':'(lambda (p) (tagbody a (rplaca p 313) b (move nil) (rplacd p (car p)) c) (values (car p) (cdr p)))',
})
def cases():
 rows=[]
 def add(name,values,args=None,nodes=None,after=None):
  ns=nodes or [];rows.append(dict(id=name,function=name,args=args or [],nodes=ns,bindings={},capacity=16,pending=1,pendingAfter=1,expected=dict(status='RETURN',values=values,nodes=ns if after is None else after,specials=[101,103,'unbound'])))
 add('p1',[1]);add('p2',[5]);add('loop_list',[31],['n0'],[[29,'n1'],[31,'nil']]);add('go_cleanup',[11],['n0'],[[0,0]],[[11,0]]);add('go_binding',[13]);add('go_outer',[19],['n0'],[[0,0]],[[19,0]]);add('go_replace',[23],['n0'],[[0,0]],[[23,0]])
 add('nested_prog',[37,59,43,43],['n0'],[[0,0]],[[43,43]])
 add('prog2_order',[67,71],['n0'],[[0,0]],[[71,0]])
 for n,v in [('parallel_let',[73,89]),('sequential_let',['t',97]),('assigned',[103,109]),('conditional_yes',[127,127]),('conditional_no',[137]),('pending_values',[163,179]),('throw_retention',[181,197]),('go_values',[227,233]),('empty_tagbody',['nil','nil'])]:add(n,v)
 add('call_order',[149,157,157],['n0'],[[0,0]],[[157,157]])
 for n,v in [('go_outer_cleanup',241),('go_shadow',251),('nil_integer_tags',311)]:add(n,[v],['n0'],[[0,0]],[[v,0]])
 for n,v in [('error_retention',223),('go_error',257),('go_cancel',263)]:add(n,[v],[3,'n0'],[[0,0]],[[v,0]])
 xs=[[i+1,'n'+str(i+1) if i<39 else 'nil'] for i in range(40)]
 for n,v in [('loop_capture',40),('loop_pending',281),('loop_binding',307)]:add(n,[v],['n0'],xs)
 add('fallthrough',[313,313],['n0'],[[0,0]],[[313,313]])
 add('fatal_cleanup',[],[3,'n0'],[[0,0]],[[337,0]]);rows[-1]['expected']['status']='TYPE'
 return rows
errors.cases=cases
if __name__=='__main__':errors.run(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
