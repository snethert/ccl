"""Retain and replay the isolated closure-transfer and branch-loop proposal."""
import argparse,hashlib,json,shutil,sys,tarfile
from pathlib import Path
from backend import ROOT,generate
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run import command
from assessment import run as assessment
HERE=Path(__file__).resolve().parent;PARENT='2026-09-19-stage1-temporaries-r1'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(x,why):
 if not x:raise ValueError(why)
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and not f.is_symlink())
def archive(p,rows):
 with tarfile.open(p,'w:gz') as t:
  for f,n in rows:t.add(f,arcname=n,recursive=False)
def pins(e):
 result=read(e/PARENT/'source-pins.json');changes={r['file']:r for r in read(ROOT/'doc/WASM/stage1/integration-ll06.json')['files']}
 for n,h in list(result.items()):
  actual=sha(ROOT/n)
  if actual!=h:need(n in changes and changes[n]['before']==h and changes[n]['after']==actual,'reviewed integration '+n)
  result[n]=actual
 for f in files(HERE):result[str(f.relative_to(ROOT))]=sha(f)
 for n in ['doc/WASM/stage1/integration-ll06.json','compiler/nx1.lisp','compiler/X86/x862.lisp','compiler/ARM/arm2.lisp']:result[n]=sha(ROOT/n)
 return dict(sorted(result.items()))
def manifest(p):save(p/'packet.json',dict(id='STAGE1-CLOSURE-TRANSFERS-R1',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def selected(d):
 return {str(f.relative_to(d)):sha(f) for f in files(d) if (f.suffix in ('.wat','.wasm','.dx64fsl') or f.name in ['summary.json','native.json','execution.json','controls.json','cases.json','refusals.json','root-contracts.json','root-ir.json','assessment.json','shape.json','compatibility.json']) and not any(x in f.relative_to(d).parts for x in ['executed-sources','proposal'])}
def qualify(e,native,out):
 need((native/'proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()==generate(),'exact native proposal')
 command([sys.executable,HERE.parent/'registration/qualify.py','--output',native,'--inputs',e/'macos-u1-inputs','--kernel',e/'2026-09-12-native-census-r7/baseline/build/dx86cl64','--destination',out],out.with_suffix('.log'))
def retain(e,x,native,p):
 need(not p.exists(),'no overwrite');need(read(x/'summary.json')['status']=='PASS' and read(native/'run.json')['status']=='PASS','executions')
 p.mkdir();source=pins(e);save(p/'source-pins.json',source);archive(p/'source.tar.gz',[(ROOT/n,n) for n in source]);(p/'wasm32-backend.lisp').write_text(generate())
 need((x/'harness/wasm32-backend.lisp').read_text()==generate(),'executed compiler')
 qualify(e,native,p/'qualification');shutil.copytree(x/'assessment',p/'assessment');archive(p/'execution.tar.gz',[(f,str(f.relative_to(x))) for f in files(x)]);save(p/'deterministic.json',selected(x))
 known={r['sha256']:str((e/'2026-09-16-stage1-1a-r2'/r['path']).relative_to(e)) for r in read(e/'2026-09-16-stage1-1a-r2/packet.json')['files']};refs=[];rows=[]
 for f in files(native):
  n=str(f.relative_to(native));h=sha(f)
  if h in known:refs.append(dict(path=n,sha256=h,evidence_path=known[h]))
  else:rows.append((f,n))
 archive(p/'native.tar.gz',rows);save(p/'native-references.json',refs)
 for n in ['scope.json','coverage.json']:shutil.copy(HERE/n,p/n)
 for n in ['options.json','abi-decision.json','abi-binding.json','toolchain.json']:shutil.copy(e/PARENT/n,p/n)
 options=read(p/'options.json');options.update(profile='wasm32-shared-B-exnref-control-v1',native_R6='executed new isolated compiler');save(p/'options.json',options)
 for n in ['collector.c','collector.wasm']:shutil.copy(x/'harness'/n,p/n);need(sha(p/n)==sha(e/PARENT/n),'reviewed collector')
 positive=p/'positive';positive.mkdir();(positive/'installed').mkdir()
 for n in ['closed','handler','restart','fast_loop','local_cleanup']:
  for ext in ['wat','wasm']:shutil.copy(x/'generated/compiled'/(n+'.'+ext),positive/(n+'.'+ext))
  shutil.copy(x/'generated/compiled'/(n+'.wasm'),positive/'installed'/(n+'.wasm'))
 shutil.copy(x/'generated/compiled/compiler.dx64fsl',positive/'compiler.dx64fsl')
 save(p/'summary.json',dict(read(x/'assessment/assessment.json'),inventory_credit=False,modules=read(x/'summary.json')['modules'],review_disposition='NOT_REVIEWED',scope=read(p/'scope.json'),native=read(p/'qualification/summary.json')))
 refs=[dict(locator=PARENT+'/'+n,sha256=sha(e/PARENT/n)) for n in ['packet.json','collector.c','collector.wasm','source-pins.json','execution.tar.gz']];save(p/'inputs.json',dict(references=refs))
 dev=[]
 for stem in ['ccl-closure-transfers-r2','ccl-closure-transfers-r4','ccl-closure-transfers-r5','ccl-closure-transfers-r6']:
  d=Path('/tmp')/stem
  for f in files(d):
   if not any(x in f.relative_to(d).parts for x in ['executed-sources','proposal']):dev.append((f,stem+'/'+str(f.relative_to(d))))
  log=Path('/tmp')/(stem+'.log')
  if log.exists():dev.append((log,stem+'/driver.log'))
 archive(p/'development.tar.gz',dev);save(p/'development.json',dict(notes=[
  'r2: a probe closed its TAGBODY before the intended label. Native compilation correctly refused the missing tag; exact form and log retained. Compiler unchanged.',
  'r4: the strengthened stale-activation test expected a control error after dynamic extent. Native instead reached a reused stack catch and returned zero. This out-of-extent case is retained, not used as a portable/native identity oracle. The final closed_nearest test has two simultaneously live targets.',
  'r5: the unsafe-branch mutant escaped go_operand because the function return restored the abandoned temporary before an observer saw it. The same mutated compiler now executes local_cleanup, whose skipped cleanup is directly visible. No producer change.',
  'r6: a missing branch escaped a forward-only case because its changed program counter still selected the correct later segment. The unchanged mutant is now rejected by the 4000-iteration backedge case. No producer change.',
  'Other development runs passed intermediate corpora and were superseded. One final packet retains the exact final proposal, outputs, original failures and newly executed native R6/R6a.'
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
 qualify(e,native,out/'qualification')
 command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution','--qualify'],out/'execution.log')
 actual=selected(out/'execution');expected=read(p/'deterministic.json');need(actual.keys()==expected.keys(),'replay membership')
 for n,h in expected.items():need(actual[n]==h,'replay '+n)
 need(source==pins(e),'source stability');result=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source),native=read(out/'qualification/summary.json'));save(out/'verification.json',result);print(result)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True)
 for n in ['execution','native','output']:a.add_argument('--'+n,type=Path)
 v=a.parse_args()
 if v.mode=='retain':retain(v.evidence.resolve(),v.execution.resolve(),v.native.resolve(),v.packet.resolve())
 else:verify(v.evidence.resolve(),v.packet.resolve(),v.output.resolve())
