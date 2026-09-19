"""Scoped retention and replay; unchanged native qualification is referenced."""
import argparse,hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
PARENT='2026-09-19-stage1-collector-live-r1'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
def archive(p,rows):
 with tarfile.open(p,'w:gz') as t:
  for f,n in rows:t.add(f,arcname=n,recursive=False)
def pins(e):
 result=read(e/PARENT/'source-pins.json')
 for n,h in result.items():assert sha(ROOT/n)==h,n
 for p in files(HERE):result[str(p.relative_to(ROOT))]=sha(p)
 result['doc/WASM/contracts/tcr.v2.json']=sha(ROOT/'doc/WASM/contracts/tcr.v2.json')
 return dict(sorted(result.items()))
def deterministic(p):
 return p.suffix in ('.wat','.wasm','.dx64fsl') or p.name in ('owner.mjs','check.mjs','summary.json','native.json','execution.json','controls.json','cases.json','owner.json','schema-roots.json')
def manifest(p):save(p/'packet.json',dict(id='STAGE1-COLLECTOR-OWNER-R1',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def retain(e,execution,p):
 assert not p.exists();assert read(execution/'summary.json')['status']=='PASS'
 parent=e/PARENT
 for n in ('wasm32-backend.lisp','collector.c','collector.wasm'):assert sha(execution/'harness'/n)==sha(parent/n),n
 p.mkdir();source=pins(e);save(p/'source-pins.json',source);archive(p/'source.tar.gz',[(ROOT/n,n) for n in source])
 archive(p/'execution.tar.gz',[(f,str(f.relative_to(execution))) for f in files(execution)])
 selected={str(f.relative_to(execution)):sha(f) for f in files(execution) if deterministic(f) and not any(x in f.relative_to(execution).parts for x in ('executed-sources','proposal'))}
 assert len(selected)>20;save(p/'deterministic.json',selected)
 refs=['packet.json','wasm32-backend.lisp','collector.c','collector.wasm','qualification/summary.json','toolchain.json']
 save(p/'inputs.json',dict(parent=PARENT,references=[dict(locator=PARENT+'/'+n,sha256=sha(parent/n)) for n in refs],native_qualification='REUSED_UNCHANGED_BYTES',integration_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()))
 shutil.copy(parent/'toolchain.json',p/'toolchain.json')
 save(p/'summary.json',dict(read(execution/'summary.json'),inventory_credit=False,review_disposition='NOT_REVIEWED',native_qualification=read(parent/'qualification/summary.json'),generated_owner_comparisons=25))
 rows=[]
 for name in ('ccl-owner-r3','ccl-owner-r4'):
  d=Path('/tmp')/name
  for f in files(d):
   if not any(x in f.relative_to(d).parts for x in ('executed-sources','proposal')):rows.append((f,name+'/'+str(f.relative_to(d))))
 f=Path('/tmp/integrate-collector-live-import-failure.py')
 if f.exists():rows.append((f,'integration-preparation/'+f.name))
 archive(p/'development.tar.gz',rows)
 save(p/'development.json',dict(notes=[
  'r3: owner composition used an eight-byte-misaligned public result area; accepted generated entry refused. Exact test, owner, generated compiler/modules/native oracle and log retained. Result reservation is now 16-byte aligned.',
  'r4: owner test reused a memory already grown to its maximum before testing a new growth. It reused r3 generated modules; exact test and owner plus log retained. The generated composition now starts in a fresh memory.',
  'r1/r2/r5/r6 were successful development checkpoints superseded as generated composition, rejection controls and schema bindings were added. No old result is relabelled.',
  'Integration preparation initially imported the wrong run module after a generator changed sys.path. It failed before mutations; original preparation script retained. Integration itself was subsequently committed as d30abc47.',
  'No compiler or collector algorithm changed. Native R6/R6a and prior moving/control evidence are reused by pinned source/module identity, not represented as a new native build.'
 ]))
 assert source==pins(e);manifest(p)
def verify(e,p,out):
 assert not out.exists();out.mkdir();source=pins(e);assert source==read(p/'source-pins.json')
 for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 for r in read(p/'inputs.json')['references']:assert sha(e/r['locator'])==r['sha256'],r['locator']
 for r in read(p/'toolchain.json')['tools']:assert sha(Path(r['path']))==r['sha256'],r['path']
 argv=[sys.executable,str(HERE/'run.py'),'--evidence',str(e),'--output',str(out/'execution')]
 save(out/'command.json',argv)
 with (out/'execution.log').open('w') as log:subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
 fresh={str(f.relative_to(out/'execution')):sha(f) for f in files(out/'execution') if deterministic(f) and not any(x in f.relative_to(out/'execution').parts for x in ('executed-sources','proposal'))}
 expected=read(p/'deterministic.json');assert fresh.keys()==expected.keys(),(fresh.keys()-expected.keys(),expected.keys()-fresh.keys())
 for n,h in expected.items():assert fresh[n]==h,n
 assert source==pins(e);result=dict(status='PASS',deterministic_files=len(fresh),source_pins=len(source));save(out/'verification.json',result);print(result)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True);a.add_argument('--execution',type=Path);a.add_argument('--output',type=Path);v=a.parse_args()
 if v.mode=='retain':retain(v.evidence.resolve(),v.execution.resolve(),v.packet.resolve())
 else:verify(v.evidence.resolve(),v.packet.resolve(),v.output.resolve())
