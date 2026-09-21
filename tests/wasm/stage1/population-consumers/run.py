import argparse,hashlib,importlib.util,json,os,shutil,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];E=ROOT.parent/'ccl-evidence';NODE=Path('/usr/local/bin/node')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log,**kw):
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600,**kw)
def run(out):
 out.mkdir(parents=True,exist_ok=False)
 prior=E/'2026-09-21-stage1-startup-review-138-r1'
 for row in read(prior/'packet.json')['files']:assert sha(prior/row['path'])==row['sha256']
 for n,h in read(prior/'source-pins.json').items():assert sha(ROOT/n)==h,n
 save(out/'parent-binding.json',{n:sha(prior/n) for n in ['packet.json','verification.json','source-pins.json']})
 dependencies=read(prior/'dependencies.json')
 for n,h in dependencies.items():
  root,path=n.split('/',1);p=(ROOT/path if root=='ROOT' else E/path if root=='EVIDENCE' else Path(path));assert sha(p)==h,n
 save(out/'dependencies.json',dependencies)
 # Pin the reused adapter/collector bytes, not only their generating sources.
 oldpacket=E/'2026-09-20-stage1-population-access-r1'
 oldfiles={r['path']:r['sha256'] for r in read(oldpacket/'packet.json')['files']}
 for n in ['adapter.wasm','collector.wasm']:assert sha(oldpacket/'execution'/n)==oldfiles['execution/'+n]
 save(out/'reused-services.json',{n:sha(oldpacket/'execution'/n) for n in ['adapter.wasm','collector.wasm']})
 kernel=E/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=E/'2026-09-16-stage1-1a-r2/native/baseline.image'
 with tempfile.TemporaryDirectory(prefix='ccl-population-consumers-') as d:
  w=Path(d);shutil.copy(kernel,w/'dx86cl64');(w/'dx86cl64').chmod(0o755);shutil.copy(image,w/'dx86cl64.image')
  command([w/'dx86cl64','--no-init','--batch','--load',HERE/'native.lisp'],out/'native.log',env={**os.environ,'POP_CONSUMERS':str(HERE/'consumers.lisp'),'POP_NATIVE':str(out/'native.json')})
 spec=importlib.util.spec_from_file_location('consumer_compile',ROOT/'tests/wasm/stage1/startup-joined/compile.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
 source=(HERE/'compile.lisp').read_text()
 for n in ['consumers.lisp','lower.lisp']:source=source.replace('(merge-pathnames "'+n+'" *load-pathname*)',json.dumps(str(HERE/n)))
 compiled=c.compile_source(E,out/'build',source,None)
 assert sha(compiled/'proposal/files/compiler/WASM32/wasm32-backend.lisp')==sha(ROOT/'compiler/WASM32/wasm32-backend.lisp')
 native_reuse=E/'2026-09-20-stage1-startup-config-r2/native-reuse.json'
 assert sha(ROOT/'compiler/WASM32/wasm32-backend.lisp')==read(native_reuse)['compiler_sha256']
 save(out/'compiler-binding.json',dict(compiler_sha256=sha(ROOT/'compiler/WASM32/wasm32-backend.lisp'),native_R6='REUSED_BY_EXACT_COMPILER_HASH',reuse_record_sha256=sha(native_reuse),source_revision='c994217adc56b3f8a564526cee4695893ac84d86'))
 dest=out/'compiled';dest.mkdir()
 for p in compiled.iterdir():
  if p.is_file() and p.suffix in ['.json','.wasm','.wat','.lisp','.dx64fsl'] and p.name!='command.json':shutil.copy(p,dest/p.name)
 for n in ['check.mjs','install.mjs']:shutil.copy(HERE/n,out/n)
 old=E/'2026-09-20-stage1-population-access-r1/execution'
 for n in ['adapter.wasm','collector.wasm']:shutil.copy(old/n,out/n)
 shutil.copy(prior/'execution/services/population.wasm',out/'population.wasm')
 shutil.copy(ROOT/'runtime/wasm32/bootstrap-populations.mjs',out/'builder.mjs')
 command([NODE,out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 save(out/'inputs.json',{str(kernel):sha(kernel),str(image):sha(image),str(NODE):sha(NODE),'ROOT/compiler/WASM32/wasm32-backend.lisp':sha(ROOT/'compiler/WASM32/wasm32-backend.lisp')})
 # Recompile changed consumer bodies; require execution to reject each against
 # the unchanged native oracle. The compiler itself is identical in all runs.
 faults=[]
 variants=[
  ('keyword-type',"0) :list :alist)","0) :alist :list)",'pc_type'),
  ('setter-result','(pop_raw_set population value nil)))','(progn (pop_raw_set population value nil) nil)))','pc_set'),
  ('reader-operation','(pop_raw_get population nil nil)','(pop_raw_type population nil nil)','pc_type post-move contents'),
  ('push-order','(walk (macroexpand-1 x))',"(let ((expanded (macroexpand-1 x))) (when (eq (car x) 'push) (rotatef (first (second expanded)) (second (second expanded)))) (walk expanded))",'pc_effects')]
 for name,a,b,why in variants:
  d=out/'faults'/name;d.mkdir(parents=True);text=(HERE/'lower.lisp').read_text();assert text.count(a)==1,a;(d/'lower.lisp').write_text(text.replace(a,b))
  faultsource=source.replace(json.dumps(str(HERE/'lower.lisp')),json.dumps(str(d/'lower.lisp')))
  compiledfault=c.compile_source(E,d/'build',faultsource,None);(d/'compiled').mkdir()
  for f in compiledfault.iterdir():
   if f.is_file() and f.suffix in ['.wasm','.json'] and f.name!='command.json':shutil.copy(f,d/'compiled'/f.name)
  for n in ['check.mjs','install.mjs','builder.mjs','adapter.wasm','collector.wasm','population.wasm','native.json']:shutil.copy(out/n,d/n)
  try:command([NODE,d/'check.mjs',d,d/'execution.json'],d/'rejected.log')
  except subprocess.CalledProcessError:assert why in (d/'rejected.log').read_text(),(name,(d/'rejected.log').read_text()[-2000:])
  else:raise AssertionError(name+' escaped')
  faults.append(dict(name=name,diagnostic=why,status='REJECTED'))
 save(out/'controls.json',faults)
 save(out/'summary.json',dict(status='PASS',modules=len(read(dest/'modules.json')),native_cases=len(read(out/'native.json')),comparisons=sum(r['comparisons'] for r in read(out/'execution.json')['rows']),collections=sum(sum(1+int(x['internalCollection']) for x in r['rows']) for r in read(out/'execution.json')['rows']),faults=len(faults),compiler_unchanged=True,slot_credit=False))
 print(read(out/'summary.json'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);run(p.parse_args().output.resolve())
