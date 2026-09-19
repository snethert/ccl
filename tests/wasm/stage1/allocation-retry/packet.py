"""Retain exact retry proposal, native qualification, executable replay and failures."""
import argparse,hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from backend import generate
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];PARENT='2026-09-19-stage1-collector-owner-r1'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and not f.is_symlink())
def archive(p,rows):
 with tarfile.open(p,'w:gz') as t:
  for f,n in rows:t.add(f,arcname=n,recursive=False)
def command(argv,log):
 save(log.with_suffix('.command.json'),list(map(str,argv)))
 with log.open('w') as f:subprocess.run(list(map(str,argv)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
def pins(e):
 result=read(e/PARENT/'source-pins.json')
 for n,h in result.items():assert sha(ROOT/n)==h,n
 for f in files(HERE):result[str(f.relative_to(ROOT))]=sha(f)
 for n in ['runtime/wasm32/collector-owner.mjs','runtime/wasm32/collector.c','runtime/wasm32/binary.mjs']:result[n]=sha(ROOT/n)
 return dict(sorted(result.items()))
def qualify(e,native,out):
 assert (native/'proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()==generate()
 command([sys.executable,HERE.parent/'registration/qualify.py','--output',native,'--inputs',e/'macos-u1-inputs','--kernel',e/'2026-09-12-native-census-r7/baseline/build/dx86cl64','--destination',out],out.with_suffix('.log'))
def manifest(p):save(p/'packet.json',dict(id='STAGE1-ALLOCATION-RETRY-R1',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def selected(d):
 return {str(f.relative_to(d)):sha(f) for f in files(d) if (f.suffix in ('.wat','.wasm','.dx64fsl') or f.name in ('summary.json','native.json','execution.json','controls.json','cases.json','compatibility.json','root-contracts.json','root-ir.json')) and not any(x in f.relative_to(d).parts for x in ('executed-sources','proposal'))}
def retain(e,execution,native,p):
 assert not p.exists();assert read(execution/'summary.json')['compiler_mutants']==6;assert read(native/'run.json')['status']=='PASS'
 for f in [execution/'harness/wasm32-backend.lisp',native/'proposal/files/compiler/WASM32/wasm32-backend.lisp']:assert f.read_text()==generate()
 p.mkdir();source=pins(e);save(p/'source-pins.json',source);archive(p/'source.tar.gz',[(ROOT/n,n) for n in source]);(p/'wasm32-backend.lisp').write_text(generate())
 archive(p/'execution.tar.gz',[(f,str(f.relative_to(execution))) for f in files(execution)]);save(p/'deterministic.json',selected(execution))
 base=e/'2026-09-16-stage1-1a-r2';known={r['sha256']:str((base/r['path']).relative_to(e)) for r in read(base/'packet.json')['files']};refs=[];rows=[]
 for f in files(native):
  h=sha(f);n=str(f.relative_to(native))
  if h in known:refs.append(dict(path=n,sha256=h,evidence_path=known[h]))
  else:rows.append((f,n))
 archive(p/'native.tar.gz',rows);save(p/'native-references.json',refs);qualify(e,native,p/'qualification')
 shutil.copy(e/PARENT/'toolchain.json',p/'toolchain.json')
 save(p/'inputs.json',dict(references=[dict(locator=n,sha256=sha(e/n)) for n in [PARENT+'/packet.json','2026-09-19-stage1-collector-live-r1/packet.json','2026-09-19-stage1-collector-live-r1/collector.c','2026-09-19-stage1-collector-live-r1/collector.wasm']],scope='Auxiliary opt-in emitter and synchronous owner service; current lazy loader refuses new capability. No LL06/LL18 credit.'))
 summary=read(execution/'summary.json');summary.pop('rows');save(p/'summary.json',dict(summary,inventory_credit=False,review_disposition='NOT_REVIEWED',native=read(p/'qualification/summary.json')))
 rows=[]
 attempts=['ccl-retry-r1','ccl-retry-r2','ccl-retry-controls-r1','ccl-retry-controls-r2','ccl-retry-controls-r3']
 for d in sorted(Path('/tmp').glob('ccl-retry-r*')):
  if d.is_dir() and not (d/'summary.json').exists() and d.name not in attempts:attempts.append(d.name)
 for name in attempts:
  d=Path('/tmp')/name
  for f in files(d):
   if not any(x in f.relative_to(d).parts for x in ('executed-sources','proposal')):rows.append((f,name+'/'+str(f.relative_to(d))))
  log=Path('/tmp')/(name+'.log')
  if log.exists():rows.append((log,name+'/driver.log'))
 for n in ['run.json','proposal/files/compiler/WASM32/wasm32-backend.lisp']:
  f=Path('/tmp/ccl-retry-native-r1')/n
  if f.exists():rows.append((f,'superseded-native-r1/'+n))
 archive(p/'development.tar.gz',rows)
 save(p/'development.json',dict(attempts=attempts,notes=[
  'r1: inherited runner required the backend base export; stopped before native compilation. r2: fixture named a helper REST and pristine CCL correctly refused redefining the predefined function. r1 retains original input scripts and a contemporaneous failure note; its terminal traceback was not redirected. r2 retains its original compile log and inputs.',
  'Controls r1: early-cell-address mutant escaped the initial captured case; a large initializer now forces collection inside the exact address/store window. Controls r2: directly called lambda was inlined, so cached closure environment was unexercised. It now escapes from another generated module before being called.',
  'Controls r3: the stale environment is rejected by an engine bounds trap, not the initially expected checked refusal. The oracle now requires that exact trap on the focused case. Any combined attempt with the earlier oracle is retained too.',
  'Native r1 succeeded but predates moving helper calls off the fast path. Only final native r2 qualifies the proposal. Its initial record and proposal are kept, not relabelled.',
  'Successful intermediate corpus runs were superseded as heap placements and controls expanded. Default-mode compatibility is measured against the accepted compiler on the final source corpus. No inherited whole-suite rerun is claimed.'
 ]))
 assert source==pins(e);manifest(p)
def verify(e,p,out):
 assert not out.exists();out.mkdir();source=pins(e);assert source==read(p/'source-pins.json')
 for row in read(p/'packet.json')['files']:assert sha(p/row['path'])==row['sha256'],row['path']
 for row in read(p/'inputs.json')['references']:assert sha(e/row['locator'])==row['sha256'],row['locator']
 for row in read(p/'toolchain.json')['tools']:assert sha(Path(row['path']))==row['sha256'],row['path']
 assert (p/'wasm32-backend.lisp').read_text()==generate()
 native=out/'native';native.mkdir()
 with tarfile.open(p/'native.tar.gz') as t:t.extractall(native,filter='data')
 for row in read(p/'native-references.json'):
  src=e/row['evidence_path'];assert sha(src)==row['sha256'];dest=native/row['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(src,dest)
 qualify(e,native,out/'qualification')
 command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution','--qualify'],out/'execution.log')
 actual=selected(out/'execution');expected=read(p/'deterministic.json');assert actual.keys()==expected.keys()
 for n,h in expected.items():assert actual[n]==h,n
 assert source==pins(e);result=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source));save(out/'verification.json',result);print(result)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True)
 for n in ['execution','native','output']:a.add_argument('--'+n,type=Path)
 v=a.parse_args();e=v.evidence.resolve();p=v.packet.resolve()
 if v.mode=='retain':retain(e,v.execution.resolve(),v.native.resolve(),p)
 else:verify(e,p,v.output.resolve())
