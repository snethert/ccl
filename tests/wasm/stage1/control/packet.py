#!/usr/bin/env python3
"""One LL19 packet: exact proposal, native R6, execution and independent replay."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from backend import generate
from assessment import run as assess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];REG=HERE.parent/'registration'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(x,why):
 if not x:raise ValueError(why)
def command(argv,log):
 save(log.with_suffix('.command.json'),list(map(str,argv)))
 with log.open('w') as f:subprocess.run(list(map(str,argv)),check=True,stdout=f,stderr=subprocess.STDOUT)
def archive(out,rows):
 with tarfile.open(out,'w:gz') as t:
  for path,name in rows:t.add(path,arcname=name,recursive=False)
def files(directory):return [p for p in sorted(directory.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and not p.is_symlink()]
def pins():
 sys.path.insert(0,str(HERE.parent/'constants'))
 spec=importlib.util.spec_from_file_location('ll19_constants_pins',HERE.parent/'constants/run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 result=m.source_pins();sys.path.pop(0)
 for folder in (HERE,HERE.parent/'b-apply-errors',HERE.parent/'b-repeated-keywords'):
  for p in folder.iterdir():
   if p.is_file():result[str(p.relative_to(ROOT))]=sha(p)
 for name in ('compiler/X86/X8632/x8632-arch.lisp','lib/macros.lisp','level-1/l1-error-signal.lisp','level-1/l1-error-system.lisp','level-1/l1-readloop.lisp','level-1/l1-clos-boot.lisp'):
  p=ROOT/name
  result[name]=sha(p)
 return dict(sorted(result.items()))
def qualify(evidence,native,out):
 need((native/'proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()==generate(),'native compiler identity')
 command([sys.executable,REG/'qualify.py','--output',native,'--inputs',evidence/'macos-u1-inputs','--kernel',evidence/'2026-09-12-native-census-r7/baseline/build/dx86cl64','--destination',out],out.with_suffix('.log'))
def manifest(out):
 save(out/'packet.json',dict(id='STAGE1-CONTROL-R1',review_disposition='NOT_REVIEWED',files=[dict(path=str(p.relative_to(out)),bytes=p.stat().st_size,sha256=sha(p)) for p in files(out) if p.name!='packet.json']))
def coverage():
 return {'S1-LL19-a:generated-eh':{
  'status':'PASS',
  'nested_cleanup_and_replacement':['execution/positive/compiled/cases.json:o_nested,o_replace','execution/positive/execution.json','control/observations.mjs','inherited/execution.json'],
  'binding_roots_VSP_TSP_CSP':['control/observations.mjs','execution/resources/observations.json','execution/controls.json:control-stack-retirement,reserve-not-rearmed'],
  'complete_values_and_no_post_exit_effect':['execution/positive/compiled/native.json:r_many_error,r_zero_error,o_nested,e_early','execution/positive/execution.json','assessment/assessment.json'],
  'type_bounds_arity_unbound_with_restarts':['execution/positive/compiled/native.json:r_basic,r_bounds,r_arity,r_unbound','execution/positive/execution.json'],
  'structured_early_fatal':['execution/positive/execution.json:fatal_diagnostics','assessment/controls.json'],
  'production_bootstrap_instances':['execution/positive/compiled/native-condition-classes.json','inherited/conditions/execution.json:condition_refusals','scope.json:class_boundary'],
  'debugger_and_restart_lifetime':['execution/positive/compiled/native.json:d_type,d_nested,d_mask,r_expired','execution/controls.json'],
  'soft_exhaustion_and_interrupt_masking':['execution/resources/cases.json','execution/resources/observations.json','execution/controls.json'],
  'R6_R6a':['native-references.json','native.tar.gz','qualification/summary.json'],
  'loader':['inherited/full-loader/summary.json','inherited/loader-controls/summary.json','inherited/lazy/summary.json','inherited/condition-lazy/summary.json','inherited/error-lazy/summary.json'],
  'locator_rule':'execution/ and inherited/ are paths within the corresponding retained tar files; control/ names the source fixture directory.'}}
def development(out):
 rows=[];attempts=[]
 # Original failed executions and their actual generated inputs, without
 # duplicating every successful baseline or all earlier mutant binaries.
 directories=sorted(Path('/tmp').glob('ccl-control-r[0-9]*'))+sorted(Path('/tmp').glob('ccl-control-inherited-r[0-9]*'))+sorted(Path('/tmp').glob('ccl-control-resources-r[0-9]*'))
 for d in directories:
  if not d.is_dir() or (d/'summary.json').exists() or d.name.endswith('r8'):continue
  keep=[]
  for p in files(d):
   rel=p.relative_to(d)
   if p.suffix=='.log' or (len(rel.parts)==1 and p.suffix in ('.json','.lisp')) or (rel.parts[0]=='harness' and len(rel.parts)==2 and p.suffix in ('.py','.mjs','.lisp','.json')) or p.name in ('cases.json','native.json','refusals.json','execution.json','compiler.dx64fsl'):
    rows.append((p,d.name+'/'+str(rel)));keep.append(str(rel))
  if keep:attempts.append(dict(attempt=d.name,files=len(keep),scope='Original logs, generated compiler/harness and native case/oracle artifacts; complete duplicate baseline/module trees omitted.'))
 for p in sorted(Path('/tmp').glob('control-*-failure.py'))+sorted(Path('/tmp').glob('control-run-unterminated.py')):
  rows.append((p,'pre-execution/'+p.name))
 for p in (Path('/tmp/ccl-control-inherited-r7/full-loader/debug.mjs'),Path('/tmp/ccl-control-loader-final.log'),Path('/tmp/ccl-control-retain-first.log')):
  if p.exists():rows.append((p,'loader-debug/'+p.name))
 archive(out/'development.tar.gz',rows)
 save(out/'development.json',dict(attempts=attempts,notes=[
  'Early restart/front-end and debugger-source iterations failed on missing private-special admission, Lisp parentheses and unsupported source declarations; original generated inputs retained.',
  'Condition registry header was initially 3066 instead of 3322 for twelve entries. The genuine run rejected it; corrected before qualification.',
  'The soft-limit guard used reserve AND boolean and missed aligned nonzero reserves. Replaced by a nonzero predicate; retained as the soft-limit-disabled mutant.',
  'Native CCL reports an out-of-bounds fixnum SVREF as SIMPLE-ERROR, an improper APPLY with the whole list datum, and a nonfunction with (OR SYMBOL FUNCTION). Literal oracles were corrected from actual retained native answers; target readers now match.',
  'A debugger-hook abort can be superseded by a cleanup transfer. The inherited native oracle left its error status after normal completion; it now resets RETURN after APPLY completes. The original o_replace mismatch remains retained.',
  'Inherited requalification caught overly broad quoted-symbol admission, changed temporary-stack hard error code, a changed legacy cons exception tag, and the now-obsolete restart-case refusal. Admission was narrowed; accepted tags/codes preserved; the refusal replaced by positive restart cases and explicit option/association refusals.',
  'The lazy owner queried compiled.values on its deferred adapter, then installation controls omitted new condition imports. These are harness-owner adaptations; loader algorithm unchanged except the profile identifier.',
  'Native R6 runs r1/r2 were successful intermediate proposals, superseded by final r3 after compiler changes. They are not the qualification for this packet. Successful incremental r24-r27 controls are not duplicated wholesale; final executed sources and artifacts are retained.'
 ]))
def retain(evidence,execution,native,inherited,out):
 need(not out.exists(),'never overwrite packet')
 for d in (execution,native,inherited):need(read(d/('run.json' if d==native else 'summary.json'))['status']=='PASS','complete '+str(d))
 for p in (execution/'wasm32-backend.lisp',native/'proposal/files/compiler/WASM32/wasm32-backend.lisp',inherited/'harness/wasm32-backend.lisp'):
  need(p.read_text()==generate(),'compiler join '+str(p))
 out.mkdir();source=pins();save(out/'source-pins.json',source)
 archive(out/'source.tar.gz',[(ROOT/n,n) for n in source])
 (out/'wasm32-backend.lisp').write_text(generate());shutil.copy(HERE/'scope.json',out/'scope.json')
 assessed=assess(execution,out/'assessment');qualify(evidence,native,out/'qualification')
 for name,d in [('execution',execution),('inherited',inherited)]:archive(out/(name+'.tar.gz'),[(p,str(p.relative_to(d))) for p in files(d)])
 # Real binary files are separately addressable for the gate's role bindings.
 for p in files(execution/'positive/compiled'):
  if p.suffix in ('.wasm','.wat','.lisp','.dx64fsl') or p.name in ('cases.json','native.json','modules.json','native-condition-classes.json','root-ir.json','root-contracts.json','refusals.json'):
   dest=out/'positive'/p.relative_to(execution/'positive/compiled');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest)
 prior=evidence/'2026-09-16-stage1-1a-r2';known={r['sha256']:str((prior/r['path']).relative_to(evidence)) for r in read(prior/'packet.json')['files']}
 refs=[];rows=[]
 for p in files(native):
  h=sha(p);name=str(p.relative_to(native))
  if h in known:refs.append(dict(path=name,sha256=h,evidence_path=known[h]))
  else:rows.append((p,name))
 archive(out/'native.tar.gz',rows);save(out/'native-references.json',refs)
 save(out/'toolchain.json',{n:dict(sha256=sha(Path('/usr/local/bin')/n),version=subprocess.check_output(['/usr/local/bin/'+n,'--version'],text=True).strip()) for n in ('node','wat2wasm')})
 save(out/'options.json',dict(wat2wasm=['--enable-threads','--enable-exceptions','--enable-tail-call'],node_flags=[],profile=read(HERE/'scope.json')['profile'],owner_workers=1,native_baseline='macOS x86-64 U1',seed=100000))
 abi=ROOT/'tests/wasm/stage0/abi-decision/decision.json';shutil.copy(abi,out/'abi-decision.json')
 save(out/'abi-binding.json',dict(decision_locator=str(abi.relative_to(ROOT)),sha256=sha(abi),protocol='B',scope='Public B entry preserved; reviewed internal-entry/continuation protocol extended only by checked condition services.'))
 inherited_summary=read(inherited/'summary.json');loader=read(inherited/'full-loader/summary.json')
 need(loader==dict(status='PASS',cases=36,mutants=14),'full loader qualification')
 summary=dict(assessed,test='S1-LL19-a',review_disposition='NOT_REVIEWED',generated_modules=read(execution/'summary.json')['modules'],native_qualification=read(out/'qualification/summary.json'),inherited={k:{f:v[f] for f in ('modules','comparisons')} for k,v in inherited_summary.items() if k in ('corpus','conditions','call_errors')},loader=loader,scope=read(HERE/'scope.json'))
 save(out/'summary.json',summary);save(out/'coverage.json',coverage());development(out)
 need(source==pins(),'source changed during retention');manifest(out);print('LL19 retained',json.dumps({k:v for k,v in summary.items() if k not in ('scope','native_qualification')}))
def verify(evidence,packet,out):
 out.mkdir(parents=True,exist_ok=False)
 for r in read(packet/'packet.json')['files']:
  p=(packet/r['path']).resolve();need(p.is_relative_to(packet.resolve()) and sha(p)==r['sha256'],'packet '+r['path'])
 source=read(packet/'source-pins.json');need(source==pins(),'executed source pins')
 need((packet/'wasm32-backend.lisp').read_text()==generate(),'proposal derivation')
 native=out/'native';native.mkdir()
 with tarfile.open(packet/'native.tar.gz') as t:t.extractall(native,filter='data')
 for r in read(packet/'native-references.json'):
  src=(evidence/r['evidence_path']).resolve();dest=(native/r['path']).resolve()
  need(src.is_relative_to(evidence) and dest.is_relative_to(native) and not dest.exists() and sha(src)==r['sha256'],'native reference')
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(src,dest)
 qualify(evidence,native,out/'qualification')
 command([sys.executable,HERE/'run.py','--evidence',evidence,'--output',out/'execution','--qualify'],out/'execution.log')
 assess(out/'execution',out/'assessment')
 command([sys.executable,HERE/'inherited.py','--evidence',evidence,'--output',out/'inherited'],out/'inherited.log')
 compared=0
 for name in ('execution','inherited'):
  with tarfile.open(packet/(name+'.tar.gz')) as t:
   for member in t.getmembers():
    p=Path(member.name)
    if p.suffix in ('.wasm','.wat','.dx64fsl') or p.name in ('summary.json','controls.json','native.json','native-condition-classes.json','refusals.json','cases.json','execution.json','observations.json'):
     need(t.extractfile(member).read()==(out/name/member.name).read_bytes(),'replay '+name+'/'+member.name);compared+=1
 for name in ('assessment.json','controls.json'):need((packet/'assessment'/name).read_bytes()==(out/'assessment'/name).read_bytes(),'assessment replay')
 need(source==pins(),'sources changed during replay')
 result=dict(status='PASS',deterministic_files=compared,source_pins=len(source),packet_sha256=sha(packet/'packet.json'),native_qualification=read(out/'qualification/summary.json'))
 save(out/'verification.json',result);print('S1-LL19-VERIFIED',json.dumps(result))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['retain','verify']);p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');p.add_argument('--output',type=Path,required=True)
 for n in ('run','native','inherited','packet'):p.add_argument('--'+n,type=Path)
 a=p.parse_args()
 if a.mode=='retain':retain(a.evidence.resolve(),a.run.resolve(),a.native.resolve(),a.inherited.resolve(),a.output.resolve())
 else:verify(a.evidence.resolve(),a.packet.resolve(),a.output.resolve())
