#!/usr/bin/env python3
import argparse,subprocess
from pathlib import Path
from support import HERE,compile_cases,read,save,sha,require
from mutants import mutations

def execute(directory,log,output):
 command=['/usr/local/bin/node',str(HERE/'execute.mjs'),str(directory),str(output)]
 with log.open('w') as stream:r=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
 return r.returncode,command

def run(evidence,native,qualification,out):
 require(not out.exists(),'NO_OVERWRITE');out.mkdir(parents=True)
 require(read(native/'run.json')['status']=='PASS' and read(qualification/'summary.json')['status']=='PASS','NATIVE_QUALIFICATION')
 require((native/'proposal/files/compiler/WASM32/wasm32-backend.lisp').read_bytes()==(HERE/'wasm32-backend.lisp').read_bytes(),'NATIVE_COMPILER_JOIN')
 save(out/'native-reference.json',{'native_report_sha256':sha(native/'run.json'),'qualification_sha256':sha(qualification/'summary.json')})
 compile_cases(evidence,out/'positive');code,command=execute(out/'positive',out/'execution.log',out/'execution.json');require(code==0,'POSITIVE_WASM '+str(out/'execution.log'))
 commands=[command];controls=[];(out/'mutants').mkdir()
 for name,text in mutations((HERE/'wasm32-backend.lisp').read_text()).items():
  backend=out/'mutants'/(name+'.lisp');backend.write_text(text);directory=out/'mutants'/name;compile_cases(evidence,directory,backend)
  code,command=execute(directory,out/'mutants'/(name+'.log'),out/'mutants'/(name+'.json'));commands.append(command);log=(out/'mutants'/(name+'.log')).read_text()
  require(code!=0 and 'AssertionError' in log,'MUTANT_ORACLE '+name)
  controls.append({'name':name,'status':'REJECTED','oracle':'unchanged native/logical results, heap effects and ownership assertions','exit_code':code})
 save(out/'commands.json',commands);save(out/'controls.json',controls);target=read(out/'execution.json')
 summary={'status':'PASS','modules':target['modules'],'native_cases':len(read(out/'positive/cases.json')),'comparisons':target['comparisons'],'static_refusals':len(read(out/'positive/refusals.json')),'mutants':len(controls),'resource_refusals':target['resource_refusals'],'ownership_inspections':target['ownership_inspections'],'peak_root_frames':target['peak_root_frames'],'scope':'Generated B call core only; required arguments, ordered direct/indirect calls and full values. No LL05 slot credit; binding, APPLY, closure objects, lazy stubs and tail transfers remain.'};save(out/'summary.json',summary);print('S1-B-CALL-CORE-PASS',summary)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('evidence','native','qualification','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();run(a.evidence.resolve(),a.native.resolve(),a.qualification.resolve(),a.output.resolve())
