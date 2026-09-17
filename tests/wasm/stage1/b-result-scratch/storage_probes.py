"""Independent literal scenarios for the per-callee four-word scratch proof."""
from pathlib import Path
from support import HERE, read, save, require
from source_scope import compile_probe
from result_demand import execute

SOURCES = {
 'h_signal':'(lambda (x) (signal x))',
 's_one':'(lambda (x) x)',
 's_zero':'(lambda () (values))',
 's_zero_take':'(lambda () 17)',
 's_four':'(lambda (p) (values (car p) 1 2 3))',
 's_four_take':'(lambda (a b c d) (values d c b a))',
 's_many':'(lambda (p) (rplaca p 101) (values p '+ ' '.join(map(str,range(1,130)))+'))',
 's_many_take':'(lambda ('+' '.join('a'+str(i) for i in range(130))+') (values (car a0) a129))',
 's_saved':'(lambda (p) (multiple-value-prog1 (values 3 5 7 11) (rplaca p 19)))',
 's_saved_zero':'(lambda (p) (multiple-value-prog1 (values) (rplaca p 23)))',
 's_branch':'(lambda (p) (if (car p) (values (car p) (cdr p) 7 11) (values)))',
 's_mutate':'(lambda (p) (let* ((x (car p)) (y (progn (rplaca p 29) (cdr p)))) (setq x y) (values x (car p) (cdr p) 31)))',
 's_special':'(lambda (x) (declare (special x)) (values x 1 2 3))',
 's_unknown_init':'(lambda (p) (let ((x (s_many p))) (car x)))',
 's_unknown_default':'(lambda (p &optional (x (s_many p))) (car x))',
 's_small_default':'(lambda (p &optional (x (values (car p) 1 2 3))) (values x 2 3 4))',
 's_factory':'(lambda (p) (lambda () (values (car p) 1 2 3)))',
 's_invoke':'(lambda (f) (funcall f))',
 'p_zero':'(lambda () (multiple-value-call (function s_zero_take) (s_zero)))',
 'p_four':'(lambda (p) (multiple-value-call (function s_four_take) (s_four p)))',
 'p_saved':'(lambda (p) (multiple-value-call (function s_four_take) (s_saved p)))',
 'p_saved_zero':'(lambda (p) (multiple-value-call (function s_zero_take) (s_saved_zero p)))',
 'p_branch':'(lambda (p) (multiple-value-call (lambda (&rest r) r) (s_branch p)))',
 'p_mutate':'(lambda (p) (multiple-value-call (function s_four_take) (s_mutate p)))',
 'p_unknown_init':'(lambda (p) (multiple-value-call (function s_one) (s_unknown_init p)))',
 'p_unknown_default':'(lambda (p) (multiple-value-call (function s_one) (s_unknown_default p)))',
 'p_small_default':'(lambda (p) (multiple-value-call (function s_four_take) (s_small_default p)))',
 'p_rebound':'(lambda (p) (multiple-value-call (function s_many_take) (s_one p)))',
 'p_closure':'(lambda (p) (multiple-value-call (function s_invoke) (s_factory p)))',
 'p_special':'(lambda (p) (multiple-value-call (function s_four_take) (s_special (car p))))',
 'p_cleanup':'(lambda (p) (unwind-protect (multiple-value-call (function s_one) (s_one (car p))) (rplaca p 37)))',
}
# Use a declared admitted special, not an invented owner index.
SOURCES['s_special']='(lambda (dyn_a) (declare (special dyn_a)) (values dyn_a 1 2 3))'

def cases():
 out=[]
 def add(name,args,values,before=None,after=None,bindings=None):
  before=[] if before is None else before
  out.append(dict(id=name+'-'+str(len(out)),function=name,args=args,nodes=before,bindings=bindings or {},capacity=4,
                  expected=dict(status='RETURN',values=values,nodes=before if after is None else after,specials=[101,103,'unbound'])))
 add('p_zero',[],[17])
 for p in ([3,5],['nil',5]):
  add('p_four',['n0'],[3,2,1,p[0]],[p])
  add('p_small_default',['n0'],[4,3,2,p[0]],[p])
  add('p_closure',['n0'],[p[0],1,2,3],[p])
  add('p_special',['n0'],[3,2,1,p[0]],[p])
 add('p_saved',['n0'],[11,7,5,3],[[3,5]],[[19,5]])
 add('p_saved_zero',['n0'],[17],[[3,5]],[[23,5]])
 add('p_mutate',['n0'],[31,5,29,5],[[3,5]],[[29,5]])
 add('p_branch',['n0'],['nil'],[['nil',5]])
 add('p_branch',['n0'],['n1'],[[3,5]],[[3,5],[3,'n2'],[5,'n3'],[7,'n4'],[11,'nil']])
 add('p_unknown_init',['n0'],[101],[[3,5]],[[101,5]])
 add('p_unknown_default',['n0'],[101],[[3,5]],[[101,5]])
 add('p_rebound',['n0'],[101,129],[[3,5]],[[101,5]],{'s_one':'s_many'})
 add('p_cleanup',['n0'],[3],[[3,5]],[[37,5]])
 return out


def run(evidence,out):
 require(not out.exists(),'NO_OVERWRITE');out.mkdir()
 compile_probe(evidence,out/'compiled',None,SOURCES,cases(),[])
 require(execute(out/'compiled',HERE/'conditions.mjs',out/'execution.json')==0,'STORAGE_PROBE_EXECUTION')
 contracts=read(out/'compiled/root-contracts.json')
 for n in ('s_one','s_zero','s_four','s_saved','s_saved_zero','s_branch','s_mutate','s_special','s_small_default','s_factory'):
  require(contracts[n]['small_scratch'],'PROVED_SMALL '+n)
 for n in ('s_many','s_unknown_init','s_unknown_default','s_invoke'):
  require(not contracts[n]['small_scratch'],'UNPROVEN_RETAINS_DYNAMIC '+n)
 summary=dict(status='PASS',cases=len(cases()),comparisons=read(out/'execution.json')['comparisons'],modules=len(contracts),small_scratch=sum(r['small_scratch'] for r in contracts.values()))
 save(out/'summary.json',summary);return summary

if __name__=='__main__':
 import sys
 print(run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
