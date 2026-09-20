"""Retain and replay the joined LL16 qualification, including fresh timing."""
import argparse,json,shutil,sys,tarfile,subprocess
from pathlib import Path
from run import ROOT,HERE,read,save,sha,command
PARENT='2026-09-20-stage1-float-calls-r2';R1='2026-09-19-stage1-float-calls-r1'
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and not f.is_symlink())
def archive(p,rows):
 with tarfile.open(p,'w:gz') as t:
  for f,n in rows:t.add(f,arcname=n,recursive=False)
def pins(e):
 old=read(e/PARENT/'source-pins.json');integration=read(ROOT/'doc/WASM/stage1/integration-float-calls.json');changes={r['file']:r for r in integration['files']};result={}
 for n,h in old.items():
  actual=sha(ROOT/n)
  if actual!=h:assert n in changes and changes[n]['before']==h and changes[n]['after']==actual,('unreviewed drift',n)
  result[n]=actual
 for f in [*files(HERE),*files(ROOT/'runtime/wasm32'),ROOT/'doc/WASM/stage1/integration-float-calls.json',ROOT/'doc/WASM/contracts/floating-point.v1.md',ROOT/'doc/WASM/stage0/benchmarks.json',ROOT/'tests/wasm/stage1/integer-core/review-followup/run.py',ROOT/'tests/wasm/stage1/integer-core/corpus.py',ROOT/'tests/wasm/stage1/integer-core/run.py']:
  result[str(f.relative_to(ROOT))]=sha(f)
 return dict(sorted(result.items()))
def manifest(p):save(p/'packet.json',dict(id='STAGE1-NUMERIC-QUALIFICATION-R1',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def retained(x):
 # Do not duplicate copied driver baselines or the positive modules reused by
 # the poisoned-dispatch run. Its replay and commands identify those inputs.
 for f in files(x):
  rel=f.relative_to(x)
  if any(n in rel.parts for n in ['driver','proposal','source']):continue
  if rel.parts[:2]==('poison','generated') and f.name not in ['execute.mjs','poison.json','poison.log','poison.command.json']:continue
  yield f

def selected(x):
 result={}
 for f in retained(x):
  n=f.relative_to(x)
  if 'benchmark' in n.parts or f.name in ['summary.json','command.json'] or f.name.endswith('.command.json'):continue
  if f.suffix in ['.json','.wasm','.wat','.c','.mjs','.dx64fsl'] or f.name in ['native-results.txt','native-args.txt','source-refusals.txt']:result[str(n)]=sha(f)
 return result

def retain(e,x,p):
 assert not p.exists() and read(x/'summary.json')['status']=='PASS';p.mkdir()
 source=pins(e);save(p/'source-pins.json',source);base=read(e/PARENT/'source-pins.json')
 archive(p/'source-additions.tar.gz',[(ROOT/n,n) for n,h in source.items() if base.get(n)!=h])
 save(p/'source-base.json',dict(packet=PARENT+'/packet.json',sha256=sha(e/PARENT/'packet.json'),rule='Use the R2 source-base chain plus these replacement/additional source paths.'))
 archive(p/'execution.tar.gz',[(f,str(f.relative_to(x))) for f in retained(x)]);save(p/'deterministic.json',selected(x))
 for n in ['summary.json','assessment.json','controls.json','dispatch.json','fallback-execution.json']:shutil.copy(x/n,p/n)
 for n in ['scope.json','coverage.json']:shutil.copy(HERE/n,p/n)
 for n in ['abi-decision.json','abi-binding.json','options.json']:shutil.copy(e/'2026-09-19-stage1-control-r1'/n,p/n)
 refs=read(e/PARENT/'inputs.json')|{PARENT+'/packet.json':sha(e/PARENT/'packet.json'),R1+'/qualification/summary.json':sha(e/R1/'qualification/summary.json'),R1+'/qualification/verification.json':sha(e/R1/'qualification/verification.json')}
 for n in ['2026-09-19-stage1-integer-core-r1/packet.json','2026-09-19-stage1-integer-review-r1/packet.json']:
  assert (e/n).is_file();refs[n]=sha(e/n)
 save(p/'inputs.json',refs)
 options=read(p/'options.json');options.update(profile='wasm32-shared-B-floating-owner-v1',integer_capacity_digits=1024,floating_widths=[32,64],native_policies=[[0,3],[3,0],[3,3]],generated_checking=[0,1],benchmark_seed=161613);save(p/'options.json',options)
 assert sha(ROOT/'compiler/WASM32/wasm32-backend.lisp')==sha(e/R1/'wasm32-backend.lisp')
 q=read(e/R1/'qualification/summary.json');assert q['status']=='PASS'
 save(p/'native-reuse.json',dict(status='PASS',compiler_sha256=sha(e/R1/'wasm32-backend.lisp'),review_commit='842a2481f08a9fa32b5ceda991658ba0383cc64e',integration='doc/WASM/stage1/integration-float-calls.json',qualification=q,scope='Compiler byte-identical to the reviewed generated-floating compiler; R6/R6a and compiler controls reused. All native arithmetic observations and generated modules are rebuilt here.'))
 shutil.copy(ROOT/'compiler/WASM32/wasm32-backend.lisp',p/'wasm32-backend.lisp')
 tool=dict(tools=[dict(path=str(Path(n).resolve()),sha256=sha(Path(n).resolve()),version=subprocess.check_output([n,'--version'],text=True).strip()) for n in ['/usr/local/bin/node','/usr/local/bin/wat2wasm','/usr/local/bin/wasm2wat','/usr/local/opt/llvm/bin/clang']]);save(p/'toolchain.json',tool)
 pos=p/'positive';pos.mkdir();(pos/'installed').mkdir()
 for name in ['q1_add','q1_sub','q1_mul','q1_ash','q1_length','q1_truncate','f_add','h_single','bench_add','bench_add__unchecked']:
  for ext in ['wat','wasm']:shutil.copy(x/'generated/compiled'/(name+'.'+ext),pos/(name+'.'+ext))
  shutil.copy(x/'generated/compiled'/(name+'.wasm'),pos/'installed'/(name+'.wasm'))
 shutil.copy(x/'generated/compiled/compiler.dx64fsl',pos/'compiler.dx64fsl')
 # Development snapshots contain the harness error, its source revision and
 # first diagnostic; successful prerequisite compiles are not copied again.
 dev=HERE/'development.json';description=read(dev);rows=[]
 for r in description['attempts']:
  for n in r['retained']:
   f=Path('/tmp')/n
   assert f.is_file(),f;rows.append((f,n))
 archive(p/'development.tar.gz',rows);shutil.copy(dev,p/'development.json')
 assert source==pins(e);manifest(p)

def verify(e,p,out):
 out.mkdir(parents=True,exist_ok=False);source=pins(e);assert source==read(p/'source-pins.json')
 for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 for n,h in read(p/'inputs.json').items():assert sha(e/n)==h,n
 for t in read(p/'toolchain.json')['tools']:assert sha(Path(t['path']))==t['sha256']
 command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'],out/'replay.log')
 got=selected(out/'execution');expected=read(p/'deterministic.json');assert got.keys()==expected.keys(),(got.keys()-expected.keys(),expected.keys()-got.keys())
 for n,h in expected.items():assert got[n]==h,n
 if (p/'role-controls.json').is_file():
  from publish import role_controls
  assert role_controls(e,read(p/'inventory.json'),read(e/(p.name+'-results.json')),sha(p/'inventory.json'))==read(p/'role-controls.json')
 assert source==pins(e)
 v=dict(status='PASS',deterministic_files=len(got),source_pins=len(source),native_R6='REUSED_BY_EXACT_COMPILER_HASH',qualification=read(out/'execution/assessment.json'),benchmark='FRESH_MEASUREMENTS_NOT_BYTE_EQUALITY');save(out/'verification.json',v);print(json.dumps(v,indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True);a.add_argument('--execution',type=Path);a.add_argument('--output',type=Path);v=a.parse_args()
 if v.mode=='retain':retain(v.evidence.resolve(),v.execution.resolve(),v.packet.resolve())
 else:verify(v.evidence.resolve(),v.packet.resolve(),v.output.resolve())
