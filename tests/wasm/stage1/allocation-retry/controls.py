"""Recompile semantic mutations and require the named execution failure."""
import json,os,subprocess
from pathlib import Path
from backend import generate,replace,prior
HERE=Path(__file__).resolve().parent

def variants():
 s=generate()
 yield 'omit-fixed-retry',replace(s,'(then (call $heap_ensure (i32.const ~d)))) ', '(then (drop (i32.const ~d)))) '),'pair','pair: checked 6'
 yield 'omit-rest-retry',replace(s,'(call $heap_ensure (i32.mul (local.get ~a) (i32.const 8)))','(drop (i32.mul (local.get ~a) (i32.const 8)))'),'gather','gather: checked 6'
 yield 'old-allocation-pointer',replace(s,'(then (call $owner_ensure (local.get $bytes)))','(then (call $owner_ensure (local.get $bytes)) (i32.store offset=48 (global.get $tcr) (local.get $p)))'),'pair','pair: checked 6'
 yield 'unrooted-eq',replace(s,prior.EQ_NEW,prior.EQ_OLD),'eq_operands','eq_operands: native graph'
 yield 'early-cell-address',replace(s,prior.BIND_NEW,prior.BIND_OLD),'early_cell','early_cell: native graph'
 old='(b-wat "(i32.load offset=~d (i32.sub (i32.load offset=2 (i32.load offset=40 (local.get $context))) (i32.const 6)))" (+ 4 (* 4 n)))'
 new='(b-wat "(i32.load offset=~d (local.get $closure_env))" (+ 4 (* 4 n)))'
 yield 'cached-environment',replace(s,old,new),'closure_inside','RuntimeError: memory access out of bounds'

def run(e,out,h,execute):
 out.mkdir();rows=[]
 for name,source,focus,diagnostic in variants():
  d=out/name;d.mkdir();backend=d/'wasm32-backend.lisp';backend.write_text(source)
  cmd=[os.sys.executable,str(h/'retry_probe.py'),str(e),str(d/'compiled'),str(backend)]
  with (d/'compile.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
  cmd=['/usr/local/bin/node',str(execute),str(d/'compiled'),str(h/'collector.wasm'),str(d/'unexpected.json')]
  with (d/'execution.log').open('w') as log:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,RETRY_CASE=focus),timeout=90)
  text=(d/'execution.log').read_text();assert p.returncode!=0 and diagnostic in text,(name,p.returncode,text[-2000:])
  rows.append(dict(name=name,status='REJECTED',case=focus,diagnostic=diagnostic))
 result=dict(status='PASS',mutants=rows);(out/'controls.json').write_text(json.dumps(result,indent=2)+'\n');return result
