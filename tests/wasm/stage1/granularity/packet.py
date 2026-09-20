import argparse,hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from run import ROOT,HERE,read,save,sha,command,run
import assessment
ID='STAGE1-GRANULARITY-R1';BASE='2026-09-20-stage1-materialization-r1'
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and not f.is_symlink() and '__pycache__' not in f.parts)
def pins(e):
 paths={ROOT/n for n in read(e/BASE/'source-pins.json')}
 paths.update(files(HERE));paths.update(ROOT/'runtime/wasm32'/n for n in ['materializer.mjs','ranges.mjs'])
 paths.add(ROOT/'doc/WASM/stage0/benchmarks.json')
 return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
def retained(out):
 for f in files(out):
  parts=f.relative_to(out).parts
  if any(x.endswith('-driver') or x in ['proposal','source'] for x in parts):continue
  if parts[0].startswith('revision-') and f.name not in ['plain.wat','plain.wasm','revision-native.json']:continue
  yield f
def deterministic(out):
 return {str(f.relative_to(out)):sha(f) for f in retained(out) if f.suffix in ['.json','.mjs','.wat','.wasm','.dx64fsl','.txt'] and not f.name.endswith('.command.json') and f.name not in ['command.json','timing-summary.json','retention.json','cold.json','warm.json'] and not f.name.startswith('cold-')}
def manifest(p):save(p/'packet.json',dict(id=ID,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def retain(e,out,p):
 assert not p.exists();p.mkdir();source=pins(e)
 save(out/'assessment.json',assessment.assess(out,e/BASE));save(out/'publication-controls.json',assessment.controls(out,e/BASE));save(out/'measurement-check.json',assessment.timing(out))
 for f in retained(out):
  dst=p/'execution'/f.relative_to(out);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,dst)
 save(p/'deterministic.json',deterministic(out));save(p/'source-pins.json',source)
 with tarfile.open(p/'sources.tar.gz','w:gz') as t:
  for n in source:t.add(ROOT/n,arcname=n,recursive=False)
 for n in ['README.md','scope.json','development.json','coverage.json']:shutil.copy(HERE/n,p/n)
 for n in ['summary.json','assessment.json','publication-controls.json','measurement-check.json','timing-summary.json']:shutil.copy(out/n,p/n)
 for n in ['abi-decision.json','abi-binding.json']:shutil.copy(e/BASE/n,p/n)
 shutil.copy(ROOT/'doc/WASM/stage0/benchmarks.json',p/'benchmark-policy.json')
 save(p/'inputs.json',{n:sha(e/n) for n in [BASE+'/'+x for x in ['packet.json','wasm32-backend.lisp','qualification/summary.json','execution/policy.json','execution/templates/modules.json']]+['macos-u1-inputs/'+x for x in ['pins.json','source.tar','bootstrap.tar.gz','tests.tar']]})
 with tarfile.open(p/'development.tar.gz','w:gz') as t:
  for r in read(HERE/'development.json')['attempts']:
   for n in r.get('retained',[]):t.add(Path('/tmp')/n,arcname=n,recursive=False)
 tools=[]
 for n in ['/usr/local/bin/node','/usr/local/bin/wat2wasm','/usr/local/bin/wasm-objdump']:
  f=Path(n).resolve();tools.append(dict(path=str(f),sha256=sha(f),version=subprocess.check_output([str(f),'--version'],text=True).strip()))
 save(p/'toolchain.json',dict(tools=tools));assert source==pins(e);manifest(p)
def verify(e,p,out):
 out.mkdir(parents=True,exist_ok=False);source=pins(e);assert source==read(p/'source-pins.json'),'source pins'
 for row in read(p/'packet.json')['files']:assert sha(p/row['path'])==row['sha256'],row['path']
 for n,h in read(p/'inputs.json').items():assert sha(e/n)==h,n
 for row in read(p/'toolchain.json')['tools']:assert sha(Path(row['path']))==row['sha256']
 assert sha(ROOT/'compiler/WASM32/wasm32-backend.lisp')==sha(e/BASE/'wasm32-backend.lisp'),'native reuse identity'
 command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution','--no-timing'],out/'replay.log')
 x=out/'execution';save(x/'assessment.json',assessment.assess(x,e/BASE));save(x/'publication-controls.json',assessment.controls(x,e/BASE));save(x/'measurement-check.json',assessment.timing(p/'execution'))
 expected=read(p/'deterministic.json');actual=deterministic(x);assert expected==actual,[(n,expected.get(n),actual.get(n)) for n in expected.keys()|actual.keys() if expected.get(n)!=actual.get(n)]
 if (p/'role-controls.json').exists():
  from publish import role_controls
  assert role_controls(e,read(p/'inventory.json'),read(e/(p.name+'-results.json')),sha(p/'inventory.json'))==read(p/'role-controls.json')
 assert source==pins(e);record=dict(status='PASS',deterministic_files=len(actual),source_pins=len(source),summary=read(x/'summary.json'),native_R6='Reused accepted LL21-a qualification by exact integrated compiler identity',timings='Raw retained arithmetic and minima verified; fresh times are not required to be identical.')
 save(out/'verification.json',record);print(json.dumps(record,indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True);a.add_argument('--execution',type=Path);a.add_argument('--output',type=Path);v=a.parse_args()
 if v.mode=='retain':retain(v.evidence.resolve(),v.execution.resolve(),v.packet.resolve())
 else:verify(v.evidence.resolve(),v.packet.resolve(),v.output.resolve())
