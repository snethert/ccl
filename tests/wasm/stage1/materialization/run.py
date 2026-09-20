import argparse,hashlib,importlib.util,json,re,shutil,subprocess,sys
from pathlib import Path
from backend import HERE,ROOT,generate,replace
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def read(p):return json.loads(p.read_text())
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
def compile(e,out,code,template):
 h=out.parent/(out.name+'-driver');shutil.copytree(HERE.parent/'constants',h,ignore=shutil.ignore_patterns('__pycache__','review-followup'))
 s=(HERE.parent/'callable-metadata/compile.lisp').read_text()
 s=replace(s,'(ccl:quit)','''(dolist (r (list (compile-module "(lambda (x) (if x 17 29))" "leaf")
                   (compile-primitive-module "(lambda (p) (%header-word p))" "primitive" '(:node) :u32)))
 (with-open-file (o (concatenate 'string (ccl:getenv "POOL_OUTPUT") (getf r :name) ".wat") :direction :output :if-exists :error)
  (write-string (getf r :wat) o)))''')
 if template:
  s=replace(s,'(load (merge-pathnames "export.lisp" *load-pathname*))','(load (merge-pathnames "export.lisp" *load-pathname*))\n(let ((*wasm32-template-memory* t))')+'\n)\n'
 (h/'compile.lisp').write_text(s+'\n(ccl:quit)\n')
 p=h/'compile.py';p.write_text(replace(p.read_text(),"ROOT=HERE.parents[3];REG=HERE.parent/'registration'",f"ROOT=Path({str(ROOT)!r});REG=ROOT/'tests/wasm/stage1/registration'"))
 sys.path.insert(0,str(h))
 spec=importlib.util.spec_from_file_location('d2_compile',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.run(e,out,code)
 import encode
 encode.Encoder.__init__.__defaults__=(ROOT/'doc/WASM/contracts/wasm32-layout.v1.json',16*1024*1024)
 from pool import compile_pool
 graph=read(out/'pools.json');keys=sorted({v['symbol'] for obj in graph['objects'] for v in obj['value'].get('elements',[]) if 'symbol' in v})
 symbols={k:620006+32*i for i,k in enumerate(keys)};plan=compile_pool(graph,symbols);material=plan.at(1048576)
 save(out/'materialized.json',dict(base=material.base,image=material.image.hex(),roots=material.roots,objects=[dict(id=i,offset=o,tag=t) for i,o,t in plan.objects],symbols=symbols))
 sys.path.pop(0)
def classify(p):
 x=subprocess.check_output(['/usr/local/bin/wasm-objdump','-x',p],text=True)
 d=subprocess.check_output(['/usr/local/bin/wasm-objdump','-d',p],text=True)
 p.with_suffix('.sections.txt').write_text(x);p.with_suffix('.instructions.txt').write_text(d)
 ops=sorted({line.split('|',1)[1].strip().split()[0] for line in d.splitlines() if '|' in line and line.split('|',1)[1].strip()})
 f=set()
 if re.search(r'-> \([^)]*,',x):f.add('multivalue')
 if any(op.startswith('return_call') for op in ops):f.add('tailcall')
 if any('.atomic.' in op for op in ops):f.add('atomics')
 if set(ops)&{'try_table','throw','throw_ref'}:f.add('exceptions')
 if 'exnref' in d or 'throw_ref' in ops:f.add('exnref')
 if set(ops)&{'memory.copy','memory.fill','memory.init','data.drop'}:f.add('bulk')
 return dict(binary_sha256=sha(p),features=sorted(f),wait=any(op.startswith('memory.atomic.wait') or op=='memory.atomic.notify' for op in ops),legacy=bool(set(ops)&{'try','catch','catch_all','delegate','rethrow'}),instruction_mnemonics=ops,sections_sha256=sha(p.with_suffix('.sections.txt')),instructions_sha256=sha(p.with_suffix('.instructions.txt')))
def execute_harness(out):
 # Reuse the accepted native-signature and escaping-closure oracle. Only host
 # plumbing changes: D2 install boundary and memory sharedness, never answers.
 s=(HERE.parent/'callable-metadata/execute.mjs').read_text()
 s=replace(s,"from './loader.mjs'","from './harness-installer.mjs'")
 s=replace(s,"const dir=process.argv[2];", "const dir=process.argv[2],profile=process.argv[4];")
 s=replace(s,'workerData:{dir,...data}', 'workerData:{dir,profile,...data}')
 s=replace(s,'const {dir,base,snapshot}=workerData','const {dir,base,snapshot,profile}=workerData')
 s=replace(s,'maximum:32769,shared:true','maximum:32769,shared:profile===\'full\'')
 s=replace(s,'new LazyLoader({memory,', 'new LazyLoader({directory:dir,profile,memory,')
 (out/'execute.mjs').write_text(s)
 C=HERE.parent/'constants'
 shutil.copy(ROOT/'doc/WASM/contracts/wasm32-layout.v1.json',out/'layout.json')
 for n in ['snapshot.mjs','transport.mjs']:
  s=(C/n).read_text().replace("new URL('../../../../doc/WASM/contracts/wasm32-layout.v1.json', import.meta.url)","new URL('./layout.json', import.meta.url)")
  if n=='snapshot.mjs':
   s=s.replace('export const digest', "tags.function = schema.subtags.find(x => x.name === 'subtag-function').value;\nexport const digest")
   s=replace(s,"if (tag === tags['simple-vector']) payload = 4*count;", "if (tag === tags.function) {check(count === 6, 'function count'); payload = 4*count;}\n      else if (tag === tags['simple-vector']) payload = 4*count;")
   s=replace(s,"if (tag === tags['simple-vector']) for", "if (tag === tags.function || tag === tags['simple-vector']) for")
  (out/n).write_text(s)
 command(['/usr/local/bin/wat2wasm','--enable-tail-call',ROOT/'runtime/wasm32/stub.wat','-o',out/'stub.wasm'],out/'stub.log')
def run(e,out):
 out.mkdir(parents=True,exist_ok=False)
 compile(e,out/'baseline',(ROOT/'compiler/wasm32/wasm32-backend.lisp').read_text(),False)
 compile(e,out/'default',generate(),False)
 compile(e,out/'templates',generate(),True)
 identical=[]
 for p in sorted((out/'baseline').iterdir()):
  if p.suffix in ['.wat','.wasm'] or p.name in ['modules.json','pools.json','native-metadata.json','native-behavior.json']:
   assert p.read_bytes()==(out/'default'/p.name).read_bytes(),p.name;identical.append(dict(path=p.name,sha256=sha(p)))
 save(out/'default-identical.json',identical)
 for n in ['bytes.mjs','sha256.mjs','binary.mjs']:shutil.copy(ROOT/'runtime/wasm32'/n,out/n)
 for n in ['materializer.mjs','harness-installer.mjs','check.mjs']:shutil.copy(HERE/n,out/n)
 save(out/'classifications.json',{p.stem:classify(p) for p in sorted((out/'templates').glob('*.wasm'))})
 bad=out/'malformed';bad.mkdir();leaf=(out/'templates/leaf.wat').read_text()
 variants={
  'unbounded':(leaf.replace('(memory 1 32769)','(memory 1)'),'CANONICAL_MEMORY'),
  'wrong-maximum':(leaf.replace('(memory 1 32769)','(memory 1 32768)'),'ABI_LIMITS'),
  'defined-memory':(leaf[:leaf.rfind(')')].replace('(import "env" "memory" (memory 1 32769))','')+' (memory 1 32769))','INITIALIZATION_OR_SECTION'),
  'start':(leaf[:leaf.rfind(')')]+' (func $badstart) (start $badstart))','INITIALIZATION_OR_SECTION'),
  'data':(leaf[:leaf.rfind(')')]+' (data (i32.const 1024) "bad"))','INITIALIZATION_OR_SECTION'),
  'wait':(leaf[:leaf.rfind(')')]+' (func (result i32) (memory.atomic.wait32 (i32.const 0) (i32.const 0) (i64.const 0))))','FORBIDDEN_INSTRUCTIONS'),
  'legacy':(leaf[:leaf.rfind(')')]+' (func (try (do) (catch_all))))','FORBIDDEN_INSTRUCTIONS')}
 rows={}
 for n,(wat,reason) in variants.items():
  p=bad/(n+'.wat');p.write_text(wat);command(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',p,'-o',p.with_suffix('.wasm')],p.with_suffix('.build.log'))
  rows[n]=dict(classification=classify(p.with_suffix('.wasm')),reason=reason)
 save(out/'malformed.json',rows)
 matrix=ROOT/'tests/wasm/stage0/engine-matrix/features.json'
 engine=e/'2026-09-15-engine-matrix-r2';environment=read(engine/'environment.json');row=next(r for r in read(engine/'matrix.json')['rows'] if r['engine']=='node')
 for p,h in environment['executable_sha256'].items():assert sha(Path(p))==h,p
 assert all(row['detection'][f] for f in read(matrix)['features'])
 save(out/'engine-join.json',dict(status='PASS',environment_sha256=sha(engine/'environment.json'),matrix_sha256=sha(engine/'matrix.json'),node=environment['node'],v8=environment['v8'],row=row,tools=environment['executable_sha256']))
 save(out/'policy.json',dict(materializer=dict(version='wasm32-d2-generated-v1',sha256=sha(out/'materializer.mjs')),engine_contract_sha256=sha(matrix),engine=dict(name='node',version=environment['node'],v8=environment['v8'],matrix_sha256=sha(engine/'matrix.json')),features=sorted(read(matrix)['features']),admission={k:row[k]['available'] for k in ['full','precompiled_callback']}))
 execute_harness(out)
 command(['/usr/local/bin/node',out/'check.mjs',out],out/'check.log')
 for profile in ['full','precompiled_callback']:
  command(['/usr/local/bin/node',out/'execute.mjs',out/profile,out/(profile+'.json'),profile],out/(profile+'.log'))
 a,b=read(out/'full.json'),read(out/'precompiled_callback.json')
 for x in [a,b]:
  for r in [x['origin'],*x['restored']]:r.pop('installations')
 assert a==b,'profile execution differs'
 save(out/'execution-equal.json',a)
 import controls
 controls.run(out,compile,e)
 import assessment
 save(out/'assessment.json',assessment.check(out));save(out/'publication-controls.json',assessment.controls(out))
 summary=dict(status='PASS',modules=len(read(out/'classifications.json')),default_identical=len(identical),profiles=['full','precompiled_callback'],workers=6,metadata_checks=sum(r['metadataChecks'] for r in [a['origin'],*a['restored']])*2,invocations=sum(len(r['observations']) for r in [a['origin'],*a['restored']])*2,checks=read(out/'checks.json'),mutants=read(out/'controls.json'))
 save(out/'summary.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--output',type=Path,required=True);v=a.parse_args();run(v.evidence.resolve(),v.output.resolve())
