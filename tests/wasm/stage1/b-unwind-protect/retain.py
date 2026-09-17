#!/usr/bin/env python3
"""Retain one compact, non-gating B call-core proposal and its R6 evidence."""
import argparse,json,shutil,tarfile,subprocess
from pathlib import Path
from support import HERE,ROOT,REG,read,save,sha,require

def manifest(out):
 save(out/'packet.json',{'id':'STAGE1-B-UNWIND-PROTECT-R1','scope':'Generated UNWIND-PROTECT: normal multiple-value retention, cleanup checkpoint restoration and exception replacement; auxiliary execution, no LL05/LL19 gate credit, not integrated.','files':[{'path':str(p.relative_to(out)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.rglob('*')) if p.is_file() and p.name!='packet.json']})
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
 save(out/'development.json',read(HERE/'development.json'))
 sources=[p for p in HERE.iterdir() if p.is_file()]+list(REG.glob('*.py'))+list(REG.glob('*.lisp'))+[REG/'payload/wasm32-backend.lisp',REG/'payload/xwasm32-fasload.lisp',HERE.parent/'architecture/generate.py',HERE.parent/'b-direct-context/wasm32-backend.lisp',HERE.parent/'b-tail-calls/mutants.py',HERE.parent/'b-tail-calls/execute.mjs',ROOT/'doc/WASM/tools/r6_registration.py',ROOT/'tests/wasm/native-census/observer.lisp',ROOT/'tests/wasm/native-baseline/tests.lisp',ROOT/'tests/wasm/stage0/abi-decision/decision.json',ROOT/'doc/WASM/contracts/wasm32-layout.v1.json',ROOT/'doc/WASM/contracts/tcr.v1.json']
 sources+=[HERE.parent/'b-direct-context/mutants.py',ROOT/'compiler/nx1.lisp',ROOT/'lib/macros.lisp',ROOT/'level-1/l1-readloop.lisp']
 sources+=list((HERE.parent/'b-lazy-calls').glob('*.mjs'))+[HERE.parent/'b-lazy-calls/prepare.py',HERE.parent/'b-lazy-calls/stub.wat']
 pins={}
 for p in sources:
  name=str(p.relative_to(ROOT));dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest);pins[name]=sha(p)
 save(out/'source-pins.json',pins);shutil.copy(ROOT/'tests/wasm/stage0/abi-decision/decision.json',out/'abi-decision.json')
 tools={}
 for name in ('node','wat2wasm'):
  p=Path('/usr/local/bin')/name;tools[name]={'path':str(p),'sha256':sha(p),'version':subprocess.check_output([str(p),'--version'],text=True).strip()}
 save(out/'toolchain.json',tools);save(out/'scope.json',{'accepted_slots_unchanged':True,'inventory_entries_executed':[],'maximum_arguments':'Runtime stack/heap extent; fixed source terms also subject to the existing bounded source-reader budget. Executed through 1024 arguments.','maximum_values':'Runtime caller-owned output reservation, propagated as a resource budget; positive tests return 1024 values. No automatic growth. Minimum four scratch words permit scalar evaluation with an empty final reservation.','unwind_protect':{'retention_bytes':'align16(8 + 4*capacity) reserved before entering the extent','checkpoint':'explicit stack top, root head, VSP, MV base/owner/count restored before exceptional cleanup','values':'runtime count and tagged retention slots survive normal cleanup','tail_legality':'protected form and cleanup execute without tail transfer; their callees may tail transfer','exceptions':'same exnref rethrown unless cleanup raises another; exception payload relocation under GC remains open'},'compiled_call_improvement':'No extra argument-vector copy or public wrapper activation. Caller reserves results before the continuation and writes final argument slots. APPLY prefix staging remains. Public boundaries retain their wrapper.', 'entry_frame_bytes':'48 + align16(4*nargs) + optional temporary callable + align16(8 + max(16, owner-output) + 4*bound_variable_slots); one continuation per ordinary call, reused by tail transfers', 'callable_objects':'Immediately applied literal callables use nonescaping stack storage and are relocated with their environments on tail transfer. Escaping functions retain heap storage. Generated 24-byte logical function objects; D1 simple-vector environments of shared D1 cons cells. Static top-level objects and code registry remain fixture-materialized; registry metadata is owner-supplied, not loader-authenticated. Captured cells are conservatively allocated on function entry, once per captured local binding per activation; untaken LET branches may retain unused cells.','keyword_identities':'explicit fixture-supplied imports, no production namespace or symbol layout claim','root_record':'previous:u32, count:u32, tagged words; count independently derived from pre-emitter IR by a lexical-ancestor analysis','stores':{'arguments and retained values':'tagged root slots','result words':'TCR descriptor ownership','frame links and counts':'raw metadata','cons writes':'tagged heap fields, including mutable capture-cell CARs; no polling/collection path','closure objects and environments':'tagged heap fields; complete extent checked before writes and allocation pointer publication; captured cell identity is shared across siblings' },'remaining':['collection and allocator slow path','dynamic reservation growth and capacity policy at production adapters','local RETURN-FROM, declarations and local macros','condition class construction, signalling and handler dispatch','CATCH/THROW, local RETURN-FROM and dynamic special binding','TCR handler/control-stack publication and unwind-state integration','live-local spill/reload under collection']});manifest(out)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('evidence','run','native','qualification','output'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--development',type=Path,nargs='*',default=[]);a=p.parse_args();retain(a.evidence.resolve(),a.run.resolve(),a.native.resolve(),a.qualification.resolve(),a.output.resolve(),a.development)
