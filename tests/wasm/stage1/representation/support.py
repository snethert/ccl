import hashlib,importlib.util,json,os,shutil,subprocess,sys,tarfile,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];REG=HERE.parent/'registration'
sys.path.insert(0,str(REG));import unit
from unit import Unit
from corpus import cases,source,FORMS

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def require(x,reason):
 if not x:raise ValueError(reason)
def proposal(src,out,backend=None):
 m=unit.proposal(src,out);p=out/'files/compiler/WASM32/wasm32-backend.lisp';p.write_bytes((backend or HERE/'wasm32-backend.lisp').read_bytes())
 next(r for r in m['added'] if r['path']=='compiler/WASM32/wasm32-backend.lisp')['sha256']=sha(p);save(out/'unit.json',m);return m

def literal(v):
 if isinstance(v,list):return '('+' '.join(literal(x) for x in v)+')'
 if isinstance(v,str):return json.dumps(v)
 return str(v)
def compile_cases(evidence,out,backend=None):
 require(not out.exists(),'NO_OVERWRITE');out.mkdir(parents=True)
 (out/'executed-sources').mkdir()
 for p in HERE.iterdir():
  if p.is_file():shutil.copy(p,out/'executed-sources'/p.name)
 corpus=cases();save(out/'cases.json',corpus)
 forms=[(n,source(n)) for n in FORMS]
 (out/'cases.lisp').write_text('(in-package "CL-USER")\n(defparameter *repr-sources* \''+literal([list(x) for x in forms])+')\n(defparameter *repr-cases* \''+literal([[c['id'],c['function'],c['nodes'],c['args']] for c in corpus])+')\n')
 for name,text in forms:(out/(name+'.lisp')).write_text(text+'\n')
 with tempfile.TemporaryDirectory(prefix='ccl-representation-') as temp:
  work=Path(temp).resolve();src=work/'ccl';src.mkdir();save(work/'stage1-disposable.json',{'source':str(src)})
  inputs=evidence/'macos-u1-inputs';pins=read(inputs/'pins.json')
  require(sha(inputs/'source.tar')==pins['inputs']['source.tar'],'SOURCE_ARCHIVE')
  with tarfile.open(inputs/'source.tar') as t:t.extractall(src,filter='data')
  require(sha(inputs/'bootstrap.tar.gz')==pins['inputs']['bootstrap.tar.gz'],'BOOTSTRAP_ARCHIVE')
  with tarfile.open(inputs/'bootstrap.tar.gz') as t:t.extractall(src,filter='data')
  original=evidence/'2026-09-16-stage1-1a-r2';kernel=evidence/'2026-09-12-native-census-r7/baseline/build/dx86cl64'
  shutil.copy(kernel,src/'dx86cl64');(src/'dx86cl64').chmod(0o755);shutil.copy(original/'native/baseline.image',src/'dx86cl64.image')
  proposal(src,out/'proposal',backend)
  with Unit(src,out/'proposal'):
   argv=[str(src/'dx86cl64'),'--no-init','--batch','--eval','(ccl::in-development-mode (load "ccl:lib;systems.lisp") (load "ccl:lib;compile-ccl.lisp"))','--load',str(REG/'load.lisp'),'--load',str(HERE/'compile.lisp')]
   env={'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C','LC_ALL':'C','CCL_DEFAULT_DIRECTORY':str(src),'REPR_OUTPUT':str(out)+'/', 'REPR_CASES':str(out/'cases.lisp')}
   save(out/'command.json',{'argv':argv,'cwd':str(src),'environment':env,'kernel_sha256':sha(kernel),'image_sha256':sha(original/'native/baseline.image'),'inputs':pins})
   with (out/'compile.log').open('w') as log:child=subprocess.run(argv,cwd=src,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
   require(child.returncode==0 and 'S1-REPRESENTATION-COMPILE-PASS' in (out/'compile.log').read_text(),'NATIVE_COMPILE '+str(out/'compile.log'))
   shutil.copy(src/'bin/wasm32-backend.dx64fsl',out/'compiler.dx64fsl')
  require(all(sha(src/r['path'])==r['before'] for r in read(out/'proposal/unit.json')['modified']),'SOURCE_RESTORATION')
 native=read(out/'native.json');require(len(native)==len(corpus),'NATIVE_COUNT')
 for a,b in zip(native,corpus):require(a==dict(id=b['id'],**b['expected']),'NATIVE_ORACLE '+b['id'])
 (out/'installed').mkdir()
 for name,_ in forms:
  subprocess.run(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions',str(out/(name+'.wat')),'-o',str(out/(name+'.wasm'))],check=True,capture_output=True)
  shutil.copy(out/(name+'.wasm'),out/'installed'/(name+'.wasm'))
 save(out/'compile-summary.json',{'status':'PASS','modules':len(forms),'cases':len(corpus),'returns':sum(c['expected']['status']=='RETURN' for c in corpus),'type_errors':sum(c['expected']['status']=='TYPE_ERROR' for c in corpus),'source_restored':True})
