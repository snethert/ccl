"""Real Wasm faults and an escaped-on-R1 witness, not report-only controls."""
from pathlib import Path
import shutil,subprocess

def copy_execution(src,d):
 d.mkdir(parents=True)
 for f in src.iterdir():
  if f.is_file() and (f.suffix in ['.mjs','.wasm'] or f.name in ['assets.json','cases.json','expected.json','selection.json','tcr.json']):shutil.copy(f,d/f.name)
 (d/'compiled').mkdir()
 for f in (src/'compiled').iterdir():
  if f.is_file() and f.suffix in ['.json','.wasm']:shutil.copy(f,d/'compiled'/f.name)

def poison_return(text,offset):
 token='(return (local.get $value) (local.get $count))';i=text.rfind(token);assert i>=0
 store=f'(i32.store offset={offset} (global.get $tcr) (i32.add (i32.load offset={offset} (global.get $tcr)) (i32.const 16)))'
 return text[:i]+store+text[i:]

def execute(d,mode,command,save,expected):
 cmd=['/usr/local/bin/node',d/('node.mjs' if mode=='config' else 'check.mjs'),d,d/'execution.json'];save(d/'command.json',list(map(str,cmd)))
 with (d/'run.log').open('w') as f:r=subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,timeout=120)
 if expected=='PASS':assert r.returncode==0,(d,(d/'run.log').read_text())
 else:
  assert r.returncode!=0,str(d)+' escaped'
  assert expected in (d/'run.log').read_text(),(d,(d/'run.log').read_text()[-2000:])

def run(e,out,command,read,save):
 rows=[]
 # Reproduce both review counterexamples in both original harnesses.
 for mode,packet,module in [('config','2026-09-20-stage1-startup-config-r1','config_5566'),('resets','2026-09-20-stage1-startup-resets-r1','reset_5568')]:
  for offset in [76,88]:
   src=e/packet/'execution';d=out/'regressions'/f'{mode}-r1-escaped-{offset}';copy_execution(src,d)
   p=d/'compiled'/(module+'.wat');p.write_text(poison_return((src/'compiled'/(module+'.wat')).read_text(),offset))
   command(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',p,'-o',p.with_suffix('.wasm')],d/'assemble.log')
   execute(d,mode,command,save,'PASS')
   rows.append(dict(name=f'{mode}-r1-{offset}',status='ESCAPED_RETAINED',exit=0))
 # Corrected checks reject both displaced pointers, the old base-field check,
 # FP policy changes, persistent scratch, reserved words and bad result count.
 for mode,module in [('config','config_5566'),('resets','reset_5568')]:
  for offset in [76,88,92,184,200,248,116]:
   src=out/mode;d=out/'regressions'/f'{mode}-r2-rejected-{offset}';copy_execution(src,d)
   p=d/'compiled'/(module+'.wat');p.write_text(poison_return((src/'compiled'/(module+'.wat')).read_text(),offset))
   command(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',p,'-o',p.with_suffix('.wasm')],d/'assemble.log')
   why='TCR result count' if offset==116 else 'TCR preservation'
   execute(d,mode,command,save,why);rows.append(dict(name=f'{mode}-r2-{offset}',status='REJECTED',diagnostic=why))
 # Remove the actual emitted cache store while retaining the value used by EQ.
 src=out/'config';d=out/'regressions'/'cpu-cache-store-omitted';copy_execution(src,d)
 s=(src/'compiled/config_5566.wat').read_text();old='(i32.store (call $special_location (i32.load offset=8 (local.get $tmp5))) (i32.load offset=12 (local.get $tmp5)))'
 assert s.count(old)==1;s=s.replace(old,'(nop)');p=d/'compiled/config_5566.wat';p.write_text(s)
 command(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',p,'-o',p.with_suffix('.wasm')],d/'assemble.log')
 execute(d,'config',command,save,'POSTCONDITION');rows.append(dict(name='cpu-cache-store-omitted',status='REJECTED',diagnostic='POSTCONDITION'))
 # Force a cache miss even when the caller supplied a prefilled CPU count.
 d=out/'regressions'/'cpu-cache-ignored';copy_execution(src,d)
 s=(src/'compiled/config_5566.wat').read_text();old='(i32.ne (i32.load (i32.add (local.get $bindings) (i32.const 0))) (i32.const 77825))'
 assert s.count(old)==1;s=s.replace(old,'(i32.const 0)');p=d/'compiled/config_5566.wat';p.write_text(s)
 command(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',p,'-o',p.with_suffix('.wasm')],d/'assemble.log')
 execute(d,'config',command,save,'POSTCONDITION');rows.append(dict(name='cpu-cache-ignored',status='REJECTED',diagnostic='POSTCONDITION'))
 save(out/'regressions.json',rows)
