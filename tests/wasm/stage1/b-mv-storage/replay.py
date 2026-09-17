"""Independent mutant sessions; process isolation keeps evaluator state private."""
import re,subprocess
from pathlib import Path
from support import HERE,compile_cases,require,read

def execute(directory,log,output):
 command=['/usr/local/bin/node',str(HERE/'execute.mjs'),str(directory),str(output)]
 with log.open('w') as stream:r=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=240)
 return r.returncode,command

def first_failure(log):
 match=re.search(r'AssertionError(?: \[[^\]]+\])?: (.+)',log);require(match is not None,'SEMANTIC_FAILURE');return match[1]

def run_mutant(task):
 name,text,evidence,out=task;evidence=Path(evidence);out=Path(out)
 backend=out/(name+'.lisp');backend.write_text(text);directory=out/name
 compile_cases(evidence,directory,backend)
 if name in ('intermediate-result-copy','direct-handoff-live-retired-roots'):
  from copy_cost import run
  try:run(directory,out/(name+'-cost'))
  except ValueError:pass
  else:raise AssertionError('intermediate copy regression escaped')
  log=(out/(name+'-cost/execution.log')).read_text();require(('no intermediate result copy' if name=='intermediate-result-copy' else 'handoff surviving root') in log,'COPY_MUTANT_ORACLE')
  (out/(name+'.log')).write_text(log)
  return {'name':name,'status':'REJECTED','oracle':('executed-copy count, with unchanged Lisp semantics' if name=='intermediate-result-copy' else 'root chain and descriptor identity before and after direct delivery'),'exit_code':1},read(out/(name+'-cost/command.json'))
 code,command=execute(directory,out/(name+'.log'),out/(name+'.json'))
 require(code!=0 and 'AssertionError' in (out/(name+'.log')).read_text(),'MUTANT_ORACLE '+name)
 return {'name':name,'status':'REJECTED','oracle':'unchanged native/logical results, heap effects and ownership assertions','exit_code':code},command

def verify_case(task):
 name,backend,evidence,temp,original,expected=task;temp=Path(temp);original=Path(original);evidence=Path(evidence)
 if backend is not None:
  path=temp/(name+'.lisp');path.write_text(backend)
 else:path=None
 fresh=temp/name;compile_cases(evidence,fresh,path)
 for p in original.iterdir():
  if p.suffix in ('.wat','.wasm') or p.name in ('native.json','cases.json','refusals.json','modules.json','compiler.dx64fsl','layout.json','entries.json','root-ir.json','root-contracts.json'):
   require(p.read_bytes()==(fresh/p.name).read_bytes(),'RECOMPILED_BYTES '+name+'/'+p.name)
 for p in (original/'installed').glob('*.wasm'):require(p.read_bytes()==(fresh/'installed'/p.name).read_bytes(),'INSTALLED_BYTES')
 if name in ('intermediate-result-copy','direct-handoff-live-retired-roots'):
  from copy_cost import run
  try:run(fresh,temp/(name+'-cost'))
  except ValueError:pass
  else:raise AssertionError('intermediate copy replay escaped')
  require(first_failure((temp/(name+'-cost/execution.log')).read_text())==first_failure(Path(expected).read_text()),'COPY_CONTROL_REPLAY')
  return name
 code,_=execute(fresh,temp/(name+'.log'),temp/(name+'.json'))
 if name=='positive':require(code==0 and read(temp/(name+'.json'))==read(Path(expected)),'TARGET_REPLAY')
 else:require(code!=0 and first_failure((temp/(name+'.log')).read_text())==first_failure(Path(expected).read_text()),'CONTROL_REPLAY '+name)
 return name
