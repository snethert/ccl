"""Test-only allocation pressure immediately before each raw constructor preflight.
The hook fills unused heap bytes with valid unreachable conses. It cannot move
objects; only the emitted owner's slow path can do that.
"""
import json,shutil,subprocess
from pathlib import Path

def run(src,out):
 out.mkdir()
 for n in ['modules.json','cases.json','native.json','native-condition-classes.json']:shutil.copy(src/n,out/n)
 (out/'installed').mkdir()
 for m in json.loads((src/'modules.json').read_text()):
  s=(src/(m['name']+'.wat')).read_text()
  anchor='(import "owner" "ensure" (func $owner_ensure (param i32)))';assert s.count(anchor)==1
  s=s.replace(anchor,anchor+'\n(import "pressure" "fill" (func $constructor_pressure (param i32)))')
  for name,kind in [('dynamic_slot',1),('restart_make',2),('condition_new',3)]:
   if '(func $'+name+' ' not in s:continue
   a=s.index('(func $'+name+' ');b=s.index('(func $',a+6)
   unit=s[a:b]
   # Pressure at the same site even when a mutant removes the retry call.
   if kind==1:at=unit.index('  (if (i64.gt_u (i64.add (i64.extend_i32_u (i32.load offset=48')
   elif kind==2:at=unit.index('\n (if (i64.gt_u (i64.add (i64.extend_i32_u (i32.load offset=48')
   else:at=unit.index('\n (if (i64.gt_u (i64.add (i64.extend_i32_u (i32.load offset=48')
   unit=unit[:at]+f'\n (call $constructor_pressure (i32.const {kind}))\n'+unit[at:];s=s[:a]+unit+s[b:]
  wat=out/(m['name']+'.wat');wat.write_text(s)
  with (out/(m['name']+'.log')).open('w') as log:subprocess.run(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',str(wat),'-o',str(out/'installed'/(m['name']+'.wasm'))],stdout=log,stderr=subprocess.STDOUT,check=True)
if __name__=='__main__':
 import sys
 run(*map(Path,sys.argv[1:3]))
