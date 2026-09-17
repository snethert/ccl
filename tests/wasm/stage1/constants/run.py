#!/usr/bin/env python3
"""Execute S1-LL10-a with native, generated, persisted and inherited oracles."""
import argparse,hashlib,json,shutil,subprocess,sys,tempfile
from pathlib import Path
from compiler import generate
from compile import run as compile_run
from execute_compiled import run as execute_run
from compiler_controls import run as compiler_controls
from image_controls import run as image_controls
from inherited import run as inherited_run,prepare as inherited_prepare
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];REG=HERE.parent/'registration'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def read(p):return json.loads(p.read_text())
def require(x,why):
 if not x:raise ValueError(why)
def source_pins():
 files=[p for p in HERE.iterdir() if p.is_file() and (p.suffix in ('.py','.lisp','.mjs','.wat') or p.name=='function-layout.json')]
 for folder in (REG,HERE.parent/'b-call-errors',HERE.parent/'b-lazy-calls',HERE.parent/'architecture'):
  files += [p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
 files += [ROOT/n for n in ('doc/WASM/contracts/wasm32-layout.v1.json','doc/WASM/contracts/tcr.v1.json','doc/WASM/tools/r6_registration.py','tests/wasm/native-census/observer.lisp','tests/wasm/native-baseline/tests.lisp','tests/wasm/stage0/abi-decision/decision.json')]
 return {str(p.relative_to(ROOT)):sha(p) for p in sorted(set(files))}
def run(evidence,native,out,inherited=None):
 out.mkdir(parents=True,exist_ok=False);pins=source_pins();save(out/'source-pins.json',pins)
 for name in pins:
  q=out/'source'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy(ROOT/name,q)
 toolchain={n:{'sha256':sha(Path('/usr/local/bin')/n),'version':subprocess.check_output(['/usr/local/bin/'+n,'--version'],text=True).strip()} for n in ('node','wat2wasm')};save(out/'toolchain.json',toolchain)
 report=read(native/'run.json');require(report['status']=='PASS' and report['source_restored'] and report['restored_fasls']==164,'R6 complete')
 require((native/'proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()==generate(),'R6 compiler identity')
 save(out/'native-reference.json',{'run_sha256':sha(native/'run.json'),'backend_sha256':hashlib.sha256(generate().encode()).hexdigest(),'baseline_reused':True})
 command=[sys.executable,str(REG/'qualify.py'),'--output',str(native),'--inputs',str(evidence/'macos-u1-inputs'),'--kernel',str(evidence/'2026-09-12-native-census-r7/baseline/build/dx86cl64'),'--destination',str(out/'qualification')]
 save(out/'qualification-command.json',command)
 with (out/'qualification.log').open('w') as log:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT)
 print('R6/R6a PASS',flush=True)
 compile_run(evidence,out/'positive');execute_run(out/'positive');target=read(out/'positive/execution.json')
 require(target['status']=='PASS' and target['modules']==87 and target['native_comparisons']==233,'generated corpus complete')
 require(read(out/'positive/refusals.json')==['b-condition-generated-form','b-condition-generated-form','b-condition-assertion','b-source','pool-symbol-owner','pool-object-type'],'source refusal scope')
 compiler_controls(evidence,out/'compiler-controls');images=image_controls(out/'positive',out/'image-controls')
 supporting={}
 for name in ('verify.py','verify_pool.py','verify_snapshot.py'):
  command=[sys.executable,str(HERE/name)];result=subprocess.run(command,capture_output=True,text=True);(out/(name+'.log')).write_text(result.stdout+result.stderr)
  require(result.returncode==0,'supporting verification '+name);supporting[name]=json.loads(result.stdout)
 save(out/'supporting.json',supporting)
 if inherited:
  require(read(inherited/'summary.json')['status']=='PASS','inherited complete')
  with tempfile.TemporaryDirectory(prefix='ccl-pool-inherited-bind-') as temp:
   fresh=inherited_prepare(Path(temp)/'harness')
   for p in fresh.iterdir():require(p.read_bytes()==(inherited/'harness'/p.name).read_bytes(),'inherited exact harness '+p.name)
  shutil.copytree(inherited,out/'inherited')
 else:inherited_run(evidence,out/'inherited')
 prior=read(out/'inherited/summary.json');loader=read(out/'inherited/full-loader/summary.json')
 require(loader=={'status':'PASS','cases':36,'mutants':14},'loader qualification')
 summary={'status':'PASS','test':'S1-LL10-a','variant':'generated','review_disposition':'NOT_REVIEWED','generated_modules':87,'generated_header_probe_modules':1,'native_derived_comparisons':233,'source_refusals':6,'compiler_mutants':4,'target_image_mutants':len(images),'supporting':{k:v['status'] for k,v in supporting.items()},'placements':[1048576,2097152,2147483648],'tail_steps_per_placement':100000,'tail_stack_bytes':2048,'transport_refusals':sum(r['transport_refusals'] for r in target['restored']),'inherited':{k:{field:v[field] for field in ('modules','comparisons')} for k,v in prior.items() if k in ('corpus','conditions','call_errors')},'inherited_loader':loader,'native_qualification':read(out/'qualification/summary.json'),'scope':'Single owner Worker; 16 MiB bounded pools; no moving GC or cross-Worker snapshot atomicity. Original native expectations composed with the separately tested mutation for restored comparisons. Private condition representation and existing emitter limits unchanged.'}
 save(out/'summary.json',summary)
 save(out/'coverage.json',{'S1-LL10-a:constant-pools':{'status':'PASS','golden_representation':['supporting.json','positive/native.json','positive/execution.json','positive/header_probe.wat'],'identity_and_cycles':['positive/pools.json','positive/materialized.json','positive/execution.json','image-controls/controls.json'],'persisted_cold_constants':['positive/snapshot.json','positive/execution.json'],'compiler_and_schema':['source-pins.json','positive/proposal/unit.json','positive/compiler.dx64fsl','native-reference.json'],'controls':['compiler-controls/controls.json','image-controls/controls.json','supporting.json'],'inherited_calls_and_loader':['inherited/summary.json','inherited/full-loader/summary.json','inherited/loader-controls/summary.json']}})
 require(pins==source_pins(),'sources changed during run');print('S1-LL10-PASS',json.dumps(summary),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('evidence','native','output'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--inherited',type=Path);a=p.parse_args();run(a.evidence.resolve(),a.native.resolve(),a.output.resolve(),a.inherited.resolve() if a.inherited else None)
