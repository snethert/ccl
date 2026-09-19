"""Recompile omitted scanners/reloads; require their independent first failure."""
import json,subprocess,sys
from pathlib import Path
from backend import generate,replace,EQ_NEW,EQ_OLD,BIND_NEW,BIND_OLD,CONDITION_FIXES

def run(e,out,h,command,clang,flags):
 out.mkdir();rows=[]
 variants=[('unrooted-eq',[(EQ_NEW,EQ_OLD)],'eq_left: native/logical result'),
           ('early-cell-address',[(BIND_NEW,BIND_OLD)],'captured_let: native/logical result'),
           ('cached-condition',[(CONDITION_FIXES[2][1],CONDITION_FIXES[2][0])],'d_condition_decline: native/logical result'),
           ('omitted-condition-root',[(CONDITION_FIXES[0][1],CONDITION_FIXES[0][0])],'d_condition_decline: native/logical result')]
 for name,edits,oracle in variants:
  source=generate()
  for a,b in edits:source=replace(source,a,b)
  compiler=out/(name+'.lisp');compiler.write_text(source)
  try:command([sys.executable,h/'live_probe.py',e,out/name,compiler],out/(name+'.log'))
  except subprocess.CalledProcessError:
   log=out/name/'execution.log';assert log.exists() and oracle in log.read_text(),name
  else:raise AssertionError(name+' escaped')
  rows.append(dict(name=name,status='REJECTED',oracle=oracle))
 source=(h/'collector.c').read_text()
 for name,a,b,oracle in [
  ('missing-restart','node_subtag(tag)||(tag==130&&n==6)','node_subtag(tag)','restart-field-0-'),
  ('missing-test-slot','scan=n;size=4+(W)n*4;','scan=tag==130?n-1:n;size=4+(W)n*4;','restart field 5 moved'),
  ('padding-as-root','scan=n;size=4+(W)n*4;','scan=tag==130?n+1:n;size=4+(W)n*4;','restart-field-0-'),
  ('unbounded-istruct','tag==130&&n==6','tag==130','unadmitted istruct count 5'),
  ('t-as-stack-callable','old!=77838u && (old&7)==6','(old&7)==6','canonical-t-root-'),
 ]:
  c=out/(name+'.c');c.write_text(replace(source,a,b));wasm=out/(name+'.wasm');command([clang,*flags,c,'-o',wasm],out/(name+'-compile.log'))
  try:command(['/usr/local/bin/node',h/'core-check.mjs',wasm,out/(name+'.json')],out/(name+'.log'))
  except subprocess.CalledProcessError:
   log=(out/(name+'.log')).read_text();assert 'AssertionError' in log and oracle in log,(name,log)
  else:raise AssertionError(name+' escaped')
  rows.append(dict(name=name,status='REJECTED',oracle=oracle))
 (out/'controls.json').write_text(json.dumps(rows,indent=2)+'\n');return rows
