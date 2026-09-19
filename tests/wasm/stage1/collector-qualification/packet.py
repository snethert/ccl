"""Retain and reproduce the LL18 generated execution and owner qualification."""
import argparse,hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from runtime import ROOT,collector,owner
from assessment import run as assessment
HERE=Path(__file__).resolve().parent;PARENT='2026-09-19-stage1-constructor-retry-r1'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(ok,why):
 if not ok:raise ValueError(why)
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and not f.is_symlink())
def archive(p,rows):
 with tarfile.open(p,'w:gz') as t:
  for f,n in rows:t.add(f,arcname=n,recursive=False)
def pins(e):
 result=read(e/PARENT/'source-pins.json');integration=read(ROOT/'doc/WASM/stage1/integration-constructor-retry.json')
 changed={r['file']:r for r in integration['files']}
 for n,h in list(result.items()):
  actual=sha(ROOT/n)
  if actual!=h:need(n in changed and changed[n]['before']==h and changed[n]['after']==actual,'reviewed integration '+n)
  result[n]=actual
 for d in [HERE,HERE.parent/'constants']:
  for f in files(d):
   if 'review-followup' not in f.parts:result[str(f.relative_to(ROOT))]=sha(f)
 for n in ['compiler/WASM32/wasm32-backend.lisp','runtime/wasm32/collector.c','runtime/wasm32/collector-owner.mjs','runtime/wasm32/allocation-service.mjs','runtime/wasm32/stub.wat','doc/WASM/contracts/wasm32-layout.v1.json','doc/WASM/stage1/integration-constructor-retry.json','doc/WASM/tools/evidence_binding.py','doc/WASM/tools/gate.py']:
  result[n]=sha(ROOT/n)
 return dict(sorted(result.items()))
def manifest(p):save(p/'packet.json',dict(id='STAGE1-COLLECTOR-QUALIFICATION-R1',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def selected(d):
 names={'summary.json','native.json','execution.json','controls.json','cases.json','core.json','owner.json','literals.json','roots.json','generated.json','lazy.json','assessment.json','expected.json','root-contracts.json','root-ir.json','materialized-low.json','materialized-high.json','materialized-pinned.json'}
 return {str(f.relative_to(d)):sha(f) for f in files(d) if (f.suffix in ('.wat','.wasm','.dx64fsl') or f.name in names) and not any(x in f.relative_to(d).parts for x in ('executed-sources','proposal','constant-driver'))}
def qualification(e,p):
 parent=e/PARENT;expected=read(parent/'packet.json')['files'];hashes={r['path']:r['sha256'] for r in expected}
 need(sha(parent/'wasm32-backend.lisp')==sha(ROOT/'compiler/WASM32/wasm32-backend.lisp'),'unchanged reviewed compiler')
 names=['packet.json','wasm32-backend.lisp','source-pins.json','native.tar.gz','native-references.json','qualification/summary.json','qualification/verification.json','toolchain.json']
 refs=[]
 for n in names:
  h=sha(parent/n)
  if n!='packet.json':need(h==hashes[n],'parent binding '+n)
  refs.append(dict(locator=PARENT+'/'+n,sha256=h))
 need(read(parent/'qualification/summary.json')['status']=='PASS','reviewed native R6')
 save(p/'native-reuse.json',dict(status='PASS',compiler_sha256=sha(parent/'wasm32-backend.lisp'),review_commit='3cdfc906',integration='doc/WASM/stage1/integration-constructor-retry.json',qualification=read(parent/'qualification/summary.json'),references=refs,scope='Exact reviewed compiler, no compiler change; reuse R6/R6a. New C collector and JavaScript owner are freestanding proposals. Native oracle compilation is re-executed.'))
def retain(e,x,p):
 need(not p.exists(),'never overwrite packet');need(read(x/'summary.json')['status']=='PASS','execution')
 p.mkdir();source=pins(e);save(p/'source-pins.json',source);archive(p/'source.tar.gz',[(ROOT/n,n) for n in source]);qualification(e,p)
 for n in ['collector.c','collector.wasm','collector-owner.mjs']:shutil.copy(x/n,p/n)
 need((p/'collector.c').read_text()==collector() and (p/'collector-owner.mjs').read_text()==owner(),'proposal derivation')
 shutil.copy(ROOT/'compiler/WASM32/wasm32-backend.lisp',p/'wasm32-backend.lisp')
 archive(p/'execution.tar.gz',[(f,str(f.relative_to(x))) for f in files(x)]);save(p/'deterministic.json',selected(x))
 shutil.copytree(x/'assessment',p/'assessment')
 for n in ['scope.json','coverage.json']:shutil.copy(HERE/n,p/n)
 for n in ['options.json','abi-decision.json','abi-binding.json']:shutil.copy(e/'2026-09-19-stage1-control-r1'/n,p/n)
 shutil.copy(e/PARENT/'toolchain.json',p/'toolchain.json')
 options=read(p/'options.json');options.update(profile='wasm32-shared-B-owner-retry-v1',collector='copying',egc=False,heap_configurations=7,maximum_pages=32769,native_R6='reused exact reviewed compiler');save(p/'options.json',options)
 pos=p/'positive';pos.mkdir();(pos/'installed').mkdir()
 for name in ['pair','many_values','make_reader']:
  for ext in ['wat','wasm']:shutil.copy(x/'generated'/(name+'.'+ext),pos/(name+'.'+ext))
  shutil.copy(x/'generated'/(name+'.wasm'),pos/'installed'/(name+'.wasm'))
 fasls=list((x/'generated').rglob('*.dx64fsl'));need(fasls,'compiled backend');shutil.copy(fasls[0],pos/'wasm32-backend.dx64fsl')
 summary=dict(read(x/'assessment/assessment.json'),test='S1-LL18-a',review_disposition='NOT_REVIEWED',retry_collections=read(x/'generated.json')['collections'],retry_growths=read(x/'generated.json')['growths'],poll_collections=len(read(x/'polls/execution.json')['moved_vectors']),literal_collections=sum(r['collections'] for r in read(x/'literals.json')['rows']),scope=read(HERE/'scope.json'),native_reuse=read(p/'native-reuse.json')['qualification'])
 save(p/'summary.json',summary)
 dev=[]
 for name in ['ccl-ll18-r1','ccl-ll18-controls-failure1','ccl-ll18-controls-failure2']:
  for f in files(Path('/tmp')/name):
   if not any(s in f.parts for s in ('executed-sources','proposal','constant-driver')):dev.append((f,name+'/'+str(f.relative_to(Path('/tmp')/name))))
  f=Path('/tmp')/(name+'.log')
  if f.exists():dev.append((f,name+'/driver.log'))
 for n in ['ll18-explore-controls.py','ccl-ll18-controls-explore.log','ccl-ll18-r5.log','ccl-ll18-r5/failed-assessment.py']:
  f=Path('/tmp')/n
  if f.exists():dev.append((f,n))
 # Exploration kept exact mutant sources and first diagnostics, not a new result.
 for f in files(Path('/tmp/ccl-ll18-r4/controls')):dev.append((f,'control-exploration/'+str(f.relative_to('/tmp/ccl-ll18-r4/controls'))))
 archive(p/'development.tar.gz',dev)
 save(p/'development.json',dict(notes=['First literal fixture omitted imported symbol globals; execution refused before collection. Harness corrected; original sources, binaries and log retained.','Initial mutant oracle predictions were too early: bit rounding loses the last bit of bits_33 on movement, byte width refuses a root rather than the inventory, and treating u32 data as roots corrupts raw_tag_words. Exploration retained; final controls require the observed literal diagnostics.','The first publication assessor confused a normal case called failure_live with the additional refusal case, then assumed core test labels were unique. It now separates the explicit resource row by its schema and preserves the reviewed raw-width duplicate labels. Its original source and driver failure are retained.', 'Successful intermediate runs were superseded by explicit poll, pinned image, partial-byte bit-vector and cold-loader coverage. No compiler or shared runtime edited by this proposal.']))
 need(source==pins(e),'sources changed');manifest(p)
def verify(e,p,out):
 out.mkdir(parents=True,exist_ok=False);source=pins(e);need(source==read(p/'source-pins.json'),'source pins')
 for r in read(p/'packet.json')['files']:need(sha(p/r['path'])==r['sha256'],'packet '+r['path'])
 for r in read(p/'native-reuse.json')['references']:need(sha(e/r['locator'])==r['sha256'],'native reuse '+r['locator'])
 need(sha(p/'wasm32-backend.lisp')==sha(ROOT/'compiler/WASM32/wasm32-backend.lisp'),'compiler')
 for r in read(p/'toolchain.json')['tools']:need(sha(Path(r['path']))==r['sha256'],'tool '+r['path'])
 from run import command
 command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution','--controls'],out/'execution.log')
 actual=selected(out/'execution');expected=read(p/'deterministic.json');need(actual.keys()==expected.keys(),'replay file membership')
 for n,h in expected.items():need(actual[n]==h,'replay '+n)
 for n in ['collector.c','collector.wasm','collector-owner.mjs']:need(sha(p/n)==sha(out/'execution'/n),'proposal '+n)
 for n in ['assessment.json','controls.json']:need(sha(p/'assessment'/n)==sha(out/'execution/assessment'/n),'assessment '+n)
 if (p/'role-controls.json').exists():
  from publish import role_controls
  need(role_controls(e,read(p/'inventory.json'),read(e/(p.name+'-results.json')),sha(p/'inventory.json'))==read(p/'role-controls.json'),'role replay')
 need(source==pins(e),'source stability');result=dict(status='PASS',source_pins=len(source),deterministic_files=len(actual),native_R6='REUSED_EXACT_REVIEWED_COMPILER');save(out/'verification.json',result);print(result)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True)
 for n in ['execution','output']:a.add_argument('--'+n,type=Path)
 v=a.parse_args()
 if v.mode=='retain':retain(v.evidence.resolve(),v.execution.resolve(),v.packet.resolve())
 else:verify(v.evidence.resolve(),v.packet.resolve(),v.output.resolve())
