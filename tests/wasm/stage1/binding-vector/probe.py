import sys,json,os
from pathlib import Path
import call_errors as errors
errors.SOURCES={
 'v_read':'(lambda (s) (symbol-value s))',
 'v_set':'(lambda (s v) (set s v))',
 'v_global':'(lambda (s) (let ((dyn_a 7)) (values (symbol-value s) dyn_a)))',
 'v_bound':'(lambda (s) (let ((dyn_a 7)) (declare (special dyn_a)) (values (symbol-value s) (set s 11) dyn_a)))',
 'v_nested':'(lambda (s) (let ((dyn_a 7)) (declare (special dyn_a)) (values dyn_a (let ((dyn_b 13)) (declare (special dyn_b)) (values (symbol-value s) (set s 17))) dyn_a)))',
 'v_throw':'(lambda (s p) (catch :x (let ((dyn_a 19)) (declare (special dyn_a)) (unwind-protect (let ((dyn_b 23)) (declare (special dyn_b)) (throw :x (values (symbol-value s) dyn_b))) (rplaca p dyn_a)))))',
 'v_error':'(lambda (s) (handler-case (let ((dyn_a 29) (dyn_b 31)) (declare (special dyn_a dyn_b)) (set s 37) (car s)) (type-error () (symbol-value s))))',
 'v_unbound':'(lambda (s) (handler-case (symbol-value s) (unbound-variable (c) (if (eq (cell-error-name c) s) 41 99))))',
 'v_bad':'(lambda (s) (handler-case (symbol-value s) (type-error (c) (type-error-datum c))))',
 'v_order':'(lambda (s p) (set (progn (rplaca p 43) s) (progn (rplacd p (car p)) 47)))',
 'v_progv':'(lambda (s xs vs) (progv xs vs (values (symbol-value s) (set s 53) (symbol-value s))))',
 'v_capture':'(lambda (s) (let ((x 59)) (let ((dyn_a 61)) (declare (special dyn_a)) (let ((f (lambda () (setq x (symbol-value s))))) (funcall f) (values x dyn_a)))))',
 'v_default':'(lambda (s &optional (dyn_a 67) (dyn_b (symbol-value s))) (declare (special dyn_a dyn_b)) (values dyn_a dyn_b))',
 'v_poll':'(lambda (s) (let ((dyn_a 71)) (declare (special dyn_a)) (ccl::%interrupt-poll) (values dyn_a (symbol-value s))))',
 'irq_gc':'(lambda () (values))','irq_service':'(lambda () (values))',
 'v_host':'(lambda (s) (let ((dyn_a 73)) (declare (special dyn_a)) (v_read s)))',
 'v_gc_chain':'(lambda (s) (ccl::%interrupt-poll) (let ((dyn_a 89)) (declare (special dyn_a)) (ccl::%interrupt-poll) (let ((dyn_b 97)) (declare (special dyn_b)) (ccl::%interrupt-poll) (values (symbol-value s) dyn_b))))',
 'v_constant_set':'(lambda (s p) (handler-case (set s (progn (rplaca p 113) 7)) (simple-error () (car p)) (error () 999)))',
 'v_bad_set':'(lambda (s p) (handler-case (set s (progn (rplaca p 127) 7)) (type-error (c) (values (type-error-datum c) (car p)))))',
 'v_missing':'(lambda (s xs) (progv xs nil (handler-case (symbol-value s) (unbound-variable () (set s 131))) (symbol-value s)))',
 'v_cleanup_growth':'(lambda (s p) (catch :x (let ((dyn_a 137)) (declare (special dyn_a)) (unwind-protect (throw :x dyn_a) (let ((dyn_b 139)) (declare (special dyn_b)) (rplaca p (symbol-value s)))))))',
 'v_shadow':'(lambda (s) (flet ((symbol-value (s) (values s 149)) (set (s v) (values v s))) (values (symbol-value s) (set s 151))))',
 'v_shadow_labels':'(lambda (s xs) (labels ((symbol-value (s xs) (if xs (symbol-value s (cdr xs)) s))) (symbol-value s xs)))',
 'v_many':'(lambda (s xs vs) (progv xs vs (let ((dyn_b 79)) (declare (special dyn_b)) (values (symbol-value s) dyn_b))))',
}
def cases():
 out=[]
 def add(n,args,values,nodes=None,after=None,specials=None,**extras):
  nodes=nodes or [];out.append(dict(id=n+'-'+str(len(out)),function=n,args=args,nodes=nodes,bindings={},capacity=16,expected=dict(status='RETURN',values=values,nodes=nodes if after is None else after,specials=specials or [101,103,'unbound']),**extras))
 add('v_read',['s:dyn_a'],[101]);add('v_read',['nil'],['nil']);add('v_read',['t'],['t'])
 add('v_set',['s:dyn_a',7],[7],specials=[7,103,'unbound']);add('v_set',['s:dyn_u',5],[5],specials=[101,103,5])
 add('v_global',['s:dyn_a'],[101,7]);add('v_bound',['s:dyn_a'],[7,11,11]);add('v_nested',['s:dyn_a'],[7,7,17])
 add('v_throw',['s:dyn_a','n0'],[19,23],[[3,5]],[[19,5]]);add('v_error',['s:dyn_a'],[101]);add('v_unbound',['s:dyn_u'],[41])
 add('v_bad',[7],[7]);add('v_bad',['n0'],['n0'],[[3,5]])
 add('v_order',['s:dyn_b','n0'],[47],[[3,5]],[[43,43]],specials=[101,47,'unbound'])
 add('v_capture',['s:dyn_a'],[61,61]);add('v_default',['s:dyn_a'],[67,67]);add('v_host',['s:dyn_a'],[73])
 add('v_gc_chain',['s:dyn_a'],[89,97],pending=1,pendingAfter=1)
 add('v_poll',['s:dyn_a'],[71,71],pending=1,pendingAfter=1)
 add('v_progv',['s:dyn_a','n0','n2'],[83,53,53],[['s:dyn_a','n1'],['s:dyn_a','nil'],[81,'n3'],[83,'nil']])
 for name,args,values in [
  ('v_read',['s:dyn_b'],[103]),('v_set',['s:dyn_b',109],[109]),
  ('v_bound',['s:dyn_b'],[103,11,7]),('v_nested',['s:dyn_b'],[7,13,7]),
  ('v_bad',['t'],['t']),('v_bad',['nil'],['nil']),
  ('v_error',['s:dyn_b'],[103]),('v_unbound',['s:dyn_a'],[101]),
  ('v_capture',['s:dyn_b'],[103,61]),('v_default',['s:dyn_b'],[67,103]),
 ]:
  specials=[101,109,'unbound'] if name=='v_set' else [101,11,'unbound'] if name=='v_bound' else None
  add(name,args,values,specials=specials)
 add('v_constant_set',['nil','n0'],[113],[[3,5]],[[113,5]])
 add('v_constant_set',['t','n0'],[113],[[3,5]],[[113,5]])
 add('v_bad_set',[7,'n0'],[7,127],[[3,5]],[[127,5]])
 add('v_bad_set',['n0','n1'],['n0',127],[[1,3],[5,7]],[[1,3],[127,7]])
 add('v_read',[':a'],[':a'])
 add('v_constant_set',[':a','n0'],[113],[[3,5]],[[113,5]])
 add('v_missing',['s:dyn_a','n0'],[131],[['s:dyn_a','n1'],['s:dyn_a','nil']])
 add('v_cleanup_growth',['s:dyn_a','n0'],[137],[[3,5]],[[137,5]])
 add('v_shadow',['s:dyn_a'],['s:dyn_a',151])
 add('v_shadow_labels',['s:dyn_b','n0'],['s:dyn_b'],[[0,'n1'],[0,'nil']])
 return out
_all_cases=cases
def selected():
 wanted=os.environ.get('LL17_CASES')
 return [c for c in _all_cases() if not wanted or c['function'] in wanted.split(',')]
errors.cases=selected
if __name__=='__main__':errors.run(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
