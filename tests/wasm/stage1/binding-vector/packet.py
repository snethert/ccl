#!/usr/bin/env python3
"""Exact-proposal retention and replay for the LL17 qualification."""
import argparse,importlib.util,json,shutil,sys,tarfile
from pathlib import Path
from backend import generate
from assessment_ll17 import run as assessment
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('ll17_reuse_control_packet',HERE.parent/'control/packet.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
read,save,sha,need,files,archive,command=prior.read,prior.save,prior.sha,prior.need,prior.files,prior.archive,prior.command

def pins():
 result=prior.pins()
 for p in files(HERE):result[str(p.relative_to(ROOT))]=sha(p)
 for name in ('level-0/l0-symbol.lisp','level-0/ARM/arm-symbol.lisp','lisp-kernel/arm-exceptions.c','library/lispequ.lisp','doc/WASM/contracts/tcr.v1.json','doc/WASM/contracts/tcr.v2.json'):
  result[name]=sha(ROOT/name)
 return dict(sorted(result.items()))
def manifest(out):
 save(out/'packet.json',dict(id='STAGE1-BINDING-VECTOR-R1',review_disposition='NOT_REVIEWED',files=[dict(path=str(p.relative_to(out)),bytes=p.stat().st_size,sha256=sha(p)) for p in files(out) if p.name!='packet.json']))
def qualify(evidence,native,out):
 need((native/'proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()==generate(),'native exact compiler')
 prior.qualify(evidence,native,out)
def retain(evidence,execution,native,inherited,out):
 need(not out.exists(),'never overwrite packet')
 for d,name in [(execution,'summary.json'),(native,'run.json'),(inherited,'summary.json')]:need(read(d/name)['status']=='PASS','completed '+str(d))
 for p in (execution/'harness/wasm32-backend.lisp',native/'proposal/files/compiler/WASM32/wasm32-backend.lisp',inherited/'harness/wasm32-backend.lisp'):need(p.read_text()==generate(),'same compiler '+str(p))
 out.mkdir();source=pins();save(out/'source-pins.json',source);archive(out/'source.tar.gz',[(ROOT/n,n) for n in source]);(out/'wasm32-backend.lisp').write_text(generate());shutil.copy(HERE/'scope.json',out/'scope.json')
 result=assessment(execution,out/'assessment');qualify(evidence,native,out/'qualification')
 for name,d in [('execution',execution),('inherited',inherited)]:archive(out/(name+'.tar.gz'),[(p,str(p.relative_to(d))) for p in files(d)])
 for p in files(execution/'positive/compiled'):
  dest=out/'positive'/p.relative_to(execution/'positive/compiled');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest)
 accepted=evidence/'2026-09-16-stage1-1a-r2';known={r['sha256']:str((accepted/r['path']).relative_to(evidence)) for r in read(accepted/'packet.json')['files']};refs=[];rows=[]
 for p in files(native):
  name=str(p.relative_to(native));h=sha(p)
  if h in known:refs.append(dict(path=name,sha256=h,evidence_path=known[h]))
  else:rows.append((p,name))
 archive(out/'native.tar.gz',rows);save(out/'native-references.json',refs)
 for name in ('toolchain.json','options.json','abi-decision.json','abi-binding.json'):shutil.copy(evidence/'2026-09-19-stage1-control-r1'/name,out/name)
 summary=dict(result,test='S1-LL17-a',review_disposition='NOT_REVIEWED',modules=read(execution/'summary.json')['modules'],native_qualification=read(out/'qualification/summary.json'),scope=read(HERE/'scope.json'),inherited={k:{f:v[f] for f in ('modules','comparisons')} for k,v in read(inherited/'summary.json').items() if k in ('corpus','conditions','call_errors')})
 save(out/'summary.json',summary)
 save(out/'coverage.json',{'S1-LL17-a:bindings':dict(status='PASS',compiled_access=['positive/native.json','execution/positive/execution.json'],SYMBOL_VALUE_SET=['probe.py:v_read,v_set,v_bound,v_global,v_shadow,v_shadow_labels'],restoration=['probe.py:v_throw,v_error,v_cleanup_growth,v_missing','execution/positive/execution.json'],host_suspension=['observer.mjs','execution/positive/execution.json:suspensions'],growth=['runtime.wat','execution/resources/execution.json','execution/positive/execution.json:moved_vectors'],namespace=['owner-check.mjs','run.py:tcr_index namespace preserved'],controls=['execution/controls.json','assessment/controls.json'],native_R6=['qualification/summary.json','native.tar.gz','native-references.json'],locator_rule='execution/ and inherited/ are members of retained archives; source files are under binding-vector in source.tar.gz.')})
 rows=[];attempts=[]
 for stem in ('ccl-binding-vector-r1','ccl-binding-vector-r4','ccl-binding-vector-r8','ccl-binding-vector-r11','ccl-binding-vector-inherited-r1','ccl-binding-vector-inherited-r2'):
  d=Path('/tmp')/stem
  if not d.exists():continue
  kept=[]
  for p in files(d):
   rel=p.relative_to(d)
   if p.suffix in ('.log','.lisp') or (rel.parts[0]=='harness' and len(rel.parts)==2) or p.name in ('native.json','cases.json','summary.json','execution.json','command.json'):
    rows.append((p,stem+'/'+str(rel)));kept.append(str(rel))
  log=Path('/tmp')/(stem+'.log')
  if log.exists():rows.append((log,stem+'/driver.log'))
  attempts.append(dict(attempt=stem,files=len(kept)))
 for p in (Path('/tmp/ccl-binding-vector-native-r1/run.json'),Path('/tmp/ccl-binding-vector-native-r1/proposal/files/compiler/WASM32/wasm32-backend.lisp')):
  if p.exists():rows.append((p,'superseded-native/'+p.name))
 archive(out/'development.tar.gz',rows)
 save(out/'development.json',dict(attempts=attempts,notes=['Initial missing Lisp close parenthesis; constant SET oracle assumed PROGRAM-ERROR but pristine CCL reports SIMPLE-ERROR; runner imported the old resources module; shadowing patch initially matched two similar source walkers. All corrected before final execution.','Inherited metadata refusals index-limit/empty/partial-capacity are now positive growth. The retired old vector may still hold copied bindings; only the published vector must be restored. Both old-oracle failures retained.','Native r1 passed but predates lexical function shadow handling; its run record and proposal are superseded by final native r2, which alone qualifies this compiler.','Successful intermediate execution runs are not separate evidence packets.']))
 need(source==pins(),'sources changed');manifest(out)
def deterministic(p):
 return p.suffix in ('.wasm','.wat','.dx64fsl') or p.name in ('summary.json','controls.json','native.json','native-condition-classes.json','refusals.json','cases.json','execution.json','observations.json')
def verify(evidence,packet,out):
 out.mkdir(parents=True,exist_ok=False)
 for row in read(packet/'packet.json')['files']:
  p=(packet/row['path']).resolve();need(p.is_relative_to(packet.resolve()) and sha(p)==row['sha256'],'packet '+row['path'])
 source=read(packet/'source-pins.json');need(source==pins(),'source pins');need((packet/'wasm32-backend.lisp').read_text()==generate(),'proposal derivation')
 native=out/'native';native.mkdir()
 with tarfile.open(packet/'native.tar.gz') as t:t.extractall(native,filter='data')
 for row in read(packet/'native-references.json'):
  src=(evidence/row['evidence_path']).resolve();dest=(native/row['path']).resolve();need(src.is_relative_to(evidence) and dest.is_relative_to(native) and not dest.exists() and sha(src)==row['sha256'],'native reference');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(src,dest)
 qualify(evidence,native,out/'qualification')
 command([sys.executable,HERE/'run.py','--evidence',evidence,'--output',out/'execution','--qualify'],out/'execution.log');assessment(out/'execution',out/'assessment')
 command([sys.executable,HERE/'inherited.py','--evidence',evidence,'--output',out/'inherited'],out/'inherited.log')
 n=0
 for name in ('execution','inherited'):
  with tarfile.open(packet/(name+'.tar.gz')) as t:
   for m in t.getmembers():
    if deterministic(Path(m.name)):need(t.extractfile(m).read()==(out/name/m.name).read_bytes(),'replay '+name+'/'+m.name);n+=1
 for name in ('assessment.json','controls.json'):need((packet/'assessment'/name).read_bytes()==(out/'assessment'/name).read_bytes(),'assessment')
 need(source==pins(),'sources changed during replay');save(out/'verification.json',dict(status='PASS',deterministic_files=n,source_pins=len(source),packet_sha256=sha(packet/'packet.json'),native_qualification=read(out/'qualification/summary.json')));print('LL17 VERIFIED',n,'deterministic files')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['retain','verify']);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--packet',type=Path,required=True)
 for name in ('output','execution','native','inherited'):p.add_argument('--'+name,type=Path)
 a=p.parse_args()
 if a.action=='verify':verify(a.evidence.resolve(),a.packet.resolve(),a.output.resolve())
 else:retain(a.evidence.resolve(),a.execution.resolve(),a.native.resolve(),a.inherited.resolve(),a.packet.resolve())
