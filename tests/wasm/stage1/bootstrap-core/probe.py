"""A test-only safepoint hook at the entry of the generated NIL leaf."""
import subprocess
from pathlib import Path
def build(directory):
 p=Path(directory)/'collector_probe.wat';s=p.read_text();start=s.index('(func $body ');i=start+len('(func $body')
 while True:
  while s[i].isspace():i+=1
  if not any(s.startswith('('+tag+' ',i) for tag in ('export','type','param','result','local')):break
  depth=1;i+=1
  while depth:
   if s[i]=='(':depth+=1
   elif s[i]==')':depth-=1
   i+=1
 s=s[:i]+'(call $probe_collect) '+s[i:]
 i=s.index('(module')+len('(module')
 s=s[:i]+'(import "probe" "collect" (func $probe_collect)) '+s[i:]
 p=p.with_name('collector_probe_hook.wat');p.write_text(s)
 subprocess.run(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',p,'-o',p.with_suffix('.wasm')],check=True)
