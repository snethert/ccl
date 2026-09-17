#!/usr/bin/env python3
"""Retain one compact, non-gating B call-core proposal and its R6 evidence."""
import argparse,json,shutil,tarfile,subprocess
from pathlib import Path
from support import HERE,ROOT,REG,read,save,sha,require

def manifest(out):
 save(out/'packet.json',{'id':'STAGE1-B-RESULT-SCRATCH-R1','scope':'Per-callee proven-small result scratch with dynamic delivery preserved; isolated derivative of conditions R2, no inventory credit or integration.','files':[{'path':str(p.relative_to(out)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.rglob('*')) if p.is_file() and p.name!='packet.json']})
def retain(evidence,run,native,qualification,out,development):
 require(not out.exists(),'NO_OVERWRITE');require(read(run/'summary.json')['status']=='PASS','COMPLETE');out.mkdir(parents=True)
 for p in run.iterdir():
  if p.name in ('mutants','condition-controls'):continue
  if p.is_dir():shutil.copytree(p,out/p.name)
  else:shutil.copy(p,out/p.name)
 with tarfile.open(out/'mutants.tar.gz','w:gz') as t:
  for p in sorted((run/'mutants').rglob('*')):
   if p.is_file():t.add(p,arcname=str(p.relative_to(run/'mutants')))
 with tarfile.open(out/'condition-controls.tar.gz','w:gz') as t:
  for p in sorted((run/'condition-controls').rglob('*')):
   if p.is_file():t.add(p,arcname=str(p.relative_to(run/'condition-controls')))
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
 sources+=[HERE.parent/'b-catch-throw/wasm32-backend.lisp',ROOT/'compiler/X86/x862.lisp',ROOT/'compiler/nx-basic.lisp',HERE.parent/'b-unwind-protect/wasm32-backend.lisp',HERE.parent/'b-direct-context/mutants.py',ROOT/'compiler/nx1.lisp',ROOT/'lib/macros.lisp',ROOT/'level-1/l1-readloop.lisp']
 sources += [ROOT/'level-1/l1-readloop-lds.lisp',ROOT/'level-1/l1-error-signal.lisp',ROOT/'compiler/nx2.lisp',ROOT/'level-0/l0-symbol.lisp',ROOT/'library/lispequ.lisp',HERE.parent/'b-special-bindings/wasm32-backend.lisp']
 sources += [HERE.parent/'b-dynamic-bindings/wasm32-backend.lisp']
 sources += [HERE.parent/'b-block-exits'/name for name in ('loader.mjs','binary.mjs','stub.wat')]
 sources+=list((HERE.parent/'b-lazy-calls').glob('*.mjs'))+[HERE.parent/'b-lazy-calls/prepare.py',HERE.parent/'b-lazy-calls/stub.wat']
 pins={}
 for p in sources:
  name=str(p.relative_to(ROOT));dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest);pins[name]=sha(p)
 save(out/'source-pins.json',pins);shutil.copy(ROOT/'tests/wasm/stage0/abi-decision/decision.json',out/'abi-decision.json')
 tools={}
 for name in ('node','wat2wasm'):
  p=Path('/usr/local/bin')/name;tools[name]={'path':str(p),'sha256':sha(p),'version':subprocess.check_output([str(p),'--version'],text=True).strip()}
 save(out/'toolchain.json',tools);save(out/'scope.json',read(HERE/'scope.json'))
 # Reuse byte-identical reviewed payloads, especially the inherited corpus.
 # Source snapshots remain local so pins can be checked before hydration.
 known={}
 for predecessor in ('2026-09-17-stage1-b-mv-storage-r2','2026-09-17-stage1-b-conditions-r1','2026-09-17-stage1-b-conditions-r2'):
  known.update({row['sha256']:predecessor+'/'+row['path'] for row in read(evidence/predecessor/'packet.json')['files']})
 for p in sorted(out.rglob('*')):
  if not p.is_file():continue
  rel=str(p.relative_to(out))
  if rel.startswith('source/') or rel in ('references.json','source-pins.json','scope.json'):continue
  h=sha(p)
  if h in known:
   refs.append(dict(path=rel,sha256=h,evidence_path=known[h]));p.unlink()
 save(out/'references.json',refs);manifest(out)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('evidence','run','native','qualification','output'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--development',type=Path,nargs='*',default=[]);a=p.parse_args();retain(a.evidence.resolve(),a.run.resolve(),a.native.resolve(),a.qualification.resolve(),a.output.resolve(),a.development)
