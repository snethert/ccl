"""Executed from the derived, reviewed constants-layout harness."""
import json,sys
from pathlib import Path
import call_errors as errors
errors.SOURCES={
 'ap_target':'(lambda (&rest xs) xs)',
 'ap_leaf':'(lambda (xs) (apply (function ap_target) xs))',
 'ap_catch':'(lambda (xs) (handler-case (ap_leaf xs) (type-error () 17) (condition () 99)))',
 'ap_normal':'(lambda (xs) (apply (function ap_target) xs) 19)',
 'ap_nontail':'(lambda (xs) (handler-case (ap_normal xs) (type-error () 23) (condition () 99)))',
 'ap_effects':'(lambda (xs p) (handler-case (apply (progn (rplaca p 31) (function ap_target)) (progn (rplacd p 37) 0) xs) (type-error () (values (car p) (cdr p)))))',
 'ap_cleanup':'(lambda (xs p) (handler-case (unwind-protect (ap_leaf xs) (rplaca p 41)) (type-error () (car p))))',
 'ap_binding':'(lambda (xs) (locally (declare (special dyn_a)) (catch xs (let ((dyn_a 43)) (handler-bind ((type-error (lambda (c) (throw xs dyn_a)))) (ap_leaf xs))))))',
 'ap_outer_binding':'(lambda (xs) (locally (declare (special dyn_a)) (handler-case (let ((dyn_a 47)) (ap_leaf xs)) (type-error () dyn_a))))',
 'ap_decline':'(lambda (xs p) (handler-case (handler-bind ((type-error (lambda (c) (rplaca p 53)))) (ap_leaf xs)) (type-error () (car p))))',
 'ap_replace':'(lambda (xs p) (handler-case (unwind-protect (ap_leaf xs) (rplaca p 59) (ap_leaf xs)) (type-error () (car p))))',
 'ap_many':'(lambda (xs) (handler-case (ap_leaf xs) (type-error () (values '+ ' '.join(map(str,range(130)))+'))))',
 'ap_producer':'(lambda (xs) (multiple-value-call (lambda (&rest r) r) (handler-case (ap_leaf xs) (type-error () (values 61 67 71 73 79)))))',
 'ap_retained':'(lambda (xs) (multiple-value-prog1 (values 83 89 97 101 103) (handler-case (ap_leaf xs) (type-error () 0))))',
 'ap_tail':'(lambda (xs path) (if path (ap_tail xs (cdr path)) (ap_leaf xs)))',
 'ap_deep':'(lambda (xs path) (handler-case (ap_tail xs path) (type-error () 107)))',
 'ap_escape':'(lambda (xs) (lambda () (ap_leaf xs)))',
 'ap_closure':'(lambda (xs) (let ((f (ap_escape xs))) (handler-case (funcall f) (type-error () 109))))',
 'ap_unhandled':'(lambda (xs p) (handler-bind ((type-error (lambda (c) (rplaca p 113)))) (ap_leaf xs)))',
}
def cases():
 out=[]
 def add(name,args,values,nodes=None,after=None,capacity=16,status='RETURN'):
  nodes=nodes or [];out.append(dict(id=name+'-'+str(len(out)),function=name,args=args,nodes=nodes,bindings={},capacity=capacity,expected=dict(status=status,values=values,nodes=nodes if after is None else after,specials=[101,103,'unbound'])))
 for tail,ns in [(7,[[3,5]]),('t',[[3,5]]),('n1',[[3,5],[1,7]]),('n1',[[3,5],[1,'n2'],[2,7]])]:
  for name,value in [('ap_catch',17),('ap_nontail',23),('ap_binding',43),('ap_outer_binding',101),('ap_closure',109)]:add(name,[tail],[value],ns)
  add('ap_effects',[tail,'n0'],[31,37],ns,[[31,37]]+ns[1:])
  for name,value in [('ap_cleanup',41),('ap_decline',53),('ap_replace',59)]:add(name,[tail,'n0'],[value],ns,[[value,5]]+ns[1:])
  add('ap_many',[tail],list(range(130)),ns,capacity=132)
  add('ap_retained',[tail],[83,89,97,101,103],ns,capacity=8)
  start=len(ns);more=[[v,'n'+str(start+i+1) if i<4 else 'nil'] for i,v in enumerate([61,67,71,73,79])]
  add('ap_producer',[tail],['n'+str(start)],ns,ns+more,capacity=4)
  add('ap_unhandled',[tail,'n0'],[],ns,[[113,5]]+ns[1:],status='TYPE')
 add('ap_catch',['nil'],['nil'])
 add('ap_catch',['n0'],['n1'],[[3,'nil']],[[3,'nil'],[3,'nil']])
 add('ap_leaf',[7],[],status='TYPE')
 xs=[[0,'n'+str(i+1) if i<2999 else 'nil'] for i in range(3000)]
 add('ap_deep',[7,'n0'],[107],xs)
 return out
errors.cases=cases
if __name__=='__main__':
 out=Path(sys.argv[2]);errors.run(Path(sys.argv[1]),out,Path(sys.argv[3]))
 print(json.dumps(json.loads((out/'summary.json').read_text())))
