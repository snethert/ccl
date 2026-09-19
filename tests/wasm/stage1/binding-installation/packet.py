"""Retain and independently replay LL11-a; unchanged native R6 is hash-reused."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];PARENT='2026-09-19-stage1-callable-metadata-r1'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(x,why):
 if not x:raise ValueError(why)
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and not f.is_symlink())
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1200)
def archive(p,rows):
 with tarfile.open(p,'w:gz') as t:
  for f,n in rows:t.add(f,arcname=n,recursive=False)
def pins(e):
 need(set(read(HERE/'coverage.json'))=={'S1-LL11-a:aliases'},'assertion coverage')
 result=read(e/PARENT/'source-pins.json');changes={r['file']:r for r in read(ROOT/'doc/WASM/stage1/integration-ll12.json')['files']}
 for n,h in list(result.items()):
  actual=sha(ROOT/n)
  if actual!=h:need(n in changes and changes[n]['before']==h and changes[n]['after']==actual,'reviewed integration '+n)
  result[n]=actual
 for f in files(HERE):result[str(f.relative_to(ROOT))]=sha(f)
 result['doc/WASM/stage1/integration-ll12.json']=sha(ROOT/'doc/WASM/stage1/integration-ll12.json')
 return dict(sorted(result.items()))
def manifest(p):save(p/'packet.json',dict(id='STAGE1-BINDING-INSTALLATION-R1',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def selected(d):
 names={'summary.json','execution.json','controls.json','assessment.json','pools.json','native-metadata.json','native-behavior.json','modules.json','inputs.json'}
 return {str(f.relative_to(d)):sha(f) for f in files(d) if (f.suffix in ('.wat','.wasm','.dx64fsl') or f.name in names or f.name.startswith('materialized-')) and not any(x in f.relative_to(d).parts for x in ['executed-sources','proposal'])}
def native_reuse(e):
 c=ROOT/'compiler/WASM32/wasm32-backend.lisp';need(sha(c)==sha(e/PARENT/'wasm32-backend.lisp'),'unchanged accepted compiler')
 integration=read(ROOT/'doc/WASM/stage1/integration-ll12.json');need(integration['files'][0]['after']==sha(c),'integrated compiler identity')
 for r in integration['unchanged_integrated_files']:need(sha(ROOT/r['file'])==r['sha256'],'unchanged runtime '+r['file'])
 summary=read(e/PARENT/'qualification/summary.json');need(summary['status']=='PASS','accepted native qualification')
 return dict(status='PASS',mode='REUSED_BY_EXACT_COMPILER_AND_RUNTIME_HASH; native fixture oracles re-executed',compiler_sha256=sha(c),integration_sha256=sha(ROOT/'doc/WASM/stage1/integration-ll12.json'),qualification=summary)
def retain(e,x,p):
 need(not p.exists(),'never overwrite');need(read(x/'summary.json')['status']=='PASS','execution');p.mkdir();source=pins(e)
 save(p/'source-pins.json',source);archive(p/'source.tar.gz',[(ROOT/n,n) for n in source]);save(p/'native-reuse.json',native_reuse(e))
 need(sha(x/'compiled/proposal/files/compiler/WASM32/wasm32-backend.lisp')==sha(e/PARENT/'wasm32-backend.lisp'),'executed compiler')
 archive(p/'execution.tar.gz',[(f,str(f.relative_to(x))) for f in files(x)]);save(p/'deterministic.json',selected(x));shutil.copytree(x/'assessment',p/'assessment')
 for n in ['installer.mjs','ranges.mjs','scope.json','coverage.json']:shutil.copy(HERE/n,p/n)
 for n in ['abi-decision.json','abi-binding.json','toolchain.json']:shutil.copy(e/PARENT/n,p/n)
 save(p/'options.json',dict(profile='wasm32-shared-B-exnref-control-v1',compiler_mode='compile-metadata-call-form; unchanged accepted compiler',placements=[1048576,2147483648],registry_capacity=64,reserved_prefix=4,owner='single Worker synchronous transaction; trusted manifest and import capabilities',native_R6='reused exact LL12 compiler'))
 positive=p/'positive';positive.mkdir();(positive/'installed').mkdir()
 for f in (x/'compiled').iterdir():
  if f.suffix in ['.wat','.wasm','.dx64fsl']:
   shutil.copy(f,positive/f.name)
   if f.suffix=='.wasm':shutil.copy(f,positive/'installed'/f.name)
 save(p/'summary.json',dict(read(x/'summary.json'),review_disposition='NOT_REVIEWED',scope=read(p/'scope.json'),native=read(p/'native-reuse.json')))
 refs=[dict(locator=PARENT+'/'+n,sha256=sha(e/PARENT/n)) for n in ['packet.json','source-pins.json','wasm32-backend.lisp','qualification/summary.json','qualification/verification.json','native.tar.gz','native-references.json']];save(p/'inputs.json',dict(references=refs))
 dev=[]
 for number in [1,3]:
  stem='ccl-binding-installation-r'+str(number);d=Path('/tmp')/stem
  for f in files(d):
   rel=f.relative_to(d)
   if 'executed-sources' not in rel.parts and (f.suffix in ['.log','.lisp','.mjs','.wat','.wasm'] or f.name.endswith('command.json')):dev.append((f,stem+'/'+str(rel)))
  log=Path('/tmp')/(stem+'.log')
  if log.exists():dev.append((log,stem+'/driver.log'))
 archive(p/'development.tar.gz',dev);save(p/'development.json',dict(notes=['r1: native oracle LET* binding list lacked a closing parenthesis; original compile input and native refusal retained.','r3: a rollback mutant correctly changed state, but the Worker could not serialize its assertion object containing Wasm functions. The harness now prints the original stack in the Worker before exit, preserving the specific oracle. Installer unchanged.','r2/r4/r5 positive development runs are superseded by the final qualification; all seven semantic faults and both memory placements execute in the retained run.']))
 need(source==pins(e),'source stability');manifest(p)
def verify(e,p,out):
 out.mkdir(parents=True,exist_ok=False);source=pins(e);need(source==read(p/'source-pins.json'),'pins')
 for r in read(p/'packet.json')['files']:need(sha(p/r['path'])==r['sha256'],'packet '+r['path'])
 for r in read(p/'inputs.json')['references']:need(sha(e/r['locator'])==r['sha256'],'input '+r['locator'])
 for r in read(p/'toolchain.json')['tools']:need(sha(Path(r['path']))==r['sha256'],'tool '+r['path'])
 need(native_reuse(e)==read(p/'native-reuse.json'),'native R6 reuse')
 command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution','--qualify'],out/'execution.log');actual=selected(out/'execution');expected=read(p/'deterministic.json');need(actual.keys()==expected.keys(),'replay population')
 for n,h in expected.items():need(actual[n]==h,'replay '+n)
 need(source==pins(e),'source stability');result=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source),native_R6='reused by unchanged compiler hash');save(out/'verification.json',result);print(result)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True)
 for n in ['execution','output']:a.add_argument('--'+n,type=Path)
 v=a.parse_args()
 if v.mode=='retain':retain(v.evidence.resolve(),v.execution.resolve(),v.packet.resolve())
 else:verify(v.evidence.resolve(),v.packet.resolve(),v.output.resolve())
