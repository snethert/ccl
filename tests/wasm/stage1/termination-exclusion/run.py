import argparse,hashlib,json,shutil,subprocess,sys,tempfile
from pathlib import Path
from derive import HERE,BASE,SCENARIOS,compile_source,check_source
ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log,why=None):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:r=subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,timeout=240)
 if why:assert r.returncode and why in log.read_text(),(log,why)
 else:assert r.returncode==0,log

def run(e,out):
 out.mkdir(parents=True)
 prior=e/'2026-09-20-stage1-startup-runtime-review-r1'
 native=read(e/'2026-09-20-stage1-startup-config-r2/native-reuse.json')
 assert native['compiler_sha256']==sha(ROOT/'compiler/WASM32/wasm32-backend.lisp')
 save(out/'native-reuse.json',native)
 for n in ['collector-owner.mjs','sha256.mjs','bytes.mjs']:shutil.copy(ROOT/'runtime/wasm32'/n,out/('owner.mjs' if n=='collector-owner.mjs' else n))
 # Reuse the integrated collector's reviewed binary by its packet binding.
 source=prior/'execution/execution/collector.wasm'
 bound=next(r for r in read(prior/'packet.json')['files'] if r['path']=='execution/execution/collector.wasm')
 assert sha(source)==bound['sha256'];shutil.copy(source,out/'collector.wasm')
 for n in ['admission.mjs','admission-check.mjs','bindings.json']:shutil.copy(HERE/n,out/n)
 conditions=(HERE.parent/'startup-runtime-review/conditions.mjs').read_text().replace('Collector timing is unavailable.','Finalization is not supported in Stage 1.')
 (out/'conditions.mjs').write_text(conditions);(out/'check.mjs').write_text(check_source())
 save(out/'scenarios.json',SCENARIOS);(out/'compile.lisp').write_text(compile_source())
 sys.path.insert(0,str(HERE.parent/'startup-joined'));from compile import compile_source as build
 c=build(e,out/'compile',compile_source(),None)
 shutil.copytree(c,out/'compiled',ignore=shutil.ignore_patterns('source','proposal','compile-input','compiler.dx64fsl'))
 node='/usr/local/bin/node'
 command([node,out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 command([node,out/'admission-check.mjs',out/'admission.json'],out/'admission.log')
 kernel=e/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=e/'2026-09-16-stage1-1a-r2/native/baseline.image'
 with tempfile.TemporaryDirectory(prefix='ccl-termination-native-') as tmp:
  d=Path(tmp);shutil.copy(kernel,d/'dx86cl64');(d/'dx86cl64').chmod(0o755);shutil.copy(image,d/'dx86cl64.image')
  command([d/'dx86cl64','--no-init','--batch','--load',HERE/'native.lisp'],out/'native.log')
 lines=(out/'native.log').read_text().splitlines()
 assert 'NATIVE-REGISTRATION|register,lookup,cancel|callbacks=0|restored' in lines
 state=next(l.split('|')[1:] for l in lines if l.startswith('TERMINATION-STATE|'))
 assert state==['0','0','0','T'],state
 kinds={l.split('|')[1]:int(l.split('|')[2]) for l in lines if l.startswith('EQL-KIND|')}
 count=int(next(l.split('|')[1] for l in lines if l.startswith('EQL-TOTAL|')))
 assert sum(kinds.values())==count
 save(out/'native-state.json',dict(registrations=0,pending=0,functions=0,automatic_enabled=True,probe_cancelled=True))
 save(out/'eql-key-survey.json',dict(entries=count,kinds=kinds,numeric_character_keys=[l[8:] for l in lines if l.startswith('EQL-KEY|')],scope='Observed pinned native specializer table; not an equality-service qualification.'))
 bindings=read(HERE/'bindings.json')['functions'];bound=[]
 for identity,module in bindings.items():
  name=identity.split(':')[-1];line=next(l for l in lines if l.startswith('BINDING|'+name+'|'))
  if '::' not in identity:assert line.endswith('|EXTERNAL'),line
  bound.append(dict(identity=identity,module=module,sha256=sha(out/'compiled'/(module+'.wasm'))))
 save(out/'bound-bindings.json',bound)
 controls=[]
 for name,a,b,why in [
  ('registered',"need(values[0]===77825,'registered objects');",'', 'registered'),
  ('pending',"need(values[1]===77825,'pending callbacks');",'', 'pending'),
  ('functions',"need(values[2]===0,'function registrations');",'', 'functions'),
  ('automatic',"need(values[3]===77825,'automatic scheduling');",'', 'automatic'),
  ('policy',"need(policy===POLICY,'policy');",'', 'policy'),
  ('alias','&&new Set(addresses).size===4','', 'aliased-slot'),
  ('slot-region','&&p>=region.start&&p+4<=region.end','', 'out-of-region'),
 ]:
  d=out/'faults'/name;d.mkdir(parents=True)
  s=(out/'admission.mjs').read_text();assert s.count(a)==1;(d/'admission.mjs').write_text(s.replace(a,b))
  shutil.copy(out/'admission-check.mjs',d/'admission-check.mjs')
  command([node,d/'admission-check.mjs',d/'result.json'],d/'rejected.log',why);controls.append(dict(name=name,status='REJECTED',diagnostic=why))
 # Changed replacement bodies go through CCL again: neither source text scans
 # nor a hand-written Wasm edit can substitute for these semantic controls.
 for name,a,b,why in [
  ('registration-succeeds','(error termination_unavailable)))','nil))','Lisp result'),
  ('automatic-silent', '(if automatic_termination_enabled (termination_drain) nil)', 'nil','Lisp result'),
  ('callback-executed','(error termination_unavailable)))','(progn (funcall callback object) (error termination_unavailable))))','callback must not run'),
 ]:
  d=out/'faults'/name;d.mkdir(parents=True)
  s=(HERE/'entries.lisp').read_text();assert a in s
  # Only change the first replacement body and leave its independent native
  # reference unmodified: compile mutant Wasm, compare to positive oracle.
  s=s.replace(a,b,1);m=build(e,d/'compile',compile_source(s),None)
  for n in ['owner.mjs','sha256.mjs','bytes.mjs','collector.wasm','conditions.mjs','check.mjs','scenarios.json']:shutil.copy(out/n,d/n)
  shutil.copytree(m,d/'compiled',ignore=shutil.ignore_patterns('source','proposal','compile-input','compiler.dx64fsl'))
  shutil.copy(out/'compiled/native.json',d/'compiled/native.json')
  command([node,d/'check.mjs',d,d/'execution.json'],d/'rejected.log',why);controls.append(dict(name=name,status='REJECTED',diagnostic=why))
 save(out/'controls.json',controls)
 save(out/'tools.json',{n:sha(Path(n)) for n in [node,'/usr/local/bin/wat2wasm']})
 summary=dict(status='PASS',modules=len(read(out/'compiled/modules.json')),comparisons=read(out/'execution.json')['comparisons'],collections=read(out/'execution.json')['collections'],admission_checks=read(out/'admission.json')['checks'],controls=len(controls),eql_survey=kinds,slot_credit=False)
 save(out/'summary.json',summary);print(summary)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
