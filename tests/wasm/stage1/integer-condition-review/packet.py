"""Retain/replay generated integer calls, native R6, and exact runtime inputs."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from backend import generate,ROOT
HERE=Path(__file__).resolve().parent;BASE='2026-09-19-stage1-integer-conditions-r1'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1200)
def archive(p,rows):
 with tarfile.open(p,'w:gz') as t:
  for f,n in rows:t.add(f,arcname=n,recursive=False)
def pins(e):
 result=read(e/BASE/'source-pins.json');integration=read(ROOT/'doc/WASM/stage1/integration-integer-calls.json');changes={r['file']:r for r in integration['files']}
 for n,h in list(result.items()):
  actual=sha(ROOT/n)
  if actual!=h:assert n in changes and changes[n]['before']==h and changes[n]['after']==actual,n
  result[n]=actual
 for f in files(HERE):result[str(f.relative_to(ROOT))]=sha(f)
 for n in ['runtime/wasm32/integer.c','runtime/wasm32/integer-service.mjs','level-0/l0-numbers.lisp','level-0/l0-bignum32.lisp','level-1/l1-error-system.lisp','level-1/x86-trap-support.lisp','compiler/WASM32/wasm32-arch.lisp','runtime/wasm32/collector.c','runtime/wasm32/collector-owner.mjs','doc/WASM/stage1/integration-integer-core.json','doc/WASM/stage1/integration-integer-calls.json']:result[n]=sha(ROOT/n)
 return result
def selected(d):
 names={'summary.json','native.json','execution.json','controls.json','pools.json','native-metadata.json','native-behavior.json','native-order.json','native-flow.json','native-condition-classes.json','cases.json','modules.json','materialized.json'}
 return {str(f.relative_to(d)):sha(f) for f in files(d) if (f.suffix in ['.wat','.wasm','.dx64fsl'] or f.name in names or f.name in ['native-results.txt','source-refusals.txt','native-zero-traps.txt','native-policy-errors.txt','native-reader-errors.txt','mode-admission.txt'] or f.name.startswith('materialized-')) and not any(n in f.relative_to(d).parts for n in ['proposal','executed-sources'])}
def manifest(p):save(p/'packet.json',dict(id='STAGE1-INTEGER-CONDITIONS-R2',kind='AUXILIARY_INTEGER_CONDITION_REVIEW',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def qualify(e,native,out):
 assert (native/'proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()==generate()
 command([sys.executable,HERE.parent/'registration/qualify.py','--output',native,'--inputs',e/'macos-u1-inputs','--kernel',e/'2026-09-12-native-census-r7/baseline/build/dx86cl64','--destination',out],out.with_suffix('.log'))
def retain(e,x,native,p):
 assert not p.exists() and read(x/'summary.json')['status']=='PASS' and read(native/'run.json')['status']=='PASS';p.mkdir();source=pins(e);save(p/'source-pins.json',source)
 archive(p/'sources.tar.gz',[(ROOT/n,n) for n in source]);(p/'wasm32-backend.lisp').write_text(generate());assert (x/'compiled/proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()==generate()
 qualify(e,native,p/'qualification');archive(p/'execution.tar.gz',[(f,str(f.relative_to(x))) for f in files(x)]);save(p/'deterministic.json',selected(x))
 known={r['sha256']:str((e/'2026-09-16-stage1-1a-r2'/r['path']).relative_to(e)) for r in read(e/'2026-09-16-stage1-1a-r2/packet.json')['files']};refs=[];rows=[]
 for f in files(native):
  n=str(f.relative_to(native));h=sha(f)
  if h in known:refs.append(dict(path=n,sha256=h,evidence_path=known[h]))
  else:rows.append((f,n))
 archive(p/'native.tar.gz',rows);save(p/'native-references.json',refs)
 paths=[BASE+'/packet.json','2026-09-19-stage1-collector-qualification-r1/collector.wasm','2026-09-19-stage1-integer-core-r1/execution/integer.wasm','2026-09-19-stage1-integer-core-r1/packet.json']
 save(p/'inputs.json',{n:sha(e/n) for n in paths});shutil.copy(HERE/'service.mjs',p/'service.mjs');shutil.copy(HERE/'README.md',p/'README.md')
 save(p/'summary.json',dict(read(x/'summary.json'),native_R6=read(p/'qualification/summary.json')))
 tools=['/usr/local/bin/node','/usr/local/bin/wat2wasm'];save(p/'toolchain.json',[dict(path=str(Path(n).resolve()),sha256=sha(Path(n).resolve())) for n in tools])
 # The prior packet retains the development failures of the original unit.
 # Keep any new failed run here; successful exploratory runs need no duplicate.
 attempts=[]
 for base in sorted(Path('/tmp').glob('ccl-ncr-r[0-9]*')):
  if base.resolve()==x.resolve() or not (base/'failure.json').exists():continue
  attempts.append(base)
 archive(p/'development.tar.gz',[(f,base.name+'/'+str(f.relative_to(base))) for base in attempts for f in files(base)])
 save(p/'development.json',dict(prior=BASE+'/development.json',attempts=[read(base/'failure.json') for base in attempts]))
 assert source==pins(e);manifest(p)
def verify(e,p,out):
 out.mkdir(parents=True,exist_ok=False);source=pins(e);assert source==read(p/'source-pins.json')
 for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 for n,h in read(p/'inputs.json').items():assert sha(e/n)==h,n
 for t in read(p/'toolchain.json'):assert sha(Path(t['path']))==t['sha256']
 native=out/'native';native.mkdir()
 with tarfile.open(p/'native.tar.gz') as t:t.extractall(native,filter='data')
 for r in read(p/'native-references.json'):
  src=e/r['evidence_path'];assert sha(src)==r['sha256'];dst=native/r['path'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(src,dst)
 qualify(e,native,out/'qualification');command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution','--qualify'],out/'execution.log')
 actual=selected(out/'execution');expected=read(p/'deterministic.json');assert actual.keys()==expected.keys()
 for n,h in expected.items():assert actual[n]==h,n
 assert source==pins(e);result=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source),summary=read(out/'execution/summary.json'),native_R6=read(out/'qualification/summary.json'));save(out/'verification.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True)
 for n in ['execution','native','output']:a.add_argument('--'+n,type=Path)
 v=a.parse_args()
 if v.mode=='retain':retain(v.evidence.resolve(),v.execution.resolve(),v.native.resolve(),v.packet.resolve())
 else:verify(v.evidence.resolve(),v.packet.resolve(),v.output.resolve())
