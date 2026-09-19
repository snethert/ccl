"""Compile and evaluate source in pristine native CCL before target execution."""
import sys,json
from pathlib import Path
import call_errors as errors
errors.SOURCES={
 'pair':'(lambda (a b) (cons a b))',
 'read_pair':'(lambda (p) (values (car p) (cdr p)))',
 'nested':'(lambda (p) (let ((a (cons p p))) (let ((b (cons a a))) (values (eq (car b) (cdr b)) (eq (car (car b)) p) (car p)))))',
 'order':'(lambda (p) (cons (progn (rplaca p 13) (cons p nil)) (progn (rplacd p 17) (cons p nil))))',
 'make_reader':'(lambda (x) (lambda () (car x)))',
 'early_cell':'(lambda () (let* ((x (gather 211 nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil)) (f (lambda () (car x)))) (funcall f)))',
 'make_alloc_reader':'(lambda (x) (lambda () (gather nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil) (car x)))',
 'closure_inside':'(lambda () (let ((f (make_alloc_reader (cons 197 199)))) (funcall f)))',
 'closure':'(lambda () (let* ((p (cons 19 23)) (f (make_reader p))) (pair nil nil) (pair nil nil) (funcall f)))',
 'captured':'(lambda (p) (let* ((x (cons p nil)) (f (lambda () (car (car x))))) (setq x (cons (cons 29 31) nil)) (funcall f)))',
 'siblings':'(lambda () (let* ((x (cons 37 41)) (read (lambda () (car x))) (write (lambda (v) (setq x (cons v 43))))) (funcall write 47) (funcall read)))',
 'local':'(lambda (xs) (labels ((walk (x last) (if x (walk (cdr x) (cons (car x) last)) (car last)))) (walk xs nil)))',
 'mutual':'(lambda (xs) (labels ((a (x) (if x (progn (cons (car x) nil) (b (cdr x))) 53)) (b (x) (if x (progn (cons (car x) nil) (a (cdr x))) 59))) (a xs)))',
 'gather':'(lambda (&rest xs) xs)',
 'rest_read':'(lambda (x y z) (let ((r (gather x y z))) (values (eq (car r) x) (eq (car (cdr r)) y) (car (car (cdr (cdr r)))))))',
 'apply_rest':'(lambda (xs) (apply (function gather) xs))',
 'literal_apply':'(lambda (p) (apply (lambda (&rest xs) (cons (car xs) (car xs))) (cons p nil)))',
 'inline_rest':'(lambda (p) ((lambda (&rest xs) (car xs)) p p p p p p p p p))',
 'default':'(lambda (&optional (p (cons 61 67))) (let ((f (lambda () (cdr p)))) (pair nil nil) (funcall f)))',
 'key_default':'(lambda (&key (p (cons 71 73))) (let ((f (lambda () (car p)))) (pair nil nil) (funcall f)))',
 'cleanup':'(lambda (p) (unwind-protect (cons p p) (rplaca p 79) (pair nil nil)))',
 'throwing':'(lambda (p) (catch p (unwind-protect (throw p (cons p p)) (pair nil nil) (rplacd p 83))))',
 'block_exit':'(lambda (p) (block done (unwind-protect (return-from done (cons p p)) (pair nil nil) (rplacd p 89))))',
 'special':'(lambda (p) (let ((dyn_a (cons p nil))) (declare (special dyn_a)) (pair nil nil) (pair nil nil) (car (car dyn_a))))',
 'many_values':'(lambda () (values (cons 97 101) (cons 103 107) (cons 109 113)))',
 'mvc':'(lambda () (multiple-value-call (function gather) (values (cons 127 131) (cons 137 139)) (values (cons 149 151) (cons 157 163))))',
 'eq_operands':'(lambda (p) (let ((x (cons p nil))) (eq x (progn (pair nil nil) (pair nil nil) x))))',
 'failure_live':'(lambda (p) (let ((x (cons 179 181))) (rplacd p x) (unwind-protect (gather x x x x x x x x x x x x x x x x) (rplaca x 191)) p))',
 'failed_cleanup':'(lambda (p) (unwind-protect (gather p p p p p p p p p p p p p p p p) (rplaca p 173)))',
}
def cases():
 out=[]
 def add(name,args=None,nodes=None):out.append(dict(id=name,function=name,args=args or [],nodes=nodes or [],bindings={},capacity=16))
 add('pair',[7,11]);add('read_pair',['n0'],[[7,11]])
 for name in ['nested','order','captured','inline_rest','cleanup','throwing','block_exit','special','eq_operands','failed_cleanup','failure_live','literal_apply']:add(name,['n0'],[[7,11]])
 for name in ['closure','early_cell','closure_inside','siblings','default','key_default','many_values','mvc']:add(name)
 xs=[[i,'n'+str(i+1) if i<79 else 'nil'] for i in range(80)]
 add('local',['n0'],xs);add('mutual',['n0'],xs)
 add('gather',['n0','n1','n0'],[[3,5],[7,11]]);add('rest_read',['n0','n1','n2'],[[3,5],[7,11],[17,19]]);add('apply_rest',['n0'],[[3,'n1'],[5,'n2'],[7,'nil']])
 for c in out:
  n=c['function'];ns=[list(x) for x in c['nodes']];v={'nested':['t','t',7],'closure':[19],'closure_inside':[197],'early_cell':[211],'captured':[29],'siblings':[47],'local':[79],'mutual':[53],'default':[67],'key_default':[71],'special':[7],'eq_operands':['t'],'rest_read':['t','t',17],'inline_rest':['n0'],'read_pair':[7,11]}.get(n)
  if n=='literal_apply':v=['n1'];ns=[[7,11],['n0','n0']]
  if n=='pair':v=['n0'];ns=[[7,11]]
  if n=='order':v=['n1'];ns=[[13,17],['n2','n3'],['n0','nil'],['n0','nil']]
  if n in ('cleanup','throwing','block_exit'):v=['n1'];ns=[([79,11] if n=='cleanup' else [7,83 if n=='throwing' else 89]),['n0','n0']]
  if n=='many_values':v=['n0','n1','n2'];ns=[[97,101],[103,107],[109,113]]
  if n in ('gather','apply_rest','failed_cleanup'):
   items=['n0','n1','n0'] if n=='gather' else [3,5,7] if n=='apply_rest' else ['n0']*16
   if n=='failed_cleanup':ns[0][0]=173
   start=len(ns);v=['n'+str(start)];ns.extend([[x,'n'+str(start+i+1) if i+1<len(items) else 'nil'] for i,x in enumerate(items)])
  if n=='failure_live':v=['n0'];ns=[[7,'n1'],[191,181]]
  if n=='mvc':v=['n0'];ns=[['n1','n2'],[127,131],['n3','n4'],[137,139],['n5','n6'],[149,151],['n7','nil'],[157,163]]
  assert v is not None,n
  c['expected']=dict(status='RETURN',values=v,nodes=ns,specials=[101,103,'unbound'])
 return out
errors.cases=cases
if __name__=='__main__':
 e,out,backend=map(Path,sys.argv[1:4]);errors.compile_suite(e,out,backend)
