"""One retained generated-materialization packet and byte-exact replay."""
import argparse,hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from backend import ROOT,HERE,generate
from run import sha,read,save,command
ID='STAGE1-MATERIALIZATION-R1'
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and not f.is_symlink())
def pins():
 paths=set(files(HERE))
 for folder in ['constants','registration','architecture']:paths.update(files(HERE.parent/folder))
 for n in ['compiler/wasm32/wasm32-backend.lisp','compiler/wasm32/wasm32-arch.lisp','runtime/wasm32/bytes.mjs','runtime/wasm32/sha256.mjs','runtime/wasm32/binary.mjs','runtime/wasm32/stub.wat','tests/wasm/stage1/callable-metadata/compile.lisp','tests/wasm/stage1/callable-metadata/execute.mjs','tests/wasm/native-census/observer.lisp','tests/wasm/native-baseline/tests.lisp','tests/wasm/stage0/engine-matrix/features.json','doc/WASM/contracts/wasm32-layout.v1.json','doc/WASM/contracts/tcr.v1.json','doc/WASM/contracts/tcr.v2.json','doc/WASM/tools/gate.py','doc/WASM/tools/evidence_binding.py']:
  paths.add(ROOT/n)
 return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
def retained(out):
 for f in files(out):
  parts=f.relative_to(out).parts
  if any(p.endswith('-driver') or p in ['proposal','source'] for p in parts):continue
  yield f
def deterministic(out):
 return {str(p.relative_to(out)):sha(p) for p in retained(out) if p.suffix in ['.json','.mjs','.wat','.wasm','.dx64fsl','.txt'] and p.name!='command.json' and not p.name.endswith('.command.json')}
def archive(p,rows):
 with tarfile.open(p,'w:gz') as t:
  for f,n in rows:t.add(f,arcname=n,recursive=False)
def manifest(p):save(p/'packet.json',dict(id=ID,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def qualify(e,native,out):
 assert (native/'proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()==generate()
 command([sys.executable,HERE.parent/'registration/qualify.py','--output',native,'--inputs',e/'macos-u1-inputs','--kernel',e/'2026-09-12-native-census-r7/baseline/build/dx86cl64','--destination',out],out.with_suffix('.log'))
def retain(e,out,native,p):
 assert not p.exists() and read(out/'summary.json')['status']=='PASS';p.mkdir()
 source=pins();save(p/'source-pins.json',source);archive(p/'sources.tar.gz',[(ROOT/n,n) for n in source])
 assert (out/'templates/proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()==generate()
 (p/'wasm32-backend.lisp').write_text(generate())
 for f in retained(out):
  dst=p/'execution'/f.relative_to(out);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,dst)
 save(p/'deterministic.json',deterministic(out))
 for n in ['summary.json','controls.json','assessment.json','publication-controls.json','materializer.mjs']:shutil.copy(out/n,p/n)
 for n in ['README.md','scope.json','coverage.json','development.json']:shutil.copy(HERE/n,p/n)
 for n in ['abi-decision.json','abi-binding.json','options.json']:shutil.copy(e/'2026-09-19-stage1-control-r1'/n,p/n)
 save(p/'options.json',dict(profiles=['full','precompiled_callback'],template_memory=True,callable_metadata=True,minimum_pages=1,maximum_pages=32769,placements=[1048576,2097152,2147483648],jspi='DEFERRED',instruction_classifier='pinned wasm-objdump',seed='DETERMINISTIC_NO_RANDOM_INPUT'))
 qualify(e,native,p/'qualification')
 known={r['sha256']:str((e/'2026-09-16-stage1-1a-r2'/r['path']).relative_to(e)) for r in read(e/'2026-09-16-stage1-1a-r2/packet.json')['files']};refs=[];rows=[]
 for f in files(native):
  h=sha(f);n=str(f.relative_to(native))
  if h in known:refs.append(dict(path=n,sha256=h,evidence_path=known[h]))
  else:rows.append((f,n))
 archive(p/'native.tar.gz',rows);save(p/'native-references.json',refs)
 names=['macos-u1-inputs/'+n for n in ['pins.json','source.tar','bootstrap.tar.gz','tests.tar']]+['2026-09-12-native-census-r7/baseline/build/dx86cl64','2026-09-16-stage1-1a-r2/native/baseline.image']
 names+=['2026-09-15-engine-matrix-r2/'+n for n in ['packet.json','environment.json','matrix.json']]
 names+=['2026-09-16-six-slot-project-acceptance/ENGINE-MATRIX-R2/accepted/accepted-results.json']
 save(p/'inputs.json',{n:sha(e/n) for n in names})
 tools=[]
 for n in ['/usr/local/bin/node','/usr/local/bin/wat2wasm','/usr/local/bin/wasm-objdump']:
  f=Path(n).resolve();tools.append(dict(path=str(f),sha256=sha(f),version=subprocess.check_output([str(f),'--version'],text=True).strip()))
 save(p/'toolchain.json',dict(tools=tools))
 failures=[]
 for r in read(HERE/'development.json')['attempts']:
  for n in r.get('retained',[]):failures.append((Path('/tmp')/n,n))
 archive(p/'development.tar.gz',failures)
 assert source==pins();manifest(p)
def verify(e,p,out):
 out.mkdir(parents=True,exist_ok=False);source=pins();assert source==read(p/'source-pins.json'),'source pins'
 for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 for n,h in read(p/'inputs.json').items():assert sha(e/n)==h,n
 for r in read(p/'toolchain.json')['tools']:assert sha(Path(r['path']))==r['sha256'],r['path']
 native=out/'native';native.mkdir()
 with tarfile.open(p/'native.tar.gz') as t:t.extractall(native,filter='data')
 for r in read(p/'native-references.json'):
  f=e/r['evidence_path'];assert sha(f)==r['sha256'];dst=native/r['path'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,dst)
 qualify(e,native,out/'qualification')
 assert read(out/'qualification/summary.json')==read(p/'qualification/summary.json')
 command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'],out/'replay.log')
 expected=read(p/'deterministic.json');actual=deterministic(out/'execution');assert expected.keys()==actual.keys(),(expected.keys()-actual.keys(),actual.keys()-expected.keys())
 for n,h in expected.items():assert actual[n]==h,n
 if (p/'role-controls.json').exists():
  from publish import role_controls
  assert role_controls(e,read(p/'inventory.json'),read(e/(p.name+'-results.json')),sha(p/'inventory.json'))==read(p/'role-controls.json')
 assert source==pins()
 result=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source),summary=read(out/'execution/summary.json'),native_R6=read(out/'qualification/summary.json'))
 save(out/'verification.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True)
 for n in ['execution','native','output']:a.add_argument('--'+n,type=Path)
 v=a.parse_args()
 if v.mode=='retain':retain(v.evidence.resolve(),v.execution.resolve(),v.native.resolve(),v.packet.resolve())
 else:verify(v.evidence.resolve(),v.packet.resolve(),v.output.resolve())
