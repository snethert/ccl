import argparse,hashlib,importlib.util,json,os,shutil,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];E=ROOT.parent/'ccl-evidence'
P=E/'2026-09-21-stage1-population-consumers-r1';T=E/'2026-09-21-stage1-typed-populations-r1';A=E/'2026-09-21-stage1-population-consumer-review-r1';Q=E/'2026-09-21-stage1-startup-review-138-r1'
NODE=Path('/usr/local/bin/node');CLANG=Path('/usr/local/opt/llvm/bin/clang');WABT=Path('/usr/local/bin/wat2wasm')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def replace(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def command(args,log,**kw):
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600,**kw)
def compile(out,source):
 spec=importlib.util.spec_from_file_location('pn_compile',ROOT/'tests/wasm/stage1/startup-joined/compile.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
 compiled=c.compile_source(E,out/'build',source,None);assert sha(compiled/'proposal/files/compiler/WASM32/wasm32-backend.lisp')==sha(ROOT/'compiler/WASM32/wasm32-backend.lisp')
 (out/'compiled').mkdir()
 for f in compiled.iterdir():
  if f.is_file() and f.suffix in ['.json','.wasm','.wat','.lisp'] and f.name!='command.json':shutil.copy(f,out/'compiled'/f.name)
def build_eql(out):
 flags=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536']
 command([CLANG,*flags,'-DMODE=1',*['-Wl,--export='+n for n in ['ht_eql','ht_run','ht_init','ht_size','ht_kind']],out/'eql.c','-o',out/'eql.wasm'],out/'eql-build.log')
def run(out):
 out.mkdir(parents=True,exist_ok=False)
 for p in [P,T,A,Q]:
  for n,h in read(p/'source-pins.json').items():assert sha(ROOT/n)==h,n
  for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256']
 save(out/'parents.json',{p.name:sha(p/'packet.json') for p in [P,T,A,Q]})
 deps=read(P/'execution/dependencies.json')
 for t in [NODE,CLANG,WABT]:assert sha(t)==deps['TOOL/'+str(t)]
 save(out/'tools.json',{str(t):sha(t) for t in [NODE,CLANG,WABT]})
 for n in ['consumers.lisp','lower.lisp','raw.mjs','admission.lisp']:shutil.copy(HERE/n,out/n)
 shutil.copy(A/'execution/lower.lisp',out/'base-lower.lisp')
 # Add an entry to the shared EQL service, calling its existing comparator.
 shared=(Q/'execution/services/eql.c').read_text()
 (out/'eql.c').write_text(shared+'\n'+(HERE/'eql-export.c').read_text());build_eql(out)
 save(out/'eql-binding.json',dict(shared_source_sha256=sha(Q/'execution/services/eql.c'),added_entry_sha256=sha(HERE/'eql-export.c'),entry='ht_eql',separate_comparison_implementation=False))
 adapter=(E/'2026-09-20-stage1-population-access-r1/execution/adapter.wat').read_text()
 a=adapter.index('  (if (i32.ne (i32.and (local.get $table)');b=adapter.index('  (local.set $status (call $run',a)
 adapter=adapter[:a]+'  (if (i32.ne (global.get $op) (i32.const 3)) (then\n'+adapter[a:b]+'))\n'+adapter[b:]
 (out/'eql-adapter.wat').write_text(adapter);command([WABT,'--enable-threads','--enable-exceptions',out/'eql-adapter.wat','-o',out/'eql-adapter.wasm'],out/'adapter-build.log')
 native=(ROOT/'tests/wasm/stage1/population-consumers/native.lisp').read_text().replace('((integerp x) (format s "~d" x))','''((and (integerp x) (<= (- (ash 1 29)) x (1- (ash 1 29)))) (format s "~d" x))
       ((integerp x) (format s "[\\\"integer\\\",\\\"~d\\\"]" x))
       ((floatp x) (format s "[\\\"double\\\",~f]" x))''')
 (out/'native.lisp').write_text(native)
 kernel=E/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=E/'2026-09-16-stage1-1a-r2/native/baseline.image'
 for p in [kernel,image]:assert sha(p)==read(P/'execution/inputs.json')[str(p)]
 with tempfile.TemporaryDirectory(prefix='ccl-pushnew-') as d:
  w=Path(d);shutil.copy(kernel,w/'dx86cl64');(w/'dx86cl64').chmod(0o755);shutil.copy(image,w/'dx86cl64.image')
  command([w/'dx86cl64','--no-init','--batch','--load',out/'native.lisp'],out/'native.log',env={**os.environ,'POP_CONSUMERS':str(out/'consumers.lisp'),'POP_NATIVE':str(out/'native.json')})
  command([w/'dx86cl64','--no-init','--batch','--load',out/'admission.lisp'],out/'admission.log',env={**os.environ,'PN_LOWER':str(out/'lower.lisp')})
  assert 'PUSHNEW-ADMISSION-PASS' in (out/'admission.log').read_text()
 source=(ROOT/'tests/wasm/stage1/population-consumers/compile.lisp').read_text()
 source=source.replace('ccl::lower-population-consumer','ccl::lower-population-pushnew').replace('"pop_gc"','"pop_gc" "pop_eql"')
 for n,path in [('consumers.lisp',out/'consumers.lisp'),('lower.lisp',out/'lower.lisp')]:source=source.replace('(merge-pathnames "'+n+'" *load-pathname*)',json.dumps(str(path)))
 compile(out,source)
 assert not any(m['name'].startswith('pop_adjoin_') and m['name']!='pop_adjoin_test' for m in read(out/'compiled/modules.json')),'ADJOIN must not allocate a local-function closure'
 for name in ['pop_adjoin','pop_adjoin_test']:assert '$tag_branch_' in (out/'compiled'/(name+'.wat')).read_text(),name+' branch loop'
 for n in ['builder.mjs','population.wasm','collector.wasm']:shutil.copy(T/'execution'/n,out/n)
 shutil.copy(P/'execution/adapter.wasm',out/'adapter.wasm')
 install=(P/'execution/install.mjs').read_text()
 install=replace(install," const adapter=await WebAssembly.compile", " const eql=(await WebAssembly.instantiate(fs.readFileSync(dir+'/eql.wasm'),{env:{memory}})).instance.exports;\n const eqlAdapter=await WebAssembly.compile(fs.readFileSync(dir+'/eql-adapter.wasm'));\n const adapter=await WebAssembly.compile")
 install=replace(install,"['pop_raw_type',2],['pop_gc',4]","['pop_raw_type',2],['pop_eql',3],['pop_gc',4]")
 install=replace(install,'new WebAssembly.Instance(adapter,{env,hash:{run:service.pop_run','new WebAssembly.Instance(op===3?eqlAdapter:adapter,{env,hash:{run:op===3?eql.ht_eql:service.pop_run')
 (out/'install.mjs').write_text(install)
 check=(P/'execution/check.mjs').read_text()
 check=replace(check,"throw Error('result tag '+v);", "if((v&7)===6&&(get(v-6)&255)===7){const n=get(v-6)>>>8;let x=0n;for(let i=n-1;i>=0;i--)x=(x<<32n)|BigInt(get(v-2+i*4));if(get(v-2+(n-1)*4)&0x80000000)x-=1n<<BigInt(32*n);return ['integer',String(x)];}if((v&7)===6&&(get(v-6)&255)===23)return ['double',d.getFloat64(v+2,true)];throw Error('result tag '+v);")
 check=replace(check,"['pc_collect','pc_closure','pc_cleanup','pc_exit']","['pn_collect','pn_place_collect','pn_cleanup']")
 check=replace(check,'  const values=gen.invoke', '  const allocationStart=get(tcr+48);\n  const values=gen.invoke')
 check=replace(check,'  assert.deepEqual(actual,expected,', '''  const delta=get(tcr+48)-allocationStart,expectedBytes={pn_duplicate:expected.type==='list'?0:8,pn_new:16,pn_twice:16,pn_equal_cons:16,pn_empty:8,pn_nil:8,pn_integer:8,pn_float:8,pn_eq:expected.type==='list'?0:8,pn_test_nil:expected.type==='list'?0:8}[expected.name];
  if(expectedBytes!==undefined)assert.equal(delta,expectedBytes,expected.name+' allocation');
  assert.deepEqual(actual,expected,''')
 check=replace(check,'externalCollection:true}', 'externalCollection:true,allocationBytes:expectedBytes??null}')
 (out/'check.mjs').write_text(check)
 command([NODE,out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 command([NODE,out/'raw.mjs',out,out/'raw.json'],out/'raw.log')
 controls=[]
 for name,a,b,why in [
  ('result-alignment','(result&3)||','','result-alignment'),
  ('result-bounds','!span(result,16)||','','result-bounds'),
  ('result-static','||overlap(result,16,1048576,65536)','','result-static'),
  ('left-key','!keys_valid(a,0,0,0,0,result)','0','left-key'),
  ('right-key','||!keys_valid(b,0,0,0,0,result)','','right-key'),
  ('eql-as-eq','same(a,b)?TRUE:NIL','(a==b)?TRUE:NIL','bignum publication')]:
  d=out/'faults'/name;d.mkdir(parents=True);(d/'eql.c').write_text(shared+'\n'+replace((HERE/'eql-export.c').read_text(),a,b));build_eql(d);shutil.copy(out/'raw.mjs',d/'raw.mjs')
  try:command([NODE,d/'raw.mjs',d,d/'result.json','all' if name=='eql-as-eq' else name],d/'rejected.log')
  except subprocess.CalledProcessError:assert why in (d/'rejected.log').read_text(),(name,(d/'rejected.log').read_text()[-1000:])
  else:raise AssertionError(name+' escaped')
  controls.append(dict(name=name,diagnostic=why,status='REJECTED'))
 for name,a,b,why in [
  ('duplicate','(setq answer list)','(setq answer (cons item list))','pn_duplicate'),
  ('operand-order','(lower (macroexpand-1 (list*', '(lower (reverse-pushnew-bindings (macroexpand-1 (list*','pn_effects')]:
  d=out/'faults'/name;d.mkdir(parents=True)
  text=(out/'lower.lisp').read_text()
  if name=='duplicate':text=text.replace(a,b,1)
  else:
   text=replace(text,a,b);text=replace(text,'(cdddr x)))))','(cdddr x))))))')
   text='(in-package :ccl)\n(defun reverse-pushnew-bindings (x) (rotatef (first (second x)) (second (second x))) x)\n'+text
  (d/'lower.lisp').write_text(text);shutil.copy(out/'base-lower.lisp',d/'base-lower.lisp')
  compile(d,source.replace(json.dumps(str(out/'lower.lisp')),json.dumps(str(d/'lower.lisp'))))
  for f in ['check.mjs','install.mjs','builder.mjs','population.wasm','collector.wasm','adapter.wasm','eql-adapter.wasm','eql.wasm','native.json']:shutil.copy(out/f,d/f)
  try:command([NODE,d/'check.mjs',d,d/'execution.json'],d/'rejected.log')
  except subprocess.CalledProcessError:assert why in (d/'rejected.log').read_text(),(name,(d/'rejected.log').read_text()[-1000:])
  else:raise AssertionError(name+' escaped')
  controls.append(dict(name=name,diagnostic=why,status='REJECTED'))
 save(out/'controls.json',controls)

 save(out/'summary.json',dict(status='PASS',modules=len(read(out/'compiled/modules.json')),native_cases=len(read(out/'native.json')),comparisons=sum(x['comparisons'] for x in read(out/'execution.json')['rows']),raw_checks=len(read(out/'raw.json')['rows']),controls=len(controls),admission_refusals=7,compiler_unchanged=True,slot_credit=False))
 print(read(out/'summary.json'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);run(p.parse_args().output.resolve())
