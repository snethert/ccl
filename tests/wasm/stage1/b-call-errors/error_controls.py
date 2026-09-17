"""One-site errors must fail the native-first call-error oracle."""
from pathlib import Path
from support import HERE,read,save,require
from call_errors import run as run_cases
from replay import first_failure

def mutations(source):
 out={}
 def edit(name,fn,old,new):
  a=source.index('(defun '+fn+' ');b=source.find('\n(defun ',a+1);b=len(source) if b<0 else b
  part=source[a:b];require(part.count(old)==1,'ERROR_MUTANT_SITE '+name)
  out[name]=source[:a]+part.replace(old,new)+source[b:]
 edit('keyword-binding-published-before-validation','b-one-module',"prepare key-scan (if dynamic-parameters (b-special-extent #'emit-body) (emit-body))","prepare (if dynamic-parameters (b-special-extent (lambda () (concatenate 'string (b-bind-value (first *required-vars*) \"(i32.load (local.get $incoming))\") key-scan (emit-body)))) (concatenate 'string key-scan (emit-body)))")
 edit('arity-bypasses-lisp','b-condition',"(member kind '(1 4 16))","(member kind '(4 16))")
 edit('wrong-arity-class','b-implicit-runtime','(i32.const 2076)','(i32.const 156)')
 edit('keyword-class-not-simple','b-implicit-runtime','(i32.const 2108)','(i32.const 2076)')
 edit('wrong-designator-class','b-implicit-runtime','(i32.const 156)','(i32.const 2076)')
 edit('wrong-undefined-class','b-implicit-runtime','(i32.const 4124)','(i32.const 156)')
 edit('implicit-bounded-transfer','b-implicit-runtime','(local.set $dynamic_results (i32.const 1))','(local.set $dynamic_results (i32.const 0))')
 edit('condition-reuses-object','b-implicit-runtime','(i32.add (local.get $heap) (i32.const 16))','(local.get $heap)')
 edit('signal-skipped','b-implicit-runtime','(write-string signal s)','(write-string "" s)')
 edit('resolve-bypasses-lisp','b-implicit-runtime','(call $implicit_error (call $designator_error_kind (local.get $node)) (local.get $top))','(throw $call_error (i32.const 4))')
 return out

def one(task):
 name,source,evidence,directory=task;out=Path(directory);backend=out/(name+'.lisp');backend.write_text(source)
 try:run_cases(Path(evidence),out/name,backend)
 except ValueError:
  log=out/name/'execution.log';require(log.exists(),'COMPILER_MUST_EXECUTE '+name)
  text=log.read_text();require('AssertionError' in text,'SEMANTIC_ERROR_CONTROL '+name)
  return dict(name=name,status='REJECTED',first_failure=first_failure(text))
 raise AssertionError('ERROR_MUTANT_ESCAPED '+name)

def run(evidence,out):
 out.mkdir();from concurrent.futures import ProcessPoolExecutor
 with ProcessPoolExecutor(max_workers=3) as pool:rows=list(pool.map(one,[(n,s,str(evidence),str(out)) for n,s in mutations((HERE/'wasm32-backend.lisp').read_text()).items()]))
 save(out/'controls.json',rows);return rows

if __name__=='__main__':
 import sys
 print(run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
