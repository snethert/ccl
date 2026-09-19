import sys,json,os
from pathlib import Path
import call_errors as errors
errors.SOURCES={
 'r_many_error':'(lambda (x p) (restart-case (handler-bind ((type-error (lambda (c) (invoke-restart :x)))) (unwind-protect (car x) (rplaca p 257))) (:x () (values '+ ' '.join(map(str,range(130)))+'))))',
 'r_zero_error':'(lambda (x p) (restart-case (handler-bind ((type-error (lambda (c) (invoke-restart :x)))) (unwind-protect (car x) (rplaca p 263))) (:x () (values))))',

 'r_svref_datum':'(lambda (v i) (handler-case (svref v i) (type-error (c) (values (type-error-datum c) (if (eq (type-error-expected-type c) (quote simple-vector)) 1 (if (eq (type-error-expected-type c) (quote fixnum)) 2 0))))))',

 'r_arity':'(lambda () (restart-case (handler-bind ((program-error (lambda (c) (invoke-restart :x 251)))) (r_two 0)) (:x (v) v)))',
 'r_undefined':'(lambda (x) (handler-case (funcall x) (undefined-function (c) (cell-error-name c))))',

 'e_early':'(lambda (x p) (rplaca p 233) (rplacd p (car x)))',
 'r_two':'(lambda (a b) (values a b))',
 'r_apply_datum':'(lambda (x) (handler-case (apply (function r_two) x) (type-error (c) (type-error-datum c))))',
 'r_funcall_datum':'(lambda (x) (handler-case (funcall x) (type-error (c) (values (type-error-datum c) (if (eq (car (type-error-expected-type c)) (quote or)) 239 0)))))',
 'r_throw':'(lambda (x) (restart-case (handler-bind ((control-error (lambda (c) (invoke-restart :x 241)))) (throw x 7)) (:x (v) v)))',
 'o_mark':'(lambda (p v) (rplaca p v))',
 'o_nested':'(lambda (p) (catch :x (let ((dyn_a 7)) (declare (special dyn_a)) (unwind-protect (unwind-protect (throw :x (values 3 5)) (o_mark p 11)) (o_mark p 13))) (o_mark p 99)))',
 'o_replace':'(lambda (p x) (handler-case (unwind-protect (unwind-protect (car x) (o_mark p 17) (throw :x 7)) (o_mark p 19)) (control-error () (car p))))',

 'irq_nested':'(lambda (p) (locally (declare (special dyn_a dyn_b)) (ccl:without-interrupts (ccl:without-interrupts (ccl::%interrupt-poll) (rplaca p 197)) (ccl::%interrupt-poll) (values (car p) dyn_b dyn_a))))',
 'irq_unwind':'(lambda (p) (catch :x (ccl:without-interrupts (throw :x (progn (rplaca p 211) 223)))))',
 'irq_gc':'(lambda () (locally (declare (special dyn_a)) (setq dyn_a 227)))',
 'irq_service':'(lambda () (locally (declare (special dyn_b)) (setq dyn_b 229)))',

 'rr_rec':'(lambda (p) (if p (unwind-protect (rr_rec (cdr p)) (values)) 9))',
 'rr_value':'(lambda (p) (restart-case (handler-bind ((storage-condition (lambda (c) (invoke-restart :x 181)))) (rr_rec p)) (:x (v) v)))',
 'rr_twice':'(lambda (p) (values (rr_value p) (rr_value p)))',
 'rr_nested':'(lambda (p) (handler-bind ((storage-condition (lambda (c) (rr_rec p)))) (rr_rec p)))',
 'rr_temp':'(lambda () (restart-case (handler-bind ((storage-condition (lambda (c) (invoke-restart :x 191)))) (multiple-value-call (function (lambda (&rest x) (car x))) (catch :x (values 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129)))) (:x (v) v)))',

 'r_datum':'(lambda (x) (handler-case (car x) (type-error (c) (values (type-error-datum c) (if (eq (type-error-expected-type c) (quote list)) 151 0)))))',
 'r_cell':'(lambda () (locally (declare (special dyn_u)) (handler-case dyn_u (unbound-variable (c) (if (eq (cell-error-name c) (quote dyn_u)) 157 0)))))',
 'r_bounds_class':'(lambda (v i) (handler-case (svref v i) (type-error () 163) (simple-error () 167)))',

 'd_type':'(lambda (x) (restart-case (let ((*debugger-hook* (lambda (c h) (invoke-restart :x 137)))) (car x)) (:x (v) v)))',
 'd_nested':'(lambda (x) (restart-case (let ((*debugger-hook* (lambda (c h) (handler-case (car x) (type-error () (invoke-restart :x 139)))))) (car x)) (:x (v) v)))',
 'd_mask':'(lambda (x) (restart-case (let ((*debugger-hook* (lambda (c h) (if *debugger-hook* 0 (invoke-restart :x 149))))) (car x)) (:x (v) v)))',

 'r_standard':'(lambda (x) (restart-case (handler-bind ((type-error (lambda (c) (invoke-restart (quote use-value) 127)))) (car x)) (use-value (v) v)))',
 'r_bounds':'(lambda (v i) (restart-case (handler-bind ((error (lambda (c) (invoke-restart (quote use-value) 131)))) (svref v i)) (use-value (x) x)))',
 'r_basic':'(lambda (x) (restart-case (handler-bind ((type-error (lambda (c) (invoke-restart :x 17)))) (car x)) (:x (v) v)))',
 'r_error':'(lambda (x) (restart-case (handler-bind ((type-error (lambda (c) (invoke-restart :x 19)))) (funcall x)) (:x (v) v)))',
 'r_unbound':'(lambda () (locally (declare (special dyn_u)) (restart-case (handler-bind ((unbound-variable (lambda (c) (invoke-restart :x 23)))) dyn_u) (:x (v) v))))',
 'r_nil_store':'(lambda () (restart-case (handler-bind ((type-error (lambda (c) (invoke-restart :x 29)))) (rplaca nil 7)) (:x (v) v)))',
 'r_store':'(lambda (x p) (restart-case (handler-bind ((type-error (lambda (c) (invoke-restart :x (car p))))) (rplaca x (progn (rplaca p 31) 7))) (:x (v) v)))',
 'r_bind':'(lambda () (restart-bind ((:x (lambda (v) (values v 37)))) (invoke-restart :x 41)))',
 'r_shadow':'(lambda () (restart-case (restart-case (invoke-restart :x 43) (:x (v) (values v 47))) (:x (v) (values v 99))))',
 'r_duplicate':'(lambda () (restart-case (invoke-restart :x 53) (:x (v) (values v 59)) (:x (v) 99)))',
 'r_identity':'(lambda () (restart-case (invoke-restart (find-restart :x) 61) (:x (v) v)))',
 'r_name':'(lambda () (restart-bind ((:x (lambda () 0))) (if (eq (restart-name (find-restart :x)) :x) 67 99)))',
 'r_expired':'(lambda () (let ((r (restart-bind ((:x (lambda () 0))) (find-restart :x)))) (values (find-restart r) (handler-case (invoke-restart r) (control-error () 71)))))',
 'r_cleanup':'(lambda (p) (restart-case (unwind-protect (invoke-restart :x 73) (rplaca p 79)) (:x (v) (values v (car p)))))',
 'r_missing':'(lambda () (handler-case (invoke-restart :x) (control-error () 83)))',
 'r_many':'(lambda () (restart-case (invoke-restart :x) (:x () (values '+ ' '.join(map(str,range(130)))+'))))',
}
def cases():
 out=[]
 def add(name,args,values,nodes=None,after=None,capacity=16):
  nodes=nodes or [];out.append(dict(id=name+'-'+str(len(out)),function=name,args=args,nodes=nodes,bindings={},capacity=capacity,expected=dict(status='RETURN',values=values,nodes=nodes if after is None else after,specials=[101,103,'unbound'])))
 add('r_many_error',[7,'n0'],list(range(130)),[[3,5]],[[257,5]],132);add('r_zero_error',[7,'n0'],[],[[3,5]],[[263,5]])
 add('r_svref_datum',[7,0],[7,1]);add('r_svref_datum',['v0','nil'],['nil',2])
 add('r_arity',[],[251]);add('r_undefined',['t'],['t'])
 add('r_apply_datum',[7],[7]);add('r_apply_datum',['n0'],['n0'],[[3,7]]);add('r_funcall_datum',[7],[7,239]);add('r_throw',[7],[241]);add('o_nested',['n0'],[3,5],[[3,5]],[[13,5]]);add('o_replace',['n0',7],[19],[[3,5]],[[19,5]])
 add('e_early',[7,'n0'],[],[[3,5]],[[233,5]]);out[-1]['expected']['status']='TYPE'
 add('irq_nested',['n0'],[197,103,101],[[3,5]],[[197,5]]);add('irq_unwind',['n0'],[223],[[3,5]],[[211,5]])
 add('rr_value',['n0'],[9],[[1,'nil']]);add('rr_twice',['n0'],[9,9],[[1,'nil']]);add('rr_nested',['n0'],[9],[[1,'nil']]);add('rr_temp',[],[0]);
 add('r_datum',[7],[7,151]);add('r_cell',[],[157]);add('r_bounds_class',['v0',-1],[167]);add('r_bounds_class',['v0','nil'],[163])
 add('d_type',[7],[137]);add('d_nested',[7],[139]);add('d_mask',[7],[149])
 add('r_standard',[7],[127])
 for i in [-1,4,536870911,'nil']:add('r_bounds',['v0',i],[131])
 add('r_bounds',['v0',2],[7])
 add('r_bounds',[7,0],[131])
 add('r_basic',[7],[17]);add('r_error',[7],[19]);add('r_unbound',[],[23])
 # A literal NIL mutation is folded by the native front end to an error call;
 # runtime invalid operands are covered by r_store instead.
 add('r_store',[7,'n0'],[31],[[3,5]],[[31,5]])
 for name,values in [('r_bind',[41,37]),('r_shadow',[43,47]),('r_duplicate',[53,59]),('r_identity',[61]),('r_name',[67]),('r_expired',['nil',71]),('r_missing',[83])]:add(name,[],values)
 add('r_cleanup',['n0'],[73,79],[[3,5]],[[79,5]])
 add('r_many',[],list(range(130)),capacity=132)
 return out
errors.SOURCES.pop('r_nil_store')
_all_cases=cases
def selected_cases():
 wanted=os.environ.get('LL19_CASES')
 return [c for c in _all_cases() if not wanted or c['function'] in wanted.split(',')]
errors.cases=selected_cases
REFUSALS=[
 ('anonymous-restart','(lambda () (restart-case (values) (nil () 1)))'),
 ('case-options','(lambda () (restart-case (values) (:x () :report "x" 1)))'),
 ('bind-options','(lambda () (restart-bind ((:x (lambda () 1) :report-function (lambda (s) s))) 1))'),
 ('condition-association','(lambda (c) (find-restart :x c))'),
 ('user-case','(lambda (x) (case x (nil 1) (t 2)))'),
]
def compile_suite(evidence,out,backend=None):
 c=errors.conditions;old=(c.SOURCES,c.cases,c.REFUSALS,c.IMPLICIT_ERRORS)
 try:
  c.SOURCES=errors.SOURCES;c.cases=selected_cases;c.REFUSALS=REFUSALS;c.IMPLICIT_ERRORS=True
  c.compile_conditions(evidence,out,backend)
 finally:c.SOURCES,c.cases,c.REFUSALS,c.IMPLICIT_ERRORS=old
errors.compile_suite=compile_suite
if __name__=='__main__':
 out=Path(sys.argv[2]);errors.run(Path(sys.argv[1]),out,Path(sys.argv[3]));print(json.dumps(json.loads((out/'summary.json').read_text())))
