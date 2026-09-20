"""Test-only WAT pressure hook; production loader must refuse the extra import."""
import json,shutil
from derive import replace

def run(out,driver):
 dst=out/'pressure';dst.mkdir();compiled=dst/'compiled';compiled.mkdir()
 for n in ['modules.json','materialized.json','native-condition-classes.json']:
  shutil.copy(out/'compiled'/n,compiled/n)
 shutil.copy(out/'native.json',dst/'native.json')
 for m in json.loads((compiled/'modules.json').read_text()):
  s=(out/'compiled'/(m['name']+'.wat')).read_text()
  anchor='(import "owner" "ensure" (func $owner_ensure (param i32)))'
  s=replace(s,anchor,anchor+'(import "pressure" "fill" (func $constructor_pressure (param i32)))')
  for name,kind in [('dynamic_slot',1),('restart_make',2),('condition_new',3)]:
   if '(func $'+name+' ' not in s:continue
   a=s.index('(func $'+name+' ');b=s.index('(func $',a+6);unit=s[a:b]
   marker='(if (i64.gt_u (i64.add (i64.extend_i32_u (i32.load offset=48'
   at=unit.index(marker);unit=unit[:at]+f'(call $constructor_pressure (i32.const {kind})) '+unit[at:]
   s=s[:a]+unit+s[b:]
  wat=compiled/(m['name']+'.wat');wat.write_text(s)
  driver.command(['/usr/local/bin/wat2wasm','--enable-threads','--enable-tail-call','--enable-exceptions',wat,'-o',wat.with_suffix('.wasm')],compiled/(m['name']+'.log'))
 driver.prepare(dst);return dst
