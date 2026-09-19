"""Every semantic fault is compiled through the real CCL front end."""
import json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent

def run(e,positive,out,driver):
 out.mkdir();source=(HERE/'runtime.lisp').read_text();compiler=(positive/'compiled/proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text();rows=[]
 faults=[
 ('retain-last-dcode','runtime',"""(let ((next (if methods candidate #'gd_missing)))
     (if (car (cdr (cdr state)))
       (gd_set_encapsulated state next)
       (rplaca (cdr state) next)))""","""(if methods
     (let ((next candidate))
       (if (car (cdr (cdr state))) (gd_set_encapsulated state next) (rplaca (cdr state) next)))
     nil)""",'empty dcode publication'),
 ('omit-empty-guard','runtime','(if (car state)\n     (apply','(if t\n     (apply','stale raw store'),
 ('wrong-encapsulated-cell','runtime','(rplaca (cdr (cdr (cdr state))) dcode)','(rplaca (cdr state) dcode)','specific'),
 ('discard-second-value','runtime','(values 10 11)','(values 10)','universal'),
 ('drop-envelope','runtime','(rplaca trace (cons 1 (car trace)))','(car trace)','encapsulation preserved'),
 ('lose-continue-retry','runtime','(continue () (apply gf args))','(continue () (values))','continue reinstalls method'),
 ('lose-condition-gf','compiler','(i32.store offset=8 (local.get $slots) (local.get $datum)) (i32.store offset=12 (local.get $slots) (local.get $expected))))','(i32.store offset=8 (local.get $slots) (i32.const 77825)) (i32.store offset=12 (local.get $slots) (local.get $expected))))','empty registry'),
 ('lose-condition-args','compiler','(i32.store offset=8 (local.get $slots) (local.get $datum)) (i32.store offset=12 (local.get $slots) (local.get $expected))))','(i32.store offset=8 (local.get $slots) (local.get $datum)) (i32.store offset=12 (local.get $slots) (i32.const 77825))))','empty registry'),
 ]
 a=source.index('  ("gd_table"');b=source.index('  ("gd_set_encapsulated"',a)
 faults.append(('universal-first','runtime',source[a:b],(HERE/'rejected-table.lisp').read_text(),'specificity after universal'))
 for name,kind,old,new,oracle in faults:
  text=source if kind=='runtime' else compiler;assert text.count(old)==(1 if kind=='runtime' else 2),(name,text.count(old));changed=text.replace(old,new);d=out/name
  try:driver(e,d,changed if kind=='compiler' else compiler,changed if kind=='runtime' else source)
  except subprocess.CalledProcessError:
   log=(d/'execution.log').read_text();assert 'AssertionError' in log and oracle in log,(name,log[:500])
  else:raise ValueError('escaped fault: '+name)
  rows.append(dict(name=name,status='REJECTED',oracle=oracle,kind=kind))
 (out/'controls.json').write_text(json.dumps(rows,indent=2,sort_keys=True)+'\n');return rows
