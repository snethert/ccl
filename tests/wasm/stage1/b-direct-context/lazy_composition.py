"""Run the pending lazy loader unchanged over the newly generated modules."""
import argparse,importlib.util,json,shutil,subprocess
from pathlib import Path
from support import HERE,read,save,require
LAZY=HERE.parent/'b-lazy-calls'

def run(positive,expected,out):
 require(not out.exists(),'NO_OVERWRITE');out.mkdir(parents=True)
 spec=importlib.util.spec_from_file_location('lazy_harness_prepare',LAZY/'prepare.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 (out/'harness.mjs').write_text(m.harness())
 for p in LAZY.glob('*.mjs'):shutil.copy(p,out/p.name)
 for name in ['installed','modules.json','cases.json','root-contracts.json']:(out/name).symlink_to(positive/name,target_is_directory=name=='installed')
 commands=[['/usr/local/bin/wat2wasm','--enable-tail-call',str(LAZY/'stub.wat'),'-o',str(out/'lazy-stub.wasm')],['/usr/local/bin/node',str(out/'catalog.mjs'),str(out),str(out/'catalog.json')],['/usr/local/bin/node',str(out/'harness.mjs'),str(out),str(out/'execution.json')]]
 save(out/'commands.json',commands)
 try:
  for i,argv in enumerate(commands):
   with (out/(str(i)+'.log')).open('w')as log:child=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=180)
   require(child.returncode==0,'LAZY_COMPOSITION '+str(out/(str(i)+'.log')))
  actual=read(out/'execution.json');want=read(expected)
  fields=['cases','tail_runs','modules','comparisons','non_tail_checks','resource_refusals','callable_checks','closure_checks','local_checks','result_capacity_checks','allocation_boundary_checks','peak_root_frames']
  for key in fields:require(actual[key]==want[key],'LAZY_COMPOSITION_ORACLE '+key)
  summary={'status':'PASS','compared_fields':fields,'comparisons':actual['comparisons'],'tail_chains':len(actual['tail_runs']),'cold_installations':[sum(e['event']=='INSTALLED'for e in r['events'])for r in actual['lazy_runs']], 'scope':'The unchanged pending lazy-loader proposal composes with the optimized compiler. The eager run additionally poisons the public table and checks internal-entry layout; those additional checks are not claimed for this inherited lazy harness.'}
  save(out/'summary.json',summary);return summary
 finally:
  for name in ['installed','modules.json','cases.json','root-contracts.json']:(out/name).unlink()

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('positive','expected','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();print(run(a.positive.resolve(),a.expected.resolve(),a.output.resolve()))
