import json,subprocess
from pathlib import Path
from backend import generate
HERE=Path(__file__).resolve().parent

def run(out):
 out.mkdir();source=generate();a=source.index('(defun b-dynamic-runtime ()');b=source.index('(defun b-progv',a);part=source[a:b];runtime=part[part.index('"')+1:part.rindex('"')];assert '\\' not in runtime
 prefix='(module (import "env" "memory" (memory 17 32769 shared)) (import "env" "tcr" (global $tcr i32)) (import "env" "call_error" (tag $call_error (param i32)))\n'
 controls=[]
 for name,text in [('positive',runtime),('growing-unbind',runtime.replace('(call $existing_dynamic_slot (i32.load offset=16 (local.get $p)))','(call $dynamic_slot (i32.load offset=16 (local.get $p)))'))]:
  wat=out/(name+'.wat');wat.write_text(prefix+text+'\n(export "unbind" (func $unbind_to)))');wasm=out/(name+'.wasm')
  subprocess.run(['/usr/local/bin/wat2wasm','--enable-all',str(wat),'-o',str(wasm)],check=True)
  with (out/(name+'.log')).open('w') as f:r=subprocess.run(['/usr/local/bin/node',str(HERE/'unbind.mjs'),str(wasm),str(out/(name+'.json'))],stdout=f,stderr=subprocess.STDOUT,timeout=60)
  if name=='positive':assert r.returncode==0,(out/(name+'.log')).read_text()
  else:
   assert r.returncode!=0 and 'missing: non-growing unbind status' in (out/(name+'.log')).read_text();controls.append(dict(name=name,status='REJECTED'))
 (out/'controls.json').write_text(json.dumps(controls,indent=2)+'\n')
