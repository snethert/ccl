"""Recompile constructor faults; pressure and the native oracle reject each."""
import json,os,subprocess
from pathlib import Path
from backend import generate,replace,ensure
from instrument import run as pressure

def scoped(s,name,old,new):
 a=s.index('(defun '+name+' ');b=s.index('\n(defun ',a+1);u=s[a:b];return s[:a]+replace(u,old,new)+s[b:]
def variants():
 s=generate()
 for name,expression,focus,diagnostic in [
  ('vector','(i32.and (i32.add (i32.mul (local.get $newcap) (i32.const 4)) (i32.const 11)) (i32.const -8))','grow_value','grow_value: checked 3'),
  ('restart','(i32.const 32)','restart_closure','restart_closure: checked 6'),
  ('condition','(local.get $bytes)','condition_heap','condition_heap: checked 6')]:
  # Preserve preflight shape for the external pressure hook.
  yield 'omit-'+name+'-retry',replace(s,'(then (call $heap_ensure '+expression+')))', '(then (drop '+expression+')))'),focus,diagnostic
 yield 'cached-new-binding-value',replace(s,'(local.set ~a (i32.load offset=20 (local.get ~a))) (i32.store (local.get ~a) ~a)', '(drop (local.get ~a)) (drop (local.get ~a)) (i32.store (local.get ~a) ~a)'),'grow_value','Error: unhandled result 3722304989'
 old='(format out "(local.set ~a (i32.load offset=12 ~a))" vals base)'
 yield 'cached-progv-values',replace(s,old,'(format out "(drop (local.get ~a)) (drop ~a)" vals base)'),'grow_progv','grow_progv: type refusal -572662307 1'
 for name,local,load,focus,diagnostic in [
  ('restart','action','(i32.load offset=4 (local.get $arguments))','restart_closure','restart_closure: checked 6'),
  ('condition','datum','(i32.load (local.get $arguments))','condition_heap','condition_heap: native graph')]:
  start='b-'+name+'-runtime';assignment='(local.set $'+local+' '+load+')'
  a=s.index('(defun '+start+' ');b=s.index('\n(defun ',a+1);u=s[a:b];assert u.count(assignment)==1
  u=u.replace(assignment,'');anchor=ensure('(i32.const 32)' if name=='restart' else '(local.get $bytes)');assert u.count(anchor)==1
  u=u.replace(anchor,assignment+'\n '+anchor)
  yield 'cached-'+name+'-'+local,s[:a]+u+s[b:],focus,diagnostic
 reload='(local.set $base (i32.load offset=104 (global.get $tcr))) (local.set $cap (i32.load offset=108 (global.get $tcr)))'
 anchor=ensure('(i32.and (i32.add (i32.mul (local.get $newcap) (i32.const 4)) (i32.const 11)) (i32.const -8))')
 yield 'cached-old-binding-vector',replace(s,anchor+reload,anchor),'grow_twice','grow_twice: checked 12'

def run(e,out,h,execute):
 out.mkdir();rows=[]
 for name,source,focus,diagnostic in variants():
  d=out/name;d.mkdir();backend=d/'wasm32-backend.lisp';backend.write_text(source)
  with (d/'compile.log').open('w') as log:subprocess.run([os.sys.executable,str(h/'retry_probe.py'),str(e),str(d/'compiled'),str(backend)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
  pressure(d/'compiled',d/'pressure')
  with (d/'execution.log').open('w') as log:p=subprocess.run(['/usr/local/bin/node',str(execute),str(d/'pressure'),str(h/'collector.wasm'),str(d/'unexpected.json')],stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,RETRY_CASE=focus,CONSTRUCTOR_PRESSURE='1'),timeout=90)
  text=(d/'execution.log').read_text();assert p.returncode!=0 and diagnostic in text,(name,p.returncode,text[-2000:])
  rows.append(dict(name=name,status='REJECTED',case=focus,diagnostic=diagnostic))
 result=dict(status='PASS',mutants=rows);(out/'controls.json').write_text(json.dumps(result,indent=2)+'\n');return result
