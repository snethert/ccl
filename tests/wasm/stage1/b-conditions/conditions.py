"""Literal condition-dispatch corpus; native CCL executes unmodified CL forms."""
import json,subprocess,sys
from pathlib import Path
from support import HERE,require,read,save,compile_cases
KINDS=['condition','simple-condition','simple-error','type-error','control-error','simple-warning']
MASKS=[1,9,31,39,71,393]
SOURCES={
 'h_signal':'(lambda (x) (signal x))',
 'h_error':'(lambda (x) (error x))',
 'h_case':'(lambda (x) (handler-case (error x) (condition (c) (values c 17))))',
 'h_types':'(lambda (x) (handler-case (error x) (type-error (c) (values 1 c)) (simple-error (c) (values 2 c)) (control-error (c) (values 3 c)) (condition (c) (values 4 c))))',
 'h_novar':'(lambda (x) (handler-case (error x) (error () 11) (condition () 13)))',
 'h_order':'(lambda (x p) (handler-bind ((condition (lambda (c) (rplaca p c))) (condition (lambda (c) (rplacd p c)))) (values (signal x) (car p) (cdr p))))',
 'h_decline':'(lambda (x p) (handler-bind ((condition (lambda (c) (rplaca p c) (values 1 2 3 4 5)))) (values (signal x) (car p))))',
 'h_cluster':'(lambda (x p) (catch p (handler-bind ((condition (lambda (c) (throw p (values c 19))))) (handler-bind ((condition (lambda (c) (rplaca p 23) (signal c))) (condition (lambda (c) (rplaca p 29)))) (signal x)))))',
 'h_nested':'(lambda (x p) (handler-bind ((condition (lambda (c) (rplacd p c)))) (handler-bind ((error (lambda (c) (rplaca p c)))) (signal x)) (values (car p) (cdr p))))',
 'h_cleanup':'(lambda (x p) (handler-case (unwind-protect (error x) (rplaca p 31)) (condition (c) (values c (car p)))))',
 'h_cleanup_error':'(lambda (x y p) (handler-case (unwind-protect (error x) (rplaca p 37) (error y)) (type-error (c) (values 1 c (car p))) (condition (c) (values 2 c (car p)))))',
 'h_special':'(lambda (x) (locally (declare (special dyn_a)) (handler-case (let ((dyn_a 41)) (error x)) (condition (c) (values c dyn_a)))))',
 'h_normal':'(lambda (x) (handler-case (values x 43 47) (condition () 0) (:no-error (a b c) (values c b a))))',
 'h_noerror_zero':'(lambda () (handler-case (values) (condition () 0) (:no-error () 53)))',
 'h_noerror_error':'(lambda (x) (handler-case (error x) (condition (c) (values 59 c)) (:no-error (v) v)))',
 'h_handler_error':'(lambda (x y p) (handler-case (handler-bind ((condition (lambda (c) (rplaca p c) (error y)))) (error x)) (condition (c) (values c (car p)))))',
 'h_same_cluster':'(lambda (x p) (handler-case (handler-bind ((condition (lambda (c) (rplaca p 61) (error c))) (condition (lambda (c) (rplaca p 67)))) (signal x)) (condition (c) (values c (car p)))))',
 'h_reenter':'(lambda (x p) (handler-bind ((condition (lambda (c) (handler-case (error c) (condition () (rplaca p 71)))))) (signal x) (values (signal x) (car p))))',
 'h_empty':'(lambda (x) (handler-bind () (handler-case (values x 73))))',
 'h_handler_values':'(lambda (x) (catch x (handler-bind ((condition (lambda (c) (throw x (values c 1 2 3 4 5))))) (signal x))))',
 'h_function_handler':'(lambda (x f) (handler-bind ((condition f)) (signal x)))',
 'h_transfer':'(lambda (x xs) (if xs (h_transfer x (cdr xs)) (error x)))',
 'h_deep':'(lambda (x xs p) (handler-case (unwind-protect (h_transfer x xs) (rplaca p 79)) (condition (c) (values c (car p)))))',
 'h_bind_entry':'(lambda (x p) (handler-bind ((condition (progn (rplaca p 83) (lambda (c) (rplacd p c))))) (values (signal x) (car p) (cdr p))))',
 'h_handler_restore':'(lambda (x p) (progn (handler-case (error x) (condition () (rplaca p 89))) (signal x) (car p)))',
 'h_case_mask':'(lambda (x p) (handler-case (handler-case (error x) (condition (c) (rplaca p 97) (error c))) (condition (c) (values c (car p)))))',
 'h_escaper':'(lambda (x) (lambda () (error x)))',
 'h_closure':'(lambda (x) (let ((f (h_escaper x))) (handler-case (funcall f) (condition (c) c))))',
 'h_mvc':'(lambda (x) (multiple-value-call (lambda (&rest r) r) (handler-case (error x) (condition (c) (values c 101 103 107 109)))) )',
}
SOURCES['h_discard_many']='(lambda (x p) (handler-bind ((condition (lambda (c) (rplaca p c) (values '+ ' '.join(map(str,range(130)))+')))) (values (signal x) (car p))))'
SOURCES['h_return_many']='(lambda (x) (handler-case (error x) (condition (c) (values '+ ' '.join(['c']*130)+'))))'
SOURCES['h_noerror_many']='(lambda (x) (handler-case (values '+ ' '.join(['x']*130)+') (condition () 0) (:no-error (&rest r) (car r))))'
TYPES={'condition':1,'serious-condition':2,'error':4,'simple-condition':8,'simple-error':16,'type-error':32,'control-error':64,'warning':128,'simple-warning':256}
for kind in TYPES:SOURCES['h_match_'+kind]='(lambda (x) (handler-case (error x) ('+kind+' () 1) (condition () 0)))'
REFUSALS=[('unknown-type',"(lambda (x) (handler-case (signal x) (stream-error () 1)))"),('compound-type',"(lambda (x) (handler-bind (((or error warning) (lambda (c) c))) (signal x)))"),('condition-constructor',"(lambda () (make-condition 'simple-error))"),('message-string','(lambda () (error "message"))'),('format-arguments','(lambda (x) (error x 1))'),('restart-case','(lambda (x) (restart-case (error x) (continue () 7)))')]
def modules():return [{'name':n,'source':s} for n,s in SOURCES.items()]
def cases():
 out=[]
 def add(n,args,values,status='RETURN',nodes=None,after=None,capacity=16):
  before=nodes or [];out.append(dict(id=n+'-'+str(len(out)),function=n,args=args,nodes=before,bindings={},capacity=capacity,expected=dict(status=status,values=values,nodes=before if after is None else after,specials=[101,103,'unbound'])))
 for i in range(6):
  q='q'+str(i)
  for kind,mask in TYPES.items():add('h_match_'+kind,[q],[1 if MASKS[i]&mask else 0])
  add('h_discard_many',[q,'n0'],['nil',q],nodes=[[3,5]],after=[[q,5]],capacity=4);add('h_return_many',[q],[q]*130,capacity=132);add('h_noerror_many',[q],[q],capacity=4);
  add('h_signal',[q],['nil']);add('h_error',[q],[],status='UNHANDLED')
  add('h_case',[q],[q,17]);add('h_types',[q],[{2:2,3:1,4:3}.get(i,4),q]);add('h_novar',[q],[11 if i in (2,3,4) else 13])
  add('h_order',[q,'n0'],['nil',q,q],nodes=[[3,5]],after=[[q,q]])
  add('h_decline',[q,'n0'],['nil',q],nodes=[[3,5]],after=[[q,5]])
  add('h_cluster',[q,'n0'],[q,19],nodes=[[3,5]],after=[[23,5]])
  add('h_nested',[q,'n0'],[q if i in (2,3,4) else 3,q],nodes=[[3,5]],after=[[q if i in (2,3,4) else 3,q]])
  add('h_cleanup',[q,'n0'],[q,31],nodes=[[3,5]],after=[[31,5]])
  add('h_special',[q],[q,101]);add('h_normal',[q],[47,43,q]);add('h_noerror_error',[q],[59,q])
  add('h_same_cluster',[q,'n0'],[q,61],nodes=[[3,5]],after=[[61,5]])
  add('h_reenter',[q,'n0'],['nil',71],nodes=[[3,5]],after=[[71,5]])
  add('h_empty',[q],[q,73]);add('h_handler_values',[q],[q,1,2,3,4,5])
  add('h_bind_entry',[q,'n0'],['nil',83,q],nodes=[[3,5]],after=[[83,q]])
  add('h_handler_restore',[q,'n0'],[89],nodes=[[3,5]],after=[[89,5]])
  add('h_case_mask',[q,'n0'],[q,97],nodes=[[3,5]],after=[[97,5]])
  add('h_closure',[q],[q])
  add('h_mvc',[q],['n0'],after=[[q,'n1'],[101,'n2'],[103,'n3'],[107,'n4'],[109,'nil']],capacity=4)
 add('h_noerror_zero',[],[53])
 for a,b in [(2,3),(3,2),(3,3)]:
  add('h_cleanup_error',['q'+str(a),'q'+str(b),'n0'],[1 if b==3 else 2,'q'+str(b),37],nodes=[[3,5]],after=[[37,5]])
  add('h_handler_error',['q'+str(a),'q'+str(b),'n0'],['q'+str(b),'q'+str(a)],nodes=[[3,5]],after=[['q'+str(a),5]])
 # Stack-independent tail recursion in the signal-producing path.
 xs=[[3,5]]+[[0,'n'+str(i+2) if i<2999 else 'nil'] for i in range(3000)]
 add('h_deep',['q3','n1','n0'],['q3',79],nodes=xs,after=[[79,5]]+xs[1:])
 return out

def compile_conditions(evidence,out,backend=None):
 import corpus
 old=(corpus.modules,corpus.cases,corpus.lisp_input)
 def lisp_input():
  def lit(v):return '('+' '.join(map(lit,v))+')' if isinstance(v,list) else json.dumps(v) if isinstance(v,str) else str(v)
  return '(in-package "CL-USER")\n(defparameter *condition-suite* t)\n'+''.join('(defparameter '+n+" '"+lit(v)+')\n' for n,v in [('*call-sources*',[[x['name'],x['source']] for x in modules()]),('*call-cases*',[[c['id'],c['function'],c['nodes'],c['args'],[]] for c in cases()]),('*call-refusals*',[list(x) for x in REFUSALS])])
 try:
  corpus.modules=modules;corpus.cases=cases;corpus.lisp_input=lisp_input
  compile_cases(evidence,out,backend)
 finally:corpus.modules,corpus.cases,corpus.lisp_input=old

def run(evidence,out,backend=None):
 require(not out.exists(),'NO_OVERWRITE');out.mkdir()
 compile_conditions(evidence,out/'compiled',backend)
 command=['/usr/local/bin/node',str(HERE/'conditions.mjs'),str(out/'compiled'),str(out/'execution.json')]
 save(out/'command.json',command)
 with (out/'execution.log').open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 require(r.returncode==0,'CONDITION_EXECUTION '+str(out/'execution.log'))
 return read(out/'execution.json')
if __name__=='__main__':
 run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
