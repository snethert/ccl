"""Native-first call-error corpus: signalling occurs before dynamic unwinding."""
from pathlib import Path
import json,subprocess
from support import HERE,read,save,require
import conditions
SOURCES={
 'ce_two':'(lambda (a b) (values a b))',
 'ce_zero':'(lambda () 3)',
 'ce_key':'(lambda (&key a) a)',
 'ce_bad':'(lambda (f) (funcall f))',
 'ce_arity':'(lambda (x) (handler-case (ce_two x) (program-error () 17) (condition () 99)))',
 'ce_excess':'(lambda (x) (handler-case (ce_zero x) (program-error () 19) (condition () 99)))',
 'ce_undefined':'(lambda (f) (handler-case (funcall f) (undefined-function () 167) (condition () 99)))',
 'ce_indirect':'(lambda (f) (handler-case (funcall f) (type-error () 23) (condition () 99)))',
 'ce_apply':'(lambda (f args) (handler-case (apply f args) (type-error () 29) (program-error () 31) (condition () 99)))',
 'ce_simple_key':'(lambda () (handler-case (ce_key :bad 1) (simple-condition () 181) (condition () 99)))',
 'ce_simple_odd':'(lambda () (handler-case (ce_key :a) (simple-condition () 191) (condition () 99)))',
 'ce_nonsimple_arity':'(lambda () (handler-case (ce_two 0) (simple-condition () 99) (program-error () 193)))',
 'ce_special_key':'(lambda (dyn_a &key x) (declare (special dyn_a)) x)',
 'ce_keyword_binding':'(lambda (p) (locally (declare (special dyn_a)) (catch p (handler-bind ((program-error (lambda (c) (throw p dyn_a)))) (ce_special_key 61 :bad 1)))))',
 'ce_key_error':'(lambda () (handler-case (ce_key :bad 1) (program-error () 37) (condition () 99)))',
 'ce_odd_key':'(lambda () (handler-case (ce_key :a) (program-error () 41) (condition () 99)))',
 'ce_effects':'(lambda (f p) (handler-case (funcall (progn (rplaca p 43) f) (progn (rplacd p 47) 0)) (condition () (values (car p) (cdr p)))))',
 'ce_before_unwind':'(lambda (f p) (catch p (handler-bind ((type-error (lambda (c) (rplaca p 53) (throw p (cdr p))))) (unwind-protect (ce_bad f) (rplacd p 59)))))',
 'ce_handler_special':'(lambda (f p) (locally (declare (special dyn_a)) (catch p (handler-bind ((type-error (lambda (c) (throw p dyn_a)))) (let ((dyn_a 61)) (declare (special dyn_a)) (ce_bad f))))))',
 'ce_decline':'(lambda (f p) (handler-case (handler-bind ((type-error (lambda (c) (rplaca p 67) (values 1 2 3 4 5)))) (ce_bad f)) (type-error () (car p))))',
 'ce_nested_error':'(lambda (f p) (handler-case (handler-bind ((type-error (lambda (c) (rplaca p 71) (ce_two 0)))) (ce_bad f)) (program-error () (values 73 (car p))) (condition () 99)))',
 'ce_cleanup_error':'(lambda (f p) (handler-case (unwind-protect (ce_bad f) (rplaca p 79) (ce_two 0)) (program-error () (car p)) (condition () 99)))',
 'ce_default':'(lambda (&optional (x (ce_two 0))) x)',
 'ce_default_catch':'(lambda () (handler-case (ce_default) (program-error () 83)))',
 'ce_rest':'(lambda (&rest r) r)',
 'ce_mvc':'(lambda (f) (multiple-value-call (function ce_rest) (handler-case (ce_bad f) (type-error () (values 89 97 101 103 107)))))',
 'ce_retained':'(lambda (f) (multiple-value-prog1 (values 109 113 127 131 137) (handler-case (ce_bad f) (type-error () 0))))',
 'ce_tail':'(lambda (f xs) (if xs (ce_tail f (cdr xs)) (ce_bad f)))',
 'ce_tail_catch':'(lambda (f xs) (handler-case (ce_tail f xs) (type-error () 139)))',
 'ce_escape':'(lambda (f) (lambda () (ce_bad f)))',
 'ce_closure':'(lambda (f) (let ((g (ce_escape f))) (handler-case (funcall g) (type-error () 149))))',
 'ce_unhandled':'(lambda (f p) (handler-bind ((type-error (lambda (c) (rplaca p 173) (values 1 2 3 4 5)))) (ce_bad f)))',
 'ce_unhandled_arity':'(lambda (p) (handler-bind ((program-error (lambda (c) (rplaca p 179)))) (ce_two 0)))',
 'ce_identity':'(lambda (f p) (handler-case (ce_bad f) (type-error (c) (rplaca p c))) (handler-case (ce_bad f) (type-error (c) (if (eq c (car p)) 99 151))))',
 'ce_handler_arity':'(lambda (f) (handler-case (handler-bind ((type-error (function ce_two))) (ce_bad f)) (program-error () 157)))',
 'ce_large_handler':'(lambda (f p) (handler-case (handler-bind ((type-error (lambda (c) (rplaca p 163) (values '+ ' '.join(map(str,range(130)))+')))) (ce_bad f)) (type-error () (car p))))',
 'ce_many':'(lambda (f) (handler-case (ce_bad f) (type-error () (values '+ ' '.join(map(str,range(130)))+'))))',
}
# Preserve condition objects in the identity test only inside local bindings,
# leaving no object-representation dependency in the expected native result.
SOURCES['ce_identity']='(lambda (f) (let ((first nil)) (handler-case (ce_bad f) (type-error (c) (setq first c))) (handler-case (ce_bad f) (type-error (c) (if (eq c first) 99 151)))))'

def cases():
 rows=[]
 def add(name,args,values,nodes=None,after=None,capacity=16,status='RETURN'):
  nodes=nodes or [];rows.append(dict(id=name+'-'+str(len(rows)),function=name,args=args,nodes=nodes,bindings={},capacity=capacity,expected=dict(status=status,values=values,nodes=nodes if after is None else after,specials=[101,103,'unbound'])))
 for name,value in [('ce_arity',17),('ce_excess',19)]:add(name,[7],[value])
 for name,value in [('ce_key_error',37),('ce_odd_key',41),('ce_default_catch',83),('ce_simple_key',181),('ce_simple_odd',191),('ce_nonsimple_arity',193)]:add(name,[],[value])
 for f in [0,7,'nil','n0']:
  ns=[[3,5]]
  add('ce_indirect',[f],[23],ns)
  add('ce_apply',[f,'nil'],[29],ns)
  add('ce_effects',[f,'n0'],[43,47],ns,[[43,47]])
  add('ce_before_unwind',[f,'n0'],[5],ns,[[53,59]])
  add('ce_handler_special',[f,'n0'],[61],ns)
  add('ce_decline',[f,'n0'],[67],ns,[[67,5]])
  add('ce_nested_error',[f,'n0'],[73,71],ns,[[71,5]])
  add('ce_cleanup_error',[f,'n0'],[79],ns,[[79,5]])
  add('ce_identity',[f],[151],ns)
  add('ce_handler_arity',[f],[157],ns)
  add('ce_closure',[f],[149],ns)
  add('ce_large_handler',[f,'n0'],[163],ns,[[163,5]],4)
  add('ce_retained',[f],[109,113,127,131,137],ns,capacity=8)
  add('ce_many',[f],list(range(130)),ns,capacity=132)
 add('ce_keyword_binding',['n0'],[101],[[3,5]])
 add('ce_unhandled',[7,'n0'],[],[[3,5]],[[173,5]],status='DESIGNATOR')
 add('ce_unhandled_arity',['n0'],[],[[3,5]],[[179,5]],status='ARITY')
 add('ce_undefined',['t'],[167])
 add('ce_apply',['f:ce_two','nil'],[31])
 add('ce_apply',['f:ce_zero','n0'],[31],[[1,'nil']])
 add('ce_mvc',[7],['n0'],after=[[89,'n1'],[97,'n2'],[101,'n3'],[103,'n4'],[107,'nil']],capacity=4)
 xs=[[0,'n'+str(i+1) if i<2999 else 'nil'] for i in range(3000)]
 add('ce_tail_catch',[7,'n0'],[139],xs)
 return rows

def compile_suite(evidence,out,backend=None):
 old=(conditions.SOURCES,conditions.cases,conditions.REFUSALS,conditions.IMPLICIT_ERRORS)
 try:
  conditions.SOURCES=SOURCES;conditions.cases=cases;conditions.REFUSALS=[];conditions.IMPLICIT_ERRORS=True
  # No host preconstructed condition is used; handlers operate on native errors.
  conditions.compile_conditions(evidence,out,backend)
 finally:conditions.SOURCES,conditions.cases,conditions.REFUSALS,conditions.IMPLICIT_ERRORS=old

def run(evidence,out,backend=None):
 require(not out.exists(),'NO_OVERWRITE');out.mkdir()
 compile_suite(evidence,out/'compiled',backend)
 s=(HERE/'conditions.mjs').read_text();a=s.index("  for(const fault of ['fixnum'");b=s.index('\n }\n}',a);s=s[:a]+s[b:]
 (out/'harness.mjs').write_text(s)
 command=['/usr/local/bin/node',str(out/'harness.mjs'),str(out/'compiled'),str(out/'execution.json')];save(out/'command.json',command)
 with (out/'execution.log').open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 require(r.returncode==0,'CALL_ERRORS '+str(out/'execution.log'))
 summary=read(out/'execution.json');save(out/'summary.json',summary);return summary
if __name__=='__main__':
 import sys
 r=run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve());print({k:r[k] for k in ('status','modules','comparisons')})
