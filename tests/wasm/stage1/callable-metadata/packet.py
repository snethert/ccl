"""Retain and replay the callable metadata qualification from pinned inputs."""
import argparse,hashlib,importlib.util,json,shutil,sys,tarfile
from pathlib import Path
from backend import ROOT,generate
HERE=Path(__file__).resolve().parent;PARENT='2026-09-19-stage1-closure-transfers-r1'
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
 need(set(read(HERE/'coverage.json'))=={'S1-LL12-a:closures'},'inventory assertion coverage')
 result=read(e/PARENT/'source-pins.json');changes={r['file']:r for r in read(ROOT/'doc/WASM/stage1/integration-closure-transfers.json')['files']}
 for n,h in list(result.items()):
  actual=sha(ROOT/n)
  if actual!=h:need(n in changes and changes[n]['before']==h and changes[n]['after']==actual,'reviewed integration '+n)
  result[n]=actual
 for f in files(HERE):result[str(f.relative_to(ROOT))]=sha(f)
 for n in ['doc/WASM/stage1/integration-closure-transfers.json','lib/backtrace.lisp','lib/arglist.lisp','level-1/l1-aprims.lisp','level-0/X86/x86-def.lisp']:result[n]=sha(ROOT/n)
 return dict(sorted(result.items()))
def manifest(p):save(p/'packet.json',dict(id='STAGE1-CALLABLE-METADATA-R1',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def selected(d):
 names={'summary.json','native.json','execution.json','controls.json','snapshot-controls.json','cases.json','refusals.json','root-contracts.json','root-ir.json','assessment.json','shape.json','compatibility.json','default-compatibility.json','pools.json','native-metadata.json','native-behavior.json','materialized.json','snapshot.json','modules.json'}
 return {str(f.relative_to(d)):sha(f) for f in files(d) if (f.suffix in ('.wat','.wasm','.dx64fsl') or f.name in names) and not any(x in f.relative_to(d).parts for x in ['executed-sources','proposal'])}
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
 options=read(p/'options.json');options.update(profile='wasm32-shared-B-exnref-control-v1',compiler_mode='compile-metadata-call-form; default mode unchanged',native_R6='executed new isolated compiler');save(p/'options.json',options)
 positive=p/'positive';positive.mkdir();(positive/'installed').mkdir()
 for f in (x/'compiled').iterdir():
  if f.suffix in ['.wat','.wasm','.dx64fsl']:
   shutil.copy(f,positive/f.name)
   if f.suffix=='.wasm':shutil.copy(f,positive/'installed'/f.name)
 for n in ['snapshot.mjs','transport.mjs']:shutil.copy(x/n,p/n)
 save(p/'summary.json',dict(read(x/'summary.json'),review_disposition='NOT_REVIEWED',scope=read(p/'scope.json'),native=read(p/'qualification/summary.json')))
 refs=[dict(locator=PARENT+'/'+n,sha256=sha(e/PARENT/n)) for n in ['packet.json','source-pins.json','execution.tar.gz']];save(p/'inputs.json',dict(references=refs))
 dev=[]
 for number in [1,3,4,5,6,7,8,10,11,12,13,14]:
  stem='ccl-callable-metadata-r'+str(number);d=Path('/tmp')/stem
  for f in files(d):
   rel=f.relative_to(d)
   if not any(a in rel.parts for a in ['executed-sources','compatibility']) and (f.suffix in ['.log','.lisp','.mjs','.wat','.wasm'] or f.name in ['command.json','pools.json','native-metadata.json']):dev.append((f,stem+'/'+str(rel)))
  log=Path('/tmp')/(stem+'.log')
  if log.exists():dev.append((log,stem+'/driver.log'))
 archive(p/'development.tar.gz',dev)
 save(p/'development.json',dict(notes=[
  'r1: copied driver lacked its import path. r3/r4: two corpus parenthesis mistakes, native reader/compiler refusals retained.',
  'r5: native argument inspection read the closure trampoline. The source-authoritative closure-function unwrap supplies the actual native signature. Compiler unchanged.',
  'r6: snapshot scanner selected inherited subtags, excluding the replaced function tag. The fixture now explicitly admits the schema function tag and exactly six tagged words.',
  'r7/r8: 128 KiB reservation above 2 GiB exceeded the accepted 32769-page module maximum. The fixture now uses a 64 KiB owned region at that placement; compiler and loader unchanged.',
  'r10/r11: Python module-name collisions selected an older runner; imports and driver injection are now explicit.',
  'r12: a reversed-index mutant was caught at an earlier ordinal check than its proposed oracle. The final mutant instead reverses capture names with indices unchanged, reaching the actual-cell oracle.',
  'r13: shortened-self mutation anchor appeared twice; narrowed to metadata-entry. r14: expected compatibility membership included installed copies but enumeration did not. The final check includes every installed copy with no byte normalization.',
  'Original failed compiler inputs, generated modules, runtime files and logs are retained where produced. Successful intermediate runs are superseded; one final pack is published.'
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
