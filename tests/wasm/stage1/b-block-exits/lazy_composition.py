"""Compose the proposed exit-tag loader policy with generated nonlocal exits."""
import argparse,importlib.util,json,shutil,subprocess
from pathlib import Path
from support import HERE,read,save,require
LAZY=HERE.parent/'b-lazy-calls'

def run(positive,expected,out):
 require(not out.exists(),'NO_OVERWRITE');out.mkdir(parents=True)
 spec=importlib.util.spec_from_file_location('lazy_harness_prepare',LAZY/'prepare.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 harness=m.harness()
 harness=harness.replace("const call_error=new WebAssembly.Tag", "const nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});\nconst call_error=new WebAssembly.Tag")
 harness=harness.replace('tail_table,call_error,','tail_table,call_error,nonlocal_exit,').replace('call_error,type_error}', 'call_error,type_error,nonlocal_exit}')
 harness=harness.replace('[1,4,5].includes(code)','[1,4,5,8].includes(code)').replace("code===5?'TYPE':'DESIGNATOR'", "code===5?'TYPE':code===8?'CONTROL':'DESIGNATOR'")
 from harness_setup import adapt
 harness=adapt(harness)
 (out/'harness.mjs').write_text(harness)
 for name in ('loader.mjs','binary.mjs','catalog.mjs'):shutil.copy(HERE/name,out/name)
 for name in ['installed','modules.json','cases.json','root-contracts.json']:(out/name).symlink_to(positive/name,target_is_directory=name=='installed')
 commands=[['/usr/local/bin/wat2wasm','--enable-tail-call',str(HERE/'stub.wat'),'-o',str(out/'lazy-stub.wasm')],['/usr/local/bin/node',str(out/'catalog.mjs'),str(out),str(out/'catalog.json')],['/usr/local/bin/node',str(out/'harness.mjs'),str(out),str(out/'execution.json')]]
 save(out/'commands.json',commands)
 try:
  for i,argv in enumerate(commands):
   with (out/(str(i)+'.log')).open('w')as log:child=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=180)
   require(child.returncode==0,'LAZY_COMPOSITION '+str(out/(str(i)+'.log')))
  actual=read(out/'execution.json');want=read(expected)
  fields=['cases','tail_runs','modules','comparisons','non_tail_checks','resource_refusals','callable_checks','closure_checks','local_checks','result_capacity_checks','allocation_boundary_checks','peak_root_frames']
  for key in fields:require(actual[key]==want[key],'LAZY_COMPOSITION_ORACLE '+key)
  summary={'status':'PASS','compared_fields':fields,'comparisons':actual['comparisons'],'tail_chains':len(actual['tail_runs']),'cold_installations':[sum(e['event']=='INSTALLED'for e in r['events'])for r in actual['lazy_runs']], 'scope':'The reviewed loader with the control-kind profile bump composes with generated lexical exits. The eager run additionally poisons the public table and checks internal-entry layout; those additional checks are not claimed for this inherited lazy harness.'}
  save(out/'summary.json',summary);return summary
 finally:
  for name in ['installed','modules.json','cases.json','root-contracts.json']:(out/name).unlink()

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('positive','expected','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();print(run(a.positive.resolve(),a.expected.resolve(),a.output.resolve()))
