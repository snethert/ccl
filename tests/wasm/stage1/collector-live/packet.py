"""Scoped retention/replay of live-restart and moving-temporary corrections."""
import argparse,importlib.util,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from run import ROOT,HERE,CLANG,FLAGS,command,collector_source
from backend import generate
spec=importlib.util.spec_from_file_location('live_core_packet',HERE.parent/'collector-core/packet.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
read,save,sha,files,archive=core.read,core.save,core.sha,core.files,core.archive
PARENT='2026-09-19-stage1-collector-core-r1'
def pins(e):
 parent=read(e/PARENT/'source-pins.json')
 for n,h in parent.items():assert sha(ROOT/n)==h,n
 result=dict(parent,**{str(p.relative_to(ROOT)):sha(p) for p in files(HERE)})
 for n in ('compiler/X86/X8632/x8632-arch.lisp','compiler/ARM/arm-arch.lisp','library/lispequ.lisp','lib/macros.lisp'):
  result[n]=sha(ROOT/n)
 return dict(sorted(result.items()))
def manifest(p):save(p/'packet.json',dict(id='STAGE1-COLLECTOR-LIVE-R1',review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p) if f.name!='packet.json']))
def qualify(e,native,out):
 core.generate=generate;core.qualify(e,native,out)
def retain(e,execution,native,inherited,p):
 assert not p.exists()
 for d,n in ((execution,'summary.json'),(native,'run.json'),(inherited,'summary.json')):assert read(d/n)['status']=='PASS',d
 for f in (execution/'harness/wasm32-backend.lisp',native/'proposal/files/compiler/WASM32/wasm32-backend.lisp',inherited/'harness/wasm32-backend.lisp'):assert f.read_text()==generate(),f
 assert (execution/'harness/collector.c').read_text()==collector_source()
 p.mkdir();source=pins(e);save(p/'source-pins.json',source);archive(p/'source.tar.gz',[(ROOT/n,n) for n in source])
 (p/'wasm32-backend.lisp').write_text(generate());(p/'collector.c').write_text(collector_source());shutil.copy(execution/'harness/collector.wasm',p/'collector.wasm')
 for name,d in [('execution',execution),('inherited',inherited)]:archive(p/(name+'.tar.gz'),[(f,str(f.relative_to(d))) for f in files(d)])
 base=e/'2026-09-16-stage1-1a-r2';known={r['sha256']:str((base/r['path']).relative_to(e)) for r in read(base/'packet.json')['files']};refs=[];rows=[]
 for f in files(native):
  h=sha(f);n=str(f.relative_to(native))
  if h in known:refs.append(dict(path=n,sha256=h,evidence_path=known[h]))
  else:rows.append((f,n))
 archive(p/'native.tar.gz',rows);save(p/'native-references.json',refs);qualify(e,native,p/'qualification')
 toolpaths=[Path(CLANG),Path(subprocess.check_output([CLANG,'--target=wasm32','--print-prog-name=wasm-ld'],text=True).strip()),Path('/usr/local/bin/wat2wasm'),Path('/usr/local/bin/node')]
 save(p/'toolchain.json',dict(tools=[dict(path=str(t),sha256=sha(t),version=subprocess.check_output([str(t),'--version'],text=True).strip()) for t in toolpaths],collector_flags=FLAGS))
 save(p/'summary.json',dict(read(execution/'summary.json'),review_disposition='NOT_REVIEWED',inventory_credit=False,native=read(p/'qualification/summary.json'),inherited={k:{f:read(inherited/'summary.json')[k][f] for f in ('modules','comparisons')} for k in ('corpus','conditions','call_errors')}))
 save(p/'inputs.json',dict(parent=dict(locator=PARENT+'/packet.json',sha256=sha(e/PARENT/'packet.json')),scope='Retained sources, compile inputs and native oracle inherited unchanged; new compiled controls, C scanner and moving corpus. No LL06 or LL18 slot claimed.'))
 rows=[]
 for d in sorted(Path('/tmp').glob('ccl-live-r[0-9]*')):
  if not d.is_dir() or (d/'summary.json').exists():continue
  for f in files(d):
   rel=f.relative_to(d)
   if any(x in rel.parts for x in ('proposal','executed-sources')):continue
   rows.append((f,d.name+'/'+str(rel)))
  log=Path(str(d)+'.log')
  if log.exists():rows.append((log,d.name+'/driver.log'))
 d=Path('/tmp/ccl-live-debug-r1')
 for f in files(d):rows.append((f,d.name+'/'+str(f.relative_to(d))))
 archive(p/'development.tar.gz',rows)
 save(p/'development.json',dict(notes=[
  'r3: actual EQ stale operand across RHS collection; r5: actual early captured-cell address; r6: canonical T misclassified as stack callable; r11: actual cached implicit condition used after handler collection. Each is fixed and covered by a final compiled control.',
  'r1 fixture CAR T folded to an unsupported native error form; r2 quoted special was unregistered; r4 emitted Lisp had one excess closing parenthesis; r8 fixture keyword :DONE had no owner entry. Exact generated compilers, fixture scripts and logs retained.',
  'r9 debugger probe ran in bootstrap mode. r10 added an unused per-case mode field. r11 used the harness\'s actual d_ service-mode convention, exposed the stale condition, and r12 passed with the dedicated condition root.',
  'Debug collector in ccl-live-debug-r1 only numbers checked-root refusals in scratch; not a qualifying execution.',
  'Successful exploratory r7/r12 were superseded as the corpus and controls expanded. Final execution and native qualification are bound to this exact generated compiler. Failed attempts retain generated inputs, not a reconstructed original Python generator.'
 ]))
 assert source==pins(e);manifest(p)
def verify(e,p,out):
 assert not out.exists();out.mkdir();source=read(p/'source-pins.json');assert source==pins(e)
 for row in read(p/'packet.json')['files']:assert sha(p/row['path'])==row['sha256'],row['path']
 for row in read(p/'toolchain.json')['tools']:assert sha(Path(row['path']))==row['sha256']
 assert (p/'wasm32-backend.lisp').read_text()==generate();assert (p/'collector.c').read_text()==collector_source()
 parent=read(p/'inputs.json')['parent'];assert sha(e/parent['locator'])==parent['sha256']
 native=out/'native';native.mkdir()
 with tarfile.open(p/'native.tar.gz') as t:t.extractall(native,filter='data')
 for row in read(p/'native-references.json'):
  src=e/row['evidence_path'];assert sha(src)==row['sha256'];dst=native/row['path'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(src,dst)
 qualify(e,native,out/'qualification')
 command([sys.executable,HERE/'run.py','--evidence',e,'--output',out/'execution'],out/'execution.log')
 command([sys.executable,HERE/'inherited.py','--evidence',e,'--output',out/'inherited'],out/'inherited.log')
 count=0
 for name in ('execution','inherited'):
  with tarfile.open(p/(name+'.tar.gz')) as t:
   for member in t.getmembers():
    path=Path(member.name)
    if member.isfile() and core.deterministic(path) and not any(x in path.parts for x in ('executed-sources','proposal')):
     assert (out/name/path).read_bytes()==t.extractfile(member).read(),str(path);count+=1
 assert source==pins(e);result=dict(status='PASS',deterministic_files=count,source_pins=len(source));save(out/'verification.json',result);print(result)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify']);a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True)
 for n in ('execution','native','inherited','output'):a.add_argument('--'+n,type=Path)
 o=a.parse_args();e=o.evidence.resolve();p=o.packet.resolve()
 if o.mode=='retain':retain(e,o.execution.resolve(),o.native.resolve(),o.inherited.resolve(),p)
 else:verify(e,p,o.output.resolve())
