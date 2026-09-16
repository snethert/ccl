#!/usr/bin/env python3
"""Retain one compact, non-gating B call-core proposal and its R6 evidence."""
import argparse,json,shutil,tarfile,subprocess
from pathlib import Path
from support import HERE,ROOT,REG,read,save,sha,require

def manifest(out):
 save(out/'packet.json',{'id':'STAGE1-B-RESULTS-R1','scope':'Generated runtime result capacity, without the fixed 64-value ceiling; auxiliary execution, no LL05 gate credit, not integrated.','files':[{'path':str(p.relative_to(out)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.rglob('*')) if p.is_file() and p.name!='packet.json']})
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
 save(out/'development.json',{'failures':['The scratch-offset mutant initially escaped: the corpus did not observe an established bound variable after a large discarded result overwrote its slot. The retained mutant source, modules, passing observation and driver failure preserve this coverage gap; The first added case still left two spare words in its budget and escaped; its run is also retained. bound_after_full fills the reservation exactly and rejects the mutant. The proposed compiler was unchanged.'],'superseded':'Positive development compiles and mutant trials were superseded by the finalized producer and retained verifier.'})
 sources=[p for p in HERE.iterdir() if p.is_file()]+list(REG.glob('*.py'))+list(REG.glob('*.lisp'))+[REG/'payload/wasm32-backend.lisp',REG/'payload/xwasm32-fasload.lisp',HERE.parent/'architecture/generate.py',HERE.parent/'b-rest-apply/wasm32-backend.lisp',ROOT/'doc/WASM/tools/r6_registration.py',ROOT/'tests/wasm/native-census/observer.lisp',ROOT/'tests/wasm/native-baseline/tests.lisp',ROOT/'tests/wasm/stage0/abi-decision/decision.json',ROOT/'doc/WASM/contracts/wasm32-layout.v1.json',ROOT/'doc/WASM/contracts/tcr.v1.json']
 pins={}
 for p in sources:
  name=str(p.relative_to(ROOT));dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest);pins[name]=sha(p)
 save(out/'source-pins.json',pins);shutil.copy(ROOT/'tests/wasm/stage0/abi-decision/decision.json',out/'abi-decision.json')
 tools={}
 for name in ('node','wat2wasm'):
  p=Path('/usr/local/bin')/name;tools[name]={'path':str(p),'sha256':sha(p),'version':subprocess.check_output([str(p),'--version'],text=True).strip()}
 save(out/'toolchain.json',tools);save(out/'scope.json',{'accepted_slots_unchanged':True,'inventory_entries_executed':[],'maximum_arguments':'Runtime stack/heap extent; fixed source terms also subject to the existing bounded source-reader budget. Executed through 1024 arguments.','maximum_values':'Runtime caller-owned output reservation, propagated as a resource budget; positive tests return 1024 values. No automatic growth. Minimum four scratch words permit scalar evaluation with an empty final reservation.','entry_frame_bytes':'align16(8 + max(16, owner - output) + 4 * bound_variable_slots)', 'keyword_identities':'explicit fixture-supplied imports, no production namespace or symbol layout claim','root_record':'previous:u32, count:u32, tagged words','stores':{'arguments and retained values':'tagged root slots','result words':'TCR descriptor ownership','frame links and counts':'raw metadata','cons writes':'tagged heap fields; initialized before allocation pointer and bound rest root publication; no polling/collection path'},'remaining':['collection and allocator slow path','dynamic reservation growth and capacity policy at production adapters','closure/function objects','full Lisp condition path','lazy stubs and role-authenticated installation','tail chains and cleanup/binding extent','live-local spill/reload under collection']});manifest(out)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('evidence','run','native','qualification','output'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--development',type=Path,nargs='*',default=[]);a=p.parse_args();retain(a.evidence.resolve(),a.run.resolve(),a.native.resolve(),a.qualification.resolve(),a.output.resolve(),a.development)
