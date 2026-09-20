"""Retain and replay unchanged-compiler numeric/owner composition."""
import argparse,hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from derive import HERE,ROOT,COMPILER,compiler,loader,owner
BASE='2026-09-19-stage1-integer-conditions-r2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1200)
def archive(p,rows):
 with tarfile.open(p,'w:gz') as t:
  for f,n in rows:t.add(f,arcname=n,recursive=False)
def pins(e):
 result=read(e/BASE/'source-pins.json');record=read(ROOT/'doc/WASM/stage1/integration-integer-conditions.json');changes={r['file']:r for r in record['files']}
 for n,h in list(result.items()):
  actual=sha(ROOT/n)
  if actual!=h:assert n in changes and changes[n]['before']==h and changes[n]['after']==actual,n
  result[n]=actual
 for f in files(HERE):result[str(f.relative_to(ROOT))]=sha(f)
 for n in ['runtime/wasm32/allocation-service.mjs','runtime/wasm32/loader.mjs','runtime/wasm32/binary.mjs','runtime/wasm32/stub.wat','doc/WASM/stage1/integration-integer-conditions.json']:result[n]=sha(ROOT/n)
 return result
def native_reuse(e):
 compiler();assert sha(e/BASE/'wasm32-backend.lisp')==COMPILER
 report=read(e/BASE/'qualification/summary.json');assert report['status']=='PASS'
 manifest={r['path']:r['sha256'] for r in read(e/BASE/'packet.json')['files']}
 for n in ['wasm32-backend.lisp','qualification/summary.json']:assert sha(e/BASE/n)==manifest[n]
 return dict(status='PASS',kind='EXACT_COMPILER_NATIVE_R6_R6A_REUSE',compiler_sha256=COMPILER,packet=BASE+'/packet.json',packet_sha256=sha(e/BASE/'packet.json'),qualification_sha256=sha(e/BASE/'qualification/summary.json'),native=report['native'])
def selected(p):
 result={}
 for f in files(p):
  rel=f.relative_to(p)
  if any(x in rel.parts for x in ['driver','source','proposal']):continue
  if f.name.endswith('.command.json') or f.name=='command.json':continue
  if f.suffix in ['.json','.mjs','.wasm','.wat','.dx64fsl'] or f.name in ['native-results.txt','source-refusals.txt','native-zero-traps.txt','native-policy-errors.txt','native-reader-errors.txt','mode-admission.txt']:result[str(rel)]=sha(f)
 return result
def manifest(p):save(p/'packet.json',dict(id='STAGE1-INTEGER-OWNER-R1',kind='AUXILIARY_NUMERIC_OWNER_COMPOSITION',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def retain(e,x,p):
 assert not p.exists() and read(x/'summary.json')['status']=='PASS';p.mkdir()
 assert sha(x/'compiled/proposal/files/compiler/WASM32/wasm32-backend.lisp')==COMPILER
 source=pins(e);save(p/'source-pins.json',source);archive(p/'sources.tar.gz',[(ROOT/n,n) for n in source]);save(p/'native-reuse.json',native_reuse(e))
 archive(p/'execution.tar.gz',[(f,str(f.relative_to(x))) for f in files(x)]);save(p/'deterministic.json',selected(x))
 (p/'loader.mjs').write_text(loader());(p/'collector-owner.mjs').write_text(owner());shutil.copy(HERE/'numeric-capabilities.mjs',p/'numeric-capabilities.mjs')
 for n in ['loader.mjs','collector-owner.mjs','numeric-capabilities.mjs']:assert (p/n).read_bytes()==(x/n).read_bytes()
 paths=[BASE+'/packet.json',BASE+'/wasm32-backend.lisp',BASE+'/qualification/summary.json','2026-09-19-stage1-collector-qualification-r1/collector.wasm','2026-09-19-stage1-integer-core-r1/execution/integer.wasm']
 save(p/'inputs.json',{n:sha(e/n) for n in paths});shutil.copy(x/'summary.json',p/'summary.json');shutil.copy(HERE/'README.md',p/'README.md')
 save(p/'toolchain.json',[dict(path=str(Path(n).resolve()),sha256=sha(Path(n).resolve())) for n in ['/usr/local/bin/node','/usr/local/bin/wat2wasm']])
 # Development inputs are shared. Keep each failed harness, control and log,
 # plus the original compiler run once, instead of duplicating every module.
 attempts=[];rows=[]
 for d in sorted(Path('/tmp').glob('ccl-integer-owner-r[0-9]*')):
  if d.resolve()==x.resolve():continue
  if (d/'summary.json').exists():continue
  reason=read(d/'failure.json') if (d/'failure.json').exists() else dict(reason='Initial import-order assertion; see eager.log')
  attempts.append(dict(directory=d.name,**reason))
  for f in files(d):
   rel=f.relative_to(d)
   if any(k in rel.parts for k in ['compiled','driver']):continue
   rows.append((f,d.name+'/'+str(rel)))
 first=Path('/tmp/ccl-integer-owner-r1')
 if first.exists():
  for f in files(first/'compiled'):
   if f.suffix in ['.wat','.wasm'] or f.name in ['compile.log','command.json']:rows.append((f,first.name+'/'+str(f.relative_to(first))))
 archive(p/'development.tar.gz',rows);save(p/'development.json',dict(attempts=attempts,notes=['The first harness expected function imports in reverse order.','The PROGV probe required zero symbol flag words; the inherited harness had filled them with NIL.','Nested-boundary refusal requires a shortage; the test now fills free space before invocation.','The first attempted forged-pair mutant retained a foreign error-tag mismatch and escaped; the retained replacement keys the association by function and is rejected.','The no-assurance fault first failed a nested-boundary diagnostic; its focused execution now begins with collecting cases to witness a value-path refusal.', 'The pressure overlay initially assumed every module emitted restart_make; it now handles the emitted subset.']))
 assert source==pins(e);manifest(p)
def verify(e,p,out):
 out.mkdir(parents=True,exist_ok=False);source=pins(e);assert source==read(p/'source-pins.json')
 for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 for n,h in read(p/'inputs.json').items():assert sha(e/n)==h,n
 for t in read(p/'toolchain.json'):assert sha(Path(t['path']))==t['sha256']
 assert native_reuse(e)==read(p/'native-reuse.json')
 assert (p/'loader.mjs').read_text()==loader() and (p/'collector-owner.mjs').read_text()==owner()
 command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'],out/'execution.log')
 actual=selected(out/'execution');expected=read(p/'deterministic.json');assert actual.keys()==expected.keys(),(actual.keys()-expected.keys(),expected.keys()-actual.keys())
 for n,h in expected.items():assert actual[n]==h,n
 assert source==pins(e);result=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source),native_R6='REUSED_EXACT_ACCEPTED_COMPILER',summary=read(out/'execution/summary.json'));save(out/'verification.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True)
 for n in ['execution','output']:a.add_argument('--'+n,type=Path)
 v=a.parse_args()
 if v.mode=='retain':retain(v.evidence.resolve(),v.execution.resolve(),v.packet.resolve())
 else:verify(v.evidence.resolve(),v.packet.resolve(),v.output.resolve())
