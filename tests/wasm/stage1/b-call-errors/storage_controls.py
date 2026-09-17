"""Faults in scratch eligibility, expansion traversal and dynamic delivery."""
from pathlib import Path
from support import HERE, require, read, save
from source_scope import compile_probe
from storage_probes import SOURCES,cases
from result_demand import execute


def mutations(source):
 a=source.index('(defun b-small-result-scratch-p ');b=source.index('(defun b-one-module ',a)
 proof=source[a:b];result={}
 def change(name,old,new):
  require(proof.count(old)==1,'PROOF_MUTANT_SITE '+name)
  result[name]=source[:a]+proof.replace(old,new)+source[b:]
 change('always-small','(walk ir)))','(declare (ignore ir)) t))')
 change('wide-values-small','(<= (length (first a)) 4)','(<= (length (first a)) 130)')
 change('unknown-calls-small',"'(nil t ccl::fixnum", "'(ccl::call nil t ccl::fixnum")
 change('skip-defaults',"(every #'walk a)","(every #'walk (if (eq op 'ccl::lambda-list) (list (sixth a)) a))")
 change('skip-initializers',"(every #'walk a)","(every #'walk (if (member op '(ccl::let ccl::let*)) (list (third a)) a))")
 old='(delivery-mode (if small-result-scratch "(i32.load offset=20 (local.get $context))" "(local.get $dynamic_results)"))'
 require(source.count(old)==1,'DELIVERY_SITE')
 result['delivery-follows-local']=source.replace(old,'(delivery-mode "(local.get $dynamic_results)")')
 old='(if small-result-scratch "(local.set $dynamic_results (i32.const 0))" "(local.set $dynamic_results (i32.load offset=20 (local.get $context)))")'
 require(source.count(old)==1,'ENTRY_MODE_SITE')
 result['inherit-everywhere']=source.replace(old,'"(local.set $dynamic_results (i32.load offset=20 (local.get $context)))"')
 return result


def run(evidence,out):
 require(not out.exists(),'NO_OVERWRITE');out.mkdir();rows=[]
 for name,source in mutations((HERE/'wasm32-backend.lisp').read_text()).items():
  backend=out/(name+'.lisp');backend.write_text(source)
  from result_demand import SOURCES as demand_sources, CASES as demand_cases
  try:compile_probe(evidence,out/name,backend,demand_sources if name=='delivery-follows-local' else SOURCES,demand_cases if name=='delivery-follows-local' else cases(),[])
  except ValueError as error:
   require(name!='delivery-follows-local' and str(error).startswith('SMALL_SCRATCH_IR_JOIN '),'PROOF_CONTROL_ORACLE '+name+': '+str(error))
   rows.append(dict(name=name,status='REJECTED',oracle=str(error)))
   continue
  require(name=='delivery-follows-local','PROOF_CONTROL_ESCAPED '+name)
  code=execute(out/name,HERE/'conditions.mjs',out/(name+'.json'))
  log=(out/(name+'.log')).read_text()
  require(code!=0 and 'AssertionError' in log and 'd_scalar' in log,'DELIVERY_CONTROL_ORACLE')
  rows.append(dict(name=name,status='REJECTED',oracle='native/logical result at d_scalar'))
 save(out/'controls.json',rows);return rows

if __name__=='__main__':
 import sys
 print(run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
