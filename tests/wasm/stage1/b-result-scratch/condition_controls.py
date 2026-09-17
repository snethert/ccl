"""Compile single-site dispatcher omissions, then reuse the literal/native oracle."""
from pathlib import Path
import subprocess
from support import HERE,read,save,require
from conditions import compile_conditions

def mutations(source):
 result={}
 def change(name,fn,old,new):
  a=source.index('(defun '+fn+' ');b=source.find('\n(defun ',a+1);b=len(source) if b<0 else b
  part=source[a:b];require(part.count(old)==1,'MUTATION_SITE '+name)
  result[name]=source[:a]+part.replace(old,new)+source[b:]
 change('type-union','b-signal','(if (i32.and (call $condition_mask','(if (i32.or (call $condition_mask')
 change('cluster-visible','b-signal','(i32.store (call $special_location ~a) (i32.load (call $handler_cons (call $special_read ~a))))','(drop (call $special_location ~a)) (drop (i32.load (call $handler_cons (call $special_read ~a))))')
 change('decline-stops-search','b-signal','(write-string (b-discard-handler handler raw-condition) s)','(write-string (b-discard-handler handler raw-condition) s) (write-string "(br $signal_done)" s)')
 change('wrong-condition','b-signal','(raw-condition (make-b-raw-code :text condition))','(raw-condition (make-b-raw-code :text "(i32.const 77825)"))')
 change('error-returns','b-signal','(if fatal "(throw $call_error (i32.const 15))"','(if nil "(throw $call_error (i32.const 15))"')
 change('indexed-condition-pair','b-signal','(b-cons (make-b-raw-code :text handler) raw-condition)','(b-cons raw-condition (make-b-raw-code :text handler))')
 change('handler-values-bounded','b-discard-handler','(local.set $dynamic_results (i32.const 1))','(local.set $dynamic_results (i32.const 0))')
 change('skip-first-handler','b-signal','root cluster handlers)','root (b-wat "(call $handler_rest ~a)" cluster) handlers)')
 change('condition-mask-unchecked','b-condition-runtime','(local.get $mask))")','(i32.const 1))")')
 change('handler-scope-leak','b-discard-handler','(call $rv_release (local.get ~a))','(drop (local.get ~a))')
 return result

def run_one(task):
 name,source,evidence,out=task;out=Path(out);backend=out/(name+'.lisp');backend.write_text(source)
 compile_conditions(Path(evidence),out/name,backend)
 cmd=['/usr/local/bin/node',str(HERE/'conditions.mjs'),str(out/name),str(out/(name+'.json'))]
 save(out/(name+'-command.json'),cmd)
 with (out/(name+'.log')).open('w') as log:
  try:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=10)
  except subprocess.TimeoutExpired:
   require(name=='cluster-visible','UNEXPECTED_TIMEOUT '+name)
   progress=read(out/(name+'.json.progress.json'));require(progress['progress'].startswith('h_discard_many-'),'MASKING_PROGRESS_CASE')
   return dict(name=name,status='REJECTED',first_failure='cluster search makes no forward progress',deadline_seconds=10,progress=progress)

 text=(out/(name+'.log')).read_text();require(r.returncode!=0 and 'AssertionError' in text,'CONDITION_MUTANT_ESCAPED '+name)
 from replay import first_failure
 return dict(name=name,status='REJECTED',first_failure=first_failure(text))

def run(evidence,out):
 out.mkdir();from concurrent.futures import ProcessPoolExecutor
 tasks=[(n,s,str(evidence),str(out)) for n,s in mutations((HERE/'wasm32-backend.lisp').read_text()).items()]
 with ProcessPoolExecutor(max_workers=3) as pool:rows=list(pool.map(run_one,tasks))
 save(out/'controls.json',rows);return rows

if __name__=='__main__':
 import sys
 print(run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
