"""Disposable Wasm call trace; never used as acceptance evidence."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import sys,json,subprocess,re,shutil
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'bootstrap-validation'))
import common as c
out=Path(sys.argv[1]);allmods=json.loads((out/'compiled/modules.json').read_text())
names={s['id']:s['name'] for s in json.loads((out/'compiled/symbols.json').read_text())}
mods=[m for m in allmods if m['name'].startswith('namespace_')]
if '--all' in sys.argv:mods=allmods
work=out/'trace';work.mkdir(exist_ok=True)
def one(m):
 p=out/'compiled'/(m['name']+'.wat');text=p.read_text()
 index=allmods.index(m)
 if '(global $tcr i32)' not in text:return
 if '(func $body' in text:
  # Each generated function records its code identity at entry.
  start=text.index('(func $body');at=text.index('(local.set $incoming',start)
  index=allmods.index(m)
  record=f'(i32.store (i32.add (i32.const 6000016) (i32.and (i32.load (i32.const 6000000)) (i32.const 4092))) (i32.const {index}))(i32.store (i32.const 6000000) (i32.add (i32.load (i32.const 6000000)) (i32.const 4)))'
  if names.get(m['function'])=='CLASS-OF':
   record+='(i32.store (i32.const 6005096) (i32.load (i32.load offset=64 (global.get $tcr))))'
  if names.get(m['function'])=='FIND-CLASS':
   record+='(i32.store (i32.const 6005080) (i32.load (i32.load offset=64 (global.get $tcr))))'
  if names.get(m['function'])=='PREPARE-TO-DESTRUCTURE':
   record+='(memory.copy (i32.const 6009456) (i32.load offset=64 (global.get $tcr)) (i32.const 16))'
  if names.get(m['function']) in ('%WASM-ERROR','%WASM-IMPLICIT-CONDITION','%DEFUN'):
   address={'%WASM-ERROR':6005000,'%DEFUN':6005024,'%WASM-IMPLICIT-CONDITION':6005048}[names[m['function']]]
   record+=''.join(f'(i32.store (i32.const {address+i*4}) (i32.load offset={i*4} (i32.load offset=64 (global.get $tcr))))' for i in range(4))
  text=text[:at]+record+text[at:]
 if '(func $implicit_error_details' in text:
  at=text.index('(if',text.index('(func $implicit_error_details'))
  record='(i32.store (i32.const 6009472) (local.get $kind))(i32.store (i32.const 6009476) (local.get $datum))(i32.store (i32.const 6009480) (local.get $expected))(i32.store (i32.const 6009484) (i32.const '+str(index)+'))'
  text=text[:at]+record+text[at:]
 needle='(local.set $code)\n            (if (i32.ne (local.get $code) (i32.const 4))'
 text=text.replace(needle,'(local.set $code)(i32.store (i32.const 6000004) (local.get $node))(i32.store (i32.const 6005104) (i32.load (i32.const 6000000)))(i32.store (i32.const 6005108) (i32.load (i32.const 6005096)))\n            (if (i32.ne (local.get $code) (i32.const 4))')
 text=text.replace('(if (i32.eq (local.get $value) (i32.const 51)) (then', '(if (i32.eq (local.get $value) (i32.const 51)) (then (i32.store (i32.const 6005100) (local.get $symbol))')
 snapshot=f'(if (i32.eqz (i32.load (i32.const 6009300))) (then (i32.store (i32.const 6009300) (i32.load (i32.const 6000000)))(i32.store (i32.const 6009312) (i32.const {index}))(memory.copy (i32.const 6005200) (i32.const 6000016) (i32.const 4096))(memory.copy (i32.const 6009400) (i32.load offset=64 (global.get $tcr)) (i32.const 32))))'
 text=re.sub(r'\(throw (\$(?:call_error|error|err)) (\([^()]+\))\)',lambda m:snapshot+m[0],text)
 q=work/p.name;q.write_text(text)
 c.assemble(q,c.DEFAULT_CACHE)
 shutil.copyfile(q.with_suffix('.wasm'),p.with_suffix('.wasm'))
with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(one,mods))
for number,(name,source) in enumerate((('hash-adapter',c.ROOT/'tests/wasm/stage1/hash-tables/adapter.wat'),('file-adapter',c.ROOT/'tests/wasm/stage1/namespace-primitives/adapter.wat')),100000):
 text=source.read_text()
 snapshot=f'(if (i32.eqz (i32.load (i32.const 6009300))) (then (i32.store (i32.const 6009300) (i32.load (i32.const 6000000)))(i32.store (i32.const 6009312) (i32.const {number}))(memory.copy (i32.const 6005200) (i32.const 6000016) (i32.const 4096))(memory.copy (i32.const 6009400) (i32.load offset=64 (global.get $tcr)) (i32.const 32))))'
 text=re.sub(r'\(throw \$error (\([^()]+\))\)',lambda m:snapshot+m[0],text)
 p=work/(name+'.wat');p.write_text(text);c.assemble(p,c.DEFAULT_CACHE);shutil.copyfile(p.with_suffix('.wasm'),out/(name+'.wasm'))
print('TRACED',len(mods))
