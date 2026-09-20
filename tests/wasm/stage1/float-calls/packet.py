import argparse,hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from backend import HERE,ROOT,generate
BASE='2026-09-19-stage1-integer-owner-r1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
def archive(p,rows):
 with tarfile.open(p,'w:gz') as t:
  for f,n in rows:t.add(f,arcname=n,recursive=False)
def pins(e):
 result=read(e/BASE/'source-pins.json');changes={x['file']:x for x in read(ROOT/'doc/WASM/stage1/integration-integer-owner.json')['files']}
 for n,h in list(result.items()):
  actual=sha(ROOT/n)
  if h!=actual:assert n in changes and changes[n]['before']==h and changes[n]['after']==actual,(n,h,actual)
  result[n]=actual
 for n in read(e/'2026-09-19-stage1-float-owner-r1/source-pins.json'):result[n]=sha(ROOT/n)
 for f in files(HERE):result[str(f.relative_to(ROOT))]=sha(f)
 for n in ['tests/wasm/stage1/float-core/corpus.py','tests/wasm/stage0/float-detection/ieee.py','runtime/wasm32/float-service.mjs','doc/WASM/stage1/integration-float-owner.json','level-0/l0-float.lisp','level-0/l0-numbers.lisp']:result[n]=sha(ROOT/n)
 return result
def selected(p):
 return {str(f.relative_to(p)):sha(f) for f in files(p) if not any(n in f.relative_to(p).parts for n in ['driver','source','proposal']) and not f.name.endswith('.command.json') and f.name!='command.json' and (f.suffix in ['.mjs','.wat','.wasm','.dx64fsl','.json'] or f.name in ['native-results.txt','native-args.txt','source-refusals.txt'])}
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1800)
def qualify(e,native,out):
 assert (native/'proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()==generate()
 command([sys.executable,HERE.parent/'registration/qualify.py','--output',native,'--inputs',e/'macos-u1-inputs','--kernel',e/'2026-09-12-native-census-r7/baseline/build/dx86cl64','--destination',out],out.with_suffix('.log'))
def manifest(p):save(p/'packet.json',dict(id='STAGE1-FLOAT-CALLS-R1',kind='AUXILIARY_GENERATED_FLOATING_CALLS',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def retain(e,x,native,p):
 assert not p.exists() and read(x/'summary.json')['status']=='PASS';p.mkdir();source=pins(e);save(p/'source-pins.json',source);archive(p/'sources.tar.gz',[(ROOT/n,n) for n in source]);(p/'wasm32-backend.lisp').write_text(generate());assert (x/'compiled/proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()==generate()
 qualify(e,native,p/'qualification');archive(p/'execution.tar.gz',[(f,str(f.relative_to(x))) for f in files(x)]);save(p/'deterministic.json',selected(x))
 known={r['sha256']:str((e/'2026-09-16-stage1-1a-r2'/r['path']).relative_to(e)) for r in read(e/'2026-09-16-stage1-1a-r2/packet.json')['files']};refs=[];rows=[]
 for f in files(native):
  n=str(f.relative_to(native));h=sha(f)
  if h in known:refs.append(dict(path=n,sha256=h,evidence_path=known[h]))
  else:rows.append((f,n))
 archive(p/'native.tar.gz',rows);save(p/'native-references.json',refs)
 paths=[BASE+'/packet.json','2026-09-19-stage1-collector-qualification-r1/collector.wasm','2026-09-19-stage1-integer-core-r1/execution/integer.wasm','2026-09-19-stage1-float-core-r2/packet.json','2026-09-19-stage1-float-core-r2/execution/float.wasm','2026-09-19-stage1-float-core-r2/execution/detector.wasm','2026-09-19-stage1-float-owner-r1/packet.json']
 save(p/'inputs.json',{n:sha(e/n) for n in paths});save(p/'toolchain.json',[dict(path=str(Path(n).resolve()),sha256=sha(Path(n).resolve())) for n in ['/usr/local/bin/node','/usr/local/bin/wat2wasm']])
 for n in ['service.mjs','floating-capabilities.mjs','loader.mjs']:shutil.copy(x/n,p/n)
 save(p/'summary.json',dict(read(x/'summary.json'),native_R6=read(p/'qualification/summary.json')))
 # Keep failures once, with compiler and exact runner per attempt, omitting
 # duplicate successful binaries and disposable U1 trees.
 rows=[];attempts=[]
 reasons={1:'Unclosed Lisp emitter form.',2:'Fixture used unsupported IGNORE declarations.',3:'Unclosed WAT float-kind function.',4:'Native unmasked exact-tiny underflow differs from decided D6 tiny-and-inexact policy; now explicit oracle join.',6:'Lost-condition-root mutant correctly failed at h_single before expected h_collect.',7:'FLOAT of same precision returned a copy rather than the native object identity.',8:'Old default harness omitted the new integrated loader dependencies.'}
 for i,reason in reasons.items():
  d=Path('/tmp')/f'ccl-float-calls-r{i}';attempts.append(dict(attempt=i,reason=reason))
  for n in ['compiled/compile.log','compiled/proposal/files/compiler/WASM32/wasm32-backend.lisp','driver/compile.lisp','driver/runtime.lisp','driver/cases.lisp','execute.mjs','service.mjs','eager.log','policy-join.json','native-observed.json','native.json','lost-condition-root/eager.log','default/execution.log']:
   f=d/n
   if f.is_file():rows.append((f,d.name+'/'+n))
 archive(p/'development.tar.gz',rows);save(p/'development.json',dict(failed_attempts=attempts,passing_pre_controls=[5],notes='r6 and r8 positive runs passed; their qualification failures are retained. Original r7 identity failure is rejected by copy-same-format control.'))
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
 actual=selected(out/'execution');expected=read(p/'deterministic.json');assert actual.keys()==expected.keys(),(actual.keys()-expected.keys(),expected.keys()-actual.keys())
 for n,h in expected.items():assert actual[n]==h,n
 assert source==pins(e);v=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source),summary=read(out/'execution/summary.json'),native_R6=read(out/'qualification/summary.json'));save(out/'verification.json',v);print(json.dumps(v,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['retain','verify']);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--packet',type=Path,required=True)
 for n in ['execution','native','output']:p.add_argument('--'+n,type=Path)
 a=p.parse_args()
 if a.mode=='retain':retain(a.evidence.resolve(),a.execution.resolve(),a.native.resolve(),a.packet.resolve())
 else:verify(a.evidence.resolve(),a.packet.resolve(),a.output.resolve())
