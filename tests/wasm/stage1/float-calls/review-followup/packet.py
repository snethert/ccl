import argparse,hashlib,importlib.util,json,shutil,subprocess,sys,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE.parents[3]
PACK='2026-09-19-stage1-float-calls-r1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
def pins(e):
 source=read(e/PACK/'source-pins.json')
 for n,h in source.items():assert sha(ROOT/n)==h,n
 extra=[*files(HERE),ROOT/'tests/wasm/stage1/float-core/execute.mjs',ROOT/'tests/wasm/stage1/float-core/run.py',ROOT/'doc/WASM/stage1/integer-float-coercion.md']
 return source|{str(f.relative_to(ROOT)):sha(f) for f in extra}
def selected(p):
 return {str(f.relative_to(p)):sha(f) for f in files(p) if not any(n in f.relative_to(p).parts for n in ['driver','source','proposal']) and not f.name.endswith('.command.json') and f.name!='command.json' and (f.suffix in ['.c','.mjs','.wat','.wasm','.dx64fsl','.json'] or f.name in ['native-results.txt','native-args.txt','source-refusals.txt'])}
def archive(p,rows):
 with tarfile.open(p,'w:gz') as t:
  for f,n in rows:t.add(f,arcname=n,recursive=False)
def manifest(p):save(p/'packet.json',dict(id='STAGE1-FLOAT-CALLS-R2',kind='AUXILIARY_GENERATED_FLOATING_CALLS_COERCION_FOLLOWUP',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def retain(e,x,p):
 assert not p.exists() and read(x/'summary.json')['status']=='PASS';p.mkdir();source=pins(e);save(p/'source-pins.json',source)
 old=read(e/PACK/'source-pins.json');archive(p/'source-additions.tar.gz',[(ROOT/n,n) for n in source if n not in old]);save(p/'source-base.json',dict(packet=PACK+'/packet.json',sha256=sha(e/PACK/'packet.json'),archive=PACK+'/sources.tar.gz',archive_sha256=sha(e/PACK/'sources.tar.gz')))
 archive(p/'execution.tar.gz',[(f,str(f.relative_to(x))) for f in files(x)]);save(p/'deterministic.json',selected(x))
 for a,b in [('primitive/float.c','float-lisp.c'),('primitive/float.wasm','float-lisp.wasm'),('float-service.mjs','float-service.mjs'),('summary.json','summary.json')]:shutil.copy(x/a,p/b)
 paths=[PACK+'/packet.json',PACK+'/qualification/summary.json',PACK+'/wasm32-backend.lisp',PACK+'/verification.json','2026-09-19-stage1-float-core-r2/packet.json','2026-09-19-stage1-float-core-r2/execution/cases.json','2026-09-19-stage1-float-core-r2/execution/detector.wasm','2026-09-19-stage1-collector-qualification-r1/collector.wasm','2026-09-19-stage1-integer-core-r1/execution/integer.wasm']
 refs=read(e/PACK/'inputs.json')|{n:sha(e/n) for n in paths};save(p/'inputs.json',refs)
 tool=read(x/'primitive/toolchain.json');save(p/'toolchain.json',dict(clang=tool,tools=[dict(path=str(Path(n).resolve()),sha256=sha(Path(n).resolve())) for n in ['/usr/local/bin/node','/usr/local/bin/wat2wasm']]))
 rows=[]
 for run,names in [('ccl-float-band-probe-r1',['driver/compile.lisp','driver/cases.lisp','native-observed.json','cases.json','eager.json','eager.log','float-service.mjs','service.mjs']),('ccl-float-band-r2',['driver/cases.lisp','compiled/compile.log'])]:
  for n in names:
   f=Path('/tmp')/run/n
   if f.is_file():rows.append((f,run+'/'+n))
 archive(p/'development.tar.gz',rows);save(p/'development.json',dict(original_finding='R1 raises inexact for the native-silent bignum rounding row, retained as h_single/664.',harness_failure='Expanded native cases used nonexistent single-float-from-bits; replaced by a literal finite value and masked double-to-single infinity conversion.',passing_pre_controls=['ccl-float-band-r3'],final='ccl-float-band-r4',compiler_unchanged=True))
 assert read(x/'raw-regression.json')['status']=='PASS';assert [r['cases'] for r in read(x/'raw-regression.json')['reports']]==[59083]*3
 assert source==pins(e);manifest(p)
def verify(e,p,out):
 out.mkdir(parents=True,exist_ok=False);source=pins(e);assert source==read(p/'source-pins.json')
 for row in read(p/'packet.json')['files']:assert sha(p/row['path'])==row['sha256'],row['path']
 for n,h in read(p/'inputs.json').items():assert sha(e/n)==h,n
 t=read(p/'toolchain.json');assert sha(Path(t['clang']['compiler']))==t['clang']['sha256']
 for tool in t['tools']:assert sha(Path(tool['path']))==tool['sha256']
 args=[sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'];save(out/'command.json',list(map(str,args)))
 with (out/'replay.log').open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1800)
 actual=selected(out/'execution');expected=read(p/'deterministic.json');assert actual.keys()==expected.keys()
 for n,h in expected.items():assert actual[n]==h,n
 assert source==pins(e);v=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source),summary=read(out/'execution/summary.json'));save(out/'verification.json',v);print(json.dumps(v,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['retain','verify']);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--packet',type=Path,required=True);p.add_argument('--execution',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 if a.mode=='retain':retain(a.evidence.resolve(),a.execution.resolve(),a.packet.resolve())
 else:verify(a.evidence.resolve(),a.packet.resolve(),a.output.resolve())
