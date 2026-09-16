import hashlib,json,os,shutil,subprocess,sys,tarfile,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];REG=HERE.parent/'registration'
sys.path.insert(0,str(REG));import unit
from unit import Unit

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def require(x,reason):
 if not x:raise ValueError(reason)
def proposal(src,out,backend=None):
 m=unit.proposal(src,out);p=out/'files/compiler/WASM32/wasm32-backend.lisp';p.write_bytes((backend or HERE/'wasm32-backend.lisp').read_bytes())
 next(r for r in m['added'] if r['path']=='compiler/WASM32/wasm32-backend.lisp')['sha256']=sha(p);save(out/'unit.json',m);return m

def compile_cases(evidence,out,backend=None):
 from corpus import modules,cases,lisp_input
 require(not out.exists(),'NO_OVERWRITE');out.mkdir(parents=True)
 layout=read(HERE/'layout.json');d1=read(ROOT/'doc/WASM/contracts/wasm32-layout.v1.json')
 def rows(value):
  if isinstance(value,dict):
   yield value
   for v in value.values():yield from rows(v)
  elif isinstance(value,list):
   for v in value:yield from rows(v)
 for name in ('symbol','function'):
  subtag=next(r['value'] for r in rows(d1) if r.get('name')=='subtag-'+name)
  require(subtag==layout[name]['subtag'] and layout[name]['header']==256*layout[name]['elements']+subtag,'D1_HEADER '+name)
 symbol=next(r for r in rows(d1) if r.get('name')=='symbol' and 'cells' in r)
 require(symbol['size_bytes']==layout['symbol']['bytes'] and next(r['raw_offset'] for r in symbol['cells'] if r['name']=='fcell')==layout['symbol']['function_cell'],'D1_SYMBOL_LAYOUT')
 save(out/'layout.json',layout)
 (out/'executed-sources').mkdir()
 for p in HERE.iterdir():
  if p.is_file():shutil.copy(p,out/'executed-sources'/p.name)
 save(out/'modules.json',modules());save(out/'cases.json',cases());(out/'cases.lisp').write_text(lisp_input())
 for m in modules():(out/(m['name']+'.lisp')).write_text(m['source']+'\n')
 with tempfile.TemporaryDirectory(prefix='ccl-b-calls-') as temp:
  work=Path(temp).resolve();src=work/'ccl';src.mkdir();save(work/'stage1-disposable.json',{'source':str(src)})
  inputs=evidence/'macos-u1-inputs';pins=read(inputs/'pins.json')
  for archive in ('source.tar','bootstrap.tar.gz'):
   require(sha(inputs/archive)==pins['inputs'][archive],'ARCHIVE '+archive)
   with tarfile.open(inputs/archive) as t:t.extractall(src,filter='data')
  original=evidence/'2026-09-16-stage1-1a-r2';kernel=evidence/'2026-09-12-native-census-r7/baseline/build/dx86cl64'
  shutil.copy(kernel,src/'dx86cl64');(src/'dx86cl64').chmod(0o755);shutil.copy(original/'native/baseline.image',src/'dx86cl64.image')
  proposal(src,out/'proposal',backend)
  with Unit(src,out/'proposal'):
   argv=[str(src/'dx86cl64'),'--no-init','--batch','--eval','(ccl::in-development-mode (load "ccl:lib;systems.lisp") (load "ccl:lib;compile-ccl.lisp"))','--load',str(REG/'load.lisp'),'--load',str(HERE/'compile.lisp')]
   env={'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C','LC_ALL':'C','CCL_DEFAULT_DIRECTORY':str(src),'CALL_OUTPUT':str(out)+'/', 'CALL_CASES':str(out/'cases.lisp')}
   save(out/'command.json',{'argv':argv,'cwd':str(src),'environment':env,'kernel_sha256':sha(kernel),'image_sha256':sha(original/'native/baseline.image'),'inputs':pins})
   with (out/'compile.log').open('w') as log:child=subprocess.run(argv,cwd=src,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
   require(child.returncode==0 and 'S1-B-CALL-COMPILE-PASS' in (out/'compile.log').read_text(),'NATIVE_COMPILE '+str(out/'compile.log'))
   shutil.copy(src/'bin/wasm32-backend.dx64fsl',out/'compiler.dx64fsl')
  require(all(sha(src/r['path'])==r['before'] for r in read(out/'proposal/unit.json')['modified']),'SOURCE_RESTORATION')
 native=read(out/'native.json');expected=[dict(id=c['id'],**c['expected']) for c in cases()];require(native==expected,'NATIVE_ORACLE')
 (out/'installed').mkdir()
 for m in modules()+[{'name':'resolve_slot'},{'name':'observe_entry'}]:
  name=m['name']
  with (out/(name+'-assembler.log')).open('w') as log:
   subprocess.run(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions',str(out/(name+'.wat')),'-o',str(out/(name+'.wasm'))],check=True,stdout=log,stderr=subprocess.STDOUT)
  shutil.copy(out/(name+'.wasm'),out/'installed'/(name+'.wasm'))
 save(out/'compile-summary.json',{'status':'PASS','modules':len(modules()),'source_restored':True})
