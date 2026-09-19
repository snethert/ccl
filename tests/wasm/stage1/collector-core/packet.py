"""Retain/replay the collector mechanism without claiming an LL18 slot."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from run import ROOT,HERE,CLANG,FLAGS,command
from backend import generate

def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files(p):return sorted(x for x in p.rglob('*') if x.is_file() and '__pycache__' not in x.parts)
def archive(dest,rows):
 with tarfile.open(dest,'w:gz') as t:
  for p,name in rows:t.add(p,arcname=name,recursive=False)
def pins(e):
 parent=read(e/'2026-09-19-stage1-binding-vector-r1/source-pins.json')
 for n,h in parent.items():assert sha(ROOT/n)==h,n
 return dict(sorted(dict(parent,**{str(p.relative_to(ROOT)):sha(p) for p in files(HERE)}).items()))
def manifest(p):save(p/'packet.json',dict(id='STAGE1-COLLECTOR-CORE-R1',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def qualify(e,native,out):
 spec=importlib.util.spec_from_file_location('collector_qualification',HERE.parent/'binding-vector/packet.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.generate=generate;m.qualify(e,native,out)
def retain(e,execution,native,inherited,p):
 assert not p.exists();assert read(native/'run.json')['status']=='PASS';assert read(execution/'summary.json')['status']=='PASS'
 for f in (execution/'harness/wasm32-backend.lisp',native/'proposal/files/compiler/WASM32/wasm32-backend.lisp',inherited/'harness/wasm32-backend.lisp'):assert f.read_text()==generate(),f
 assert all(read(inherited/'summary.json')[k]['status']=='PASS' for k in ('corpus','conditions','call_errors'))
 p.mkdir();source=pins(e);save(p/'source-pins.json',source);archive(p/'source.tar.gz',[(ROOT/n,n) for n in source]);(p/'wasm32-backend.lisp').write_text(generate());shutil.copy(execution/'collector.wasm',p/'collector.wasm')
 for name,d in [('execution',execution),('inherited',inherited)]:archive(p/(name+'.tar.gz'),[(f,str(f.relative_to(d))) for f in files(d)])
 # Reuse the pinned pristine baseline bytes, never duplicate a baseline tree.
 base=e/'2026-09-16-stage1-1a-r2';known={r['sha256']:str((base/r['path']).relative_to(e)) for r in read(base/'packet.json')['files']};refs=[];rows=[]
 for f in files(native):
  h=sha(f);n=str(f.relative_to(native))
  if h in known:refs.append(dict(path=n,sha256=h,evidence_path=known[h]))
  else:rows.append((f,n))
 archive(p/'native.tar.gz',rows);save(p/'native-references.json',refs);qualify(e,native,p/'qualification')
 toolpaths=[Path(CLANG),Path(subprocess.check_output([CLANG,'--target=wasm32','--print-prog-name=wasm-ld'],text=True).strip()),Path('/usr/local/bin/wat2wasm'),Path('/usr/local/bin/node')]
 save(p/'toolchain.json',dict(tools=[dict(path=str(t),sha256=sha(t),version=subprocess.check_output([str(t),'--version'],text=True).strip()) for t in toolpaths],collector_flags=FLAGS))
 save(p/'summary.json',dict(read(execution/'summary.json'),review_disposition='NOT_REVIEWED',inventory_credit=False,native=read(p/'qualification/summary.json'),inherited={k:{f:read(inherited/'summary.json')[k][f] for f in ('modules','comparisons')} for k in ('corpus','conditions','call_errors')}))
 rows=[]
 names=['ccl-collector-development-r1','ccl-collector-development-r8','ccl-collector-development-r13','ccl-collector-development-r17']
 names += [d.name for d in sorted(Path('/tmp').glob('ccl-collector-run-r*')) if d.is_dir() and not (d/'summary.json').exists()]
 for name in names:
  d=Path('/tmp')/name
  for f in files(d):
   # Full failed target artifacts/commands, without duplicate prerequisite trees.
   if 'proposal' in f.relative_to(d).parts or 'executed-sources' in f.relative_to(d).parts:continue
   rows.append((f,name+'/'+str(f.relative_to(d))))
 for f in [Path('/tmp/ccl-collector-retain.log')]:
  if f.exists():rows.append((f,'prepublication/'+f.name))
 for f in sorted(Path('/tmp').glob('ccl-collector-run-r*.log')):rows.append((f,'driver-logs/'+f.name))
 for name in ('ccl-collector-native-r1','ccl-collector-native-r2'):
  d=Path('/tmp')/name
  for n in ('run.json','proposal/files/compiler/WASM32/wasm32-backend.lisp'):
   f=d/n
   if f.exists():rows.append((f,name+'/'+n))
 for name in ('failed-packet.py','source-pins.json','source.tar.gz','ccl-collector-retain-r2.log'):
  f=Path('/tmp/ccl-collector-retain-failed-r2')/name
  if f.exists():rows.append((f,'retention-failure/'+name))
 archive(p/'development.tar.gz',rows)
 save(p/'development.json',dict(notes=['First C service set an error but returned success from early refusal; fixed and retained as false-success mutant.','Raw vector admission initially used four-byte widths for 16-bit and double-float vectors; exact-width tests found this before finalization, corrected and retained as a mutant.', 'Live closure environment and recursive self used cached Wasm locals after movement; both exposed by generated execution, fixed and retained as compiled controls.','Initial collector assumed monotonically ordered root records; direct producer descriptors violate that assumption. Cycle detection now uses visited identities and the independent test includes a nonmonotonic chain.','First retention refused before publication because its LLVM linker path assumption was wrong; the corrected tool pin comes from clang --print-prog-name=wasm-ld. Failed retainer, source archive, pins and log retained; successful execution archives are shared inputs, not reruns.', 'Harness failures: missing Python module alias before any output directory (driver log retained; original whole driver was not snapshotted), extra source parenthesis, generated JS parenthesis, duplicate standalone-test lexical name, observer lexical scope, and treating a cons-valued import as a symbol in the external-slot list.','Native r1 predates capture reload; native r2 predates self reload. Only final native r3 qualifies this proposal. No old execution is relabelled.']))
 assert source==pins(e);manifest(p)
def deterministic(p):return p.suffix in ('.wat','.wasm','.dx64fsl') or p.name in ('summary.json','native.json','execution.json','controls.json','core-checks.json','cases.json','root-contracts.json','root-ir.json','positive.json')
def verify(e,p,out):
 assert not out.exists();out.mkdir();source=read(p/'source-pins.json');assert source==pins(e)
 for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 assert (p/'wasm32-backend.lisp').read_text()==generate()
 for row in read(p/'toolchain.json')['tools']:assert sha(Path(row['path']))==row['sha256']
 native=out/'native';native.mkdir()
 with tarfile.open(p/'native.tar.gz') as t:t.extractall(native,filter='data')
 for r in read(p/'native-references.json'):
  src=e/r['evidence_path'];assert sha(src)==r['sha256'];dest=native/r['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(src,dest)
 qualify(e,native,out/'qualification')
 command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'],out/'execution.log')
 command([sys.executable,HERE/'inherited.py','--evidence',e,'--output',out/'inherited'],out/'inherited.log')
 count=0
 for name in ('execution','inherited'):
  with tarfile.open(p/(name+'.tar.gz')) as t:
   for member in t.getmembers():
    path=Path(member.name)
    if member.isfile() and deterministic(path) and not any(x in path.parts for x in ('executed-sources','proposal')):
     dest=out/name/path;assert dest.read_bytes()==t.extractfile(member).read(),str(dest);count+=1
 assert source==pins(e);result=dict(status='PASS',deterministic_files=count,source_pins=len(source));save(out/'verification.json',result);print(result)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True)
 for n in ('execution','native','inherited','output'):a.add_argument('--'+n,type=Path)
 o=a.parse_args();e=o.evidence.resolve();p=o.packet.resolve()
 if o.mode=='retain':retain(e,o.execution.resolve(),o.native.resolve(),o.inherited.resolve(),p)
 else:verify(e,p,o.output.resolve())
