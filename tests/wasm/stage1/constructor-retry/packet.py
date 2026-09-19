"""Retain exact retry proposal, native qualification, executable replay and failures."""
import argparse,hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from backend import generate
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];PARENT='2026-09-19-stage1-allocation-retry-r1'
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
 for n in ['runtime/wasm32/collector-owner.mjs','runtime/wasm32/collector.c','runtime/wasm32/binary.mjs','runtime/wasm32/loader.mjs','runtime/wasm32/allocation-service.mjs']:result[n]=sha(ROOT/n)
 return dict(sorted(result.items()))
def qualify(e,native,out):
 assert (native/'proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()==generate()
 command([sys.executable,HERE.parent/'registration/qualify.py','--output',native,'--inputs',e/'macos-u1-inputs','--kernel',e/'2026-09-12-native-census-r7/baseline/build/dx86cl64','--destination',out],out.with_suffix('.log'))
def manifest(p):save(p/'packet.json',dict(id='STAGE1-CONSTRUCTOR-RETRY-R1',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def selected(d):
 return {str(f.relative_to(d)):sha(f) for f in files(d) if (f.suffix in ('.wat','.wasm','.dx64fsl') or f.name in ('summary.json','native.json','execution.json','controls.json','cases.json','compatibility.json','root-contracts.json','root-ir.json','pressure.json','lazy.json','nested.json')) and not any(x in f.relative_to(d).parts for x in ('executed-sources','proposal'))}
def retain(e,execution,native,p):
 assert not p.exists();assert read(execution/'summary.json')['compiler_mutants']==8;assert read(native/'run.json')['status']=='PASS'
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
 save(p/'inputs.json',dict(references=[dict(locator=n,sha256=sha(e/n)) for n in [PARENT+'/packet.json','2026-09-19-stage1-collector-live-r1/packet.json','2026-09-19-stage1-collector-live-r1/collector.c','2026-09-19-stage1-collector-live-r1/collector.wasm']],scope='Auxiliary raw-constructor retry and explicit owner-capability loader profile. No LL06/LL18 credit.'))
 summary=read(execution/'summary.json');summary.pop('rows');save(p/'summary.json',dict(summary,inventory_credit=False,review_disposition='NOT_REVIEWED',native=read(p/'qualification/summary.json')))
 rows=[]
 attempts=['ccl-constructors-r1','ccl-constructors-r2','ccl-constructors-r4','ccl-constructors-controls-r1','ccl-constructors-controls-r2','ccl-constructors-controls-r3','ccl-constructors-controls-r4']
 for name in attempts:
  d=Path('/tmp')/name
  for f in files(d):
   if not any(x in f.relative_to(d).parts for x in ('executed-sources','proposal')):rows.append((f,name+'/'+str(f.relative_to(d))))
  log=Path('/tmp')/(name+'.log')
  if log.exists():rows.append((log,name+'/driver.log'))
 for f in [Path('/tmp/ccl-constructors-progv-diagnostic.log')]:
  if f.exists():rows.append((f,f.name))
 archive(p/'development.tar.gz',rows)
 save(p/'development.json',dict(attempts=attempts,notes=[
  'r1: condition registry increased the image root population beyond the inherited root-list reservation. Owner admission refused before execution; the fixture now declares a larger disjoint root-list region.',
  'r2: inherited symbol initialization filled the flags word with NIL, which PROGV correctly refused. Fixture symbols now have zero flags.',
  'r4: the pressure rewriter assumed every module emitted restart runtime. It now instruments that constructor only in modules which contain it.',
  'Controls r1-r4 rejected the intended stale-reference mutations, but their first failures differed from the initially predicted diagnostics. Retained observations identify poisoned value output, a PROGV type refusal, collector refusal of a stale restart action, and the corrupt binding-vector refusal. The final oracles require these exact first failures.',
  'Successful intermediate runs were superseded by pressure, loader composition and legacy-profile coverage. The one native run passed and qualifies the unchanged final compiler generator.'
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
