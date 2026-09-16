#!/usr/bin/env python3
"""Retain one compact, non-gating B call-core proposal and its R6 evidence."""
import argparse,json,shutil,tarfile,subprocess
from pathlib import Path
from support import HERE,ROOT,REG,read,save,sha,require

def manifest(out):
 save(out/'packet.json',{'id':'STAGE1-B-BINDINGS-R1','scope':'Generated optional and keyword argument binding; auxiliary execution, no LL05 gate credit, not integrated.','files':[{'path':str(p.relative_to(out)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.rglob('*')) if p.is_file() and p.name!='packet.json']})
def retain(evidence,run,native,qualification,out,development):
 require(not out.exists(),'NO_OVERWRITE');require(read(run/'summary.json')['status']=='PASS','COMPLETE');out.mkdir(parents=True)
 for p in run.iterdir():
  if p.name=='mutants':continue
  if p.is_dir():shutil.copytree(p,out/p.name)
  else:shutil.copy(p,out/p.name)
 with tarfile.open(out/'mutants.tar.gz','w:gz') as t:
  for p in sorted((run/'mutants').rglob('*')):
   if p.is_file():t.add(p,arcname=str(p.relative_to(run/'mutants')))
 lookup={x['sha256']:'2026-09-16-stage1-1a-r2/'+x['path'] for x in read(evidence/'2026-09-16-stage1-1a-r2/packet.json')['files']};refs=[]
 for name,directory in [('native',native),('qualification',qualification)]:
  for p in sorted(directory.rglob('*')):
   if not p.is_file():continue
   h=sha(p);dest=name+'/'+str(p.relative_to(directory))
   if h in lookup:refs.append({'path':dest,'sha256':h,'evidence_path':lookup[h]})
   else:q=out/dest;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,q)
 save(out/'references.json',refs)
 with tarfile.open(out/'development.tar.gz','w:gz') as t:
  for directory in development:
   for p in sorted(directory.rglob('*')):
    if p.is_file():t.add(p,arcname=directory.name+'/'+str(p.relative_to(directory)))
 save(out/'development.json',{'failures':['Development attempts 1 and 2: missing closing parentheses in the new Lisp emitter, refused by the native reader.','Development attempt 3: missing closing parenthesis in the emitted keyword scan, refused by WABT.','Development attempt 4: exploratory Python import selected registration/run.py instead of this fixture; no compiler ran. The original log is retained.'],'superseded':'Initial positive and mutant runs passed, but final inspection found that lowercase import names could conflate distinct escaped keyword spellings. The unpublished packet was withdrawn; the compiler now refuses unsupported spellings and the new source refusals cover both literal and parameter forms. Fresh R6/R6a and all controls were rerun. An exploratory direct-image probe failed before reaching the compiler (nonexecutable retained kernel, then backend package absent); the available logs and explicit stderr-retention limitation are retained as harness failures. A separate normal-driver replay of the former compiler fails the new escaped-keyword refusal assertion and is retained as the regression witness.'})
 sources=[p for p in HERE.iterdir() if p.is_file()]+list(REG.glob('*.py'))+list(REG.glob('*.lisp'))+[REG/'payload/wasm32-backend.lisp',REG/'payload/xwasm32-fasload.lisp',HERE.parent/'architecture/generate.py',HERE.parent/'b-calls/wasm32-backend.lisp',ROOT/'doc/WASM/tools/r6_registration.py',ROOT/'tests/wasm/native-census/observer.lisp',ROOT/'tests/wasm/native-baseline/tests.lisp',ROOT/'tests/wasm/stage0/abi-decision/decision.json',ROOT/'doc/WASM/contracts/wasm32-layout.v1.json',ROOT/'doc/WASM/contracts/tcr.v1.json']
 pins={}
 for p in sources:
  name=str(p.relative_to(ROOT));dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest);pins[name]=sha(p)
 save(out/'source-pins.json',pins);shutil.copy(ROOT/'tests/wasm/stage0/abi-decision/decision.json',out/'abi-decision.json')
 tools={}
 for name in ('node','wat2wasm'):
  p=Path('/usr/local/bin')/name;tools[name]={'path':str(p),'sha256':sha(p),'version':subprocess.check_output([str(p),'--version'],text=True).strip()}
 save(out/'toolchain.json',tools);save(out/'scope.json',{'accepted_slots_unchanged':True,'inventory_entries_executed':[],'maximum_arguments':64,'maximum_values':64,'entry_frame_bytes':'align16(264 + 4 * bound_variable_slots)', 'keyword_identities':'explicit fixture-supplied imports, no production namespace or symbol layout claim','root_record':'previous:u32, count:u32, tagged words','stores':{'arguments and retained values':'tagged root slots','result words':'TCR descriptor ownership','frame links and counts':'raw metadata','cons writes':'tagged heap fields; no collecting/safepoint path yet'},'remaining':['rest binding and allocation','APPLY validation','closure/function objects','full Lisp condition path','lazy stubs and role-authenticated installation','tail chains and cleanup/binding extent','live-local spill/reload under collection']});manifest(out)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('evidence','run','native','qualification','output'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--development',type=Path,nargs='*',default=[]);a=p.parse_args();retain(a.evidence.resolve(),a.run.resolve(),a.native.resolve(),a.qualification.resolve(),a.output.resolve(),a.development)
