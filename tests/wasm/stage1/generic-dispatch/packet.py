"""Retain and replay the generic dispatch qualification from pinned inputs."""
import argparse,hashlib,importlib.util,json,shutil,sys,tarfile
from pathlib import Path
from backend import ROOT,generate
HERE=Path(__file__).resolve().parent;PARENT='2026-09-19-stage1-binding-installation-r1'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(x,why):
 if not x:raise ValueError(why)
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and not f.is_symlink())
def command(args,log):
 import subprocess
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1200)
def archive(p,rows):
 with tarfile.open(p,'w:gz') as t:
  for f,n in rows:t.add(f,arcname=n,recursive=False)
def pins(e):
 need(set(read(HERE/'coverage.json'))=={'S1-LL11-b:empty-registry'},'inventory assertion coverage')
 result=read(e/PARENT/'source-pins.json');changes={r['file']:r for r in read(ROOT/'doc/WASM/stage1/integration-ll11a.json')['files']}
 for n,h in list(result.items()):
  actual=sha(ROOT/n)
  if actual!=h:need(n in changes and changes[n]['before']==h and changes[n]['after']==actual,'reviewed integration '+n)
  result[n]=actual
 for f in files(HERE):result[str(f.relative_to(ROOT))]=sha(f)
 for n in ['doc/WASM/stage1/integration-ll11a.json','runtime/wasm32/installer.mjs','runtime/wasm32/ranges.mjs','level-1/l1-clos-boot.lisp','level-1/l1-dcode.lisp','level-1/l1-error-system.lisp','lib/encapsulate.lisp','tests/wasm/native-census/dispatch-registry/removal-probe.lisp']:result[n]=sha(ROOT/n)
 return dict(sorted(result.items()))
def manifest(p):save(p/'packet.json',dict(id='STAGE1-GENERIC-DISPATCH-R1',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def selected(d):
 names={'summary.json','native.json','execution.json','controls.json','snapshot-controls.json','cases.json','refusals.json','root-contracts.json','root-ir.json','assessment.json','shape.json','compatibility.json','default-compatibility.json','pools.json','native-metadata.json','native-behavior.json','native-order.json','native-flow.json','native-condition-classes.json','inputs.json','materialized.json','snapshot.json','modules.json'}
 return {str(f.relative_to(d)):sha(f) for f in files(d) if (f.suffix in ('.wat','.wasm','.dx64fsl') or f.name in names or f.name.startswith('materialized-')) and not any(x in f.relative_to(d).parts for x in ['executed-sources','proposal'])}
def qualify(e,native,out):
 need((native/'proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()==generate(),'exact native proposal')
 command([sys.executable,HERE.parent/'registration/qualify.py','--output',native,'--inputs',e/'macos-u1-inputs','--kernel',e/'2026-09-12-native-census-r7/baseline/build/dx86cl64','--destination',out],out.with_suffix('.log'))
def retain(e,x,native,p):
 need(not p.exists(),'no overwrite');need(read(x/'summary.json')['status']=='PASS' and read(native/'run.json')['status']=='PASS','executions');p.mkdir()
 source=pins(e);save(p/'source-pins.json',source);archive(p/'source.tar.gz',[(ROOT/n,n) for n in source]);(p/'wasm32-backend.lisp').write_text(generate())
 need((x/'compiled/proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()==generate(),'executed compiler')
 qualify(e,native,p/'qualification');shutil.copytree(x/'assessment',p/'assessment');archive(p/'execution.tar.gz',[(f,str(f.relative_to(x))) for f in files(x)]);save(p/'deterministic.json',selected(x))
 known={r['sha256']:str((e/'2026-09-16-stage1-1a-r2'/r['path']).relative_to(e)) for r in read(e/'2026-09-16-stage1-1a-r2/packet.json')['files']};refs=[];rows=[]
 for f in files(native):
  n=str(f.relative_to(native));h=sha(f)
  if h in known:refs.append(dict(path=n,sha256=h,evidence_path=known[h]))
  else:rows.append((f,n))
 archive(p/'native.tar.gz',rows);save(p/'native-references.json',refs)
 for n in ['scope.json','coverage.json']:shutil.copy(HERE/n,p/n)
 for n in ['options.json','abi-decision.json','abi-binding.json','toolchain.json']:shutil.copy(e/PARENT/n,p/n)
 options=dict(profile='wasm32-shared-B-exnref-control-v1',compiler_mode='compile-metadata-call-form; bounded twelve/thirteen-class condition registry',native_R6='executed new isolated compiler',placements=[1048576,2147483648],registry_capacity=128,reserved_prefix=4);save(p/'options.json',options)
 positive=p/'positive';positive.mkdir();(positive/'installed').mkdir()
 for f in (x/'compiled').iterdir():
  if f.suffix in ['.wat','.wasm','.dx64fsl']:
   shutil.copy(f,positive/f.name)
   if f.suffix=='.wasm':shutil.copy(f,positive/'installed'/f.name)
 for n in ['runtime.lisp','condition.lisp']:shutil.copy(HERE/n,p/n)
 save(p/'summary.json',dict(read(x/'summary.json'),review_disposition='NOT_REVIEWED',scope=read(p/'scope.json'),native=read(p/'qualification/summary.json')))
 refs=[dict(locator=PARENT+'/'+n,sha256=sha(e/PARENT/n)) for n in ['packet.json','source-pins.json']];save(p/'inputs.json',dict(references=refs))
 dev=[]
 for stem in ['ccl-gd-r1','ccl-gd-r2','ccl-gd-r4','ccl-gd-r5','ccl-gd-r9','ccl-gd-r12','ccl-gd-r13','ccl-gd-harness-r6']:
  d=Path('/tmp')/stem
  for f in files(d):
   rel=f.relative_to(d)
   if not any(a in rel.parts for a in ['executed-sources','compatibility','proposal']) and (f.suffix in ['.log','.lisp','.mjs','.wat','.wasm'] or f.name.endswith('command.json')):dev.append((f,stem+'/'+str(rel)))
  log=Path('/tmp')/(stem+'.log')
  if log.exists():dev.append((log,stem+'/driver.log'))
 archive(p/'development.tar.gz',dev)
 save(p/'development.json',dict(notes=[
  'r1: private helper names contained characters the existing link-name admission refuses. Renamed with the admitted identifier alphabet.',
  'r2/r4: fixture IGNORE declarations and the new quoted condition class were refused by admission. Removed unsupported IGNORE declarations; added the new condition type to the existing admitted mask list.',
  'r5: the harness supplied a tagged binding-vector address where the TCR requires its untagged data address. Corrected the owner setup. The harness-r6 failure expected one extra envelope entry on an arity error; arity is checked before entering the envelope, so the independent count is fifteen.',
  'r9: a real selector error chose a newly prepended universal method before an EQL method. The corrected selector carries the universal method as fallback until the exact key search ends. Rejected original source and compiled output are retained, and the universal-first compiled control re-executes it.',
  'r12: qualification orchestration used an undefined local evidence path after a successful positive run. Corrected the driver variable; compiler and runtime unchanged.',
  'r13: the first retain-dcode mutant was ineffective because recomputation already passed the missing-method entry. The retained control now omits dispatch publication on an empty list, reproducing the native WHEN-METHODS defect. No escaped fault was counted.',
  'Successful exploratory runs are superseded; one final packet retains all qualified results and the original failures.'
 ]))
 need(source==pins(e),'source stability');manifest(p)
def verify(e,p,out):
 out.mkdir(parents=True,exist_ok=False);source=pins(e);need(source==read(p/'source-pins.json'),'pins')
 for r in read(p/'packet.json')['files']:need(sha(p/r['path'])==r['sha256'],'packet '+r['path'])
 for r in read(p/'inputs.json')['references']:need(sha(e/r['locator'])==r['sha256'],'input '+r['locator'])
 for r in read(p/'toolchain.json')['tools']:need(sha(Path(r['path']))==r['sha256'],'tool '+r['path'])
 native=out/'native';native.mkdir()
 with tarfile.open(p/'native.tar.gz') as t:t.extractall(native,filter='data')
 for r in read(p/'native-references.json'):
  src=e/r['evidence_path'];need(sha(src)==r['sha256'],'native reference');dest=native/r['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(src,dest)
 qualify(e,native,out/'qualification');command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution','--qualify'],out/'execution.log')
 actual=selected(out/'execution');expected=read(p/'deterministic.json');need(actual.keys()==expected.keys(),'replay membership')
 for n,h in expected.items():need(actual[n]==h,'replay '+n)
 need(source==pins(e),'source stability');result=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source),native=read(out/'qualification/summary.json'));save(out/'verification.json',result);print(result)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True)
 for n in ['execution','native','output']:a.add_argument('--'+n,type=Path)
 v=a.parse_args()
 if v.mode=='retain':retain(v.evidence.resolve(),v.execution.resolve(),v.native.resolve(),v.packet.resolve())
 else:verify(v.evidence.resolve(),v.packet.resolve(),v.output.resolve())
