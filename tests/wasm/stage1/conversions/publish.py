#!/usr/bin/env python3
"""Retain a compact conversions packet with references to unchanged inputs."""
import argparse,datetime,shutil,subprocess,sys,tarfile
from pathlib import Path
from support import HERE,ROOT,REG,read,save,sha,require
sys.path.insert(0,str(ROOT/'doc/WASM/tools'))
from evidence_binding import bind_report
from gate import assess

def assemble(evidence,run,native,qualification,out,development):
 require(not out.exists(),'NO_OVERWRITE');out.mkdir(parents=True)
 require(read(run/'summary.json')['status']=='PASS','COMPLETED_RUN')
 for p in run.iterdir():
  if p.name=='mutants':continue
  if p.is_dir():shutil.copytree(p,out/p.name)
  else:shutil.copy(p,out/p.name)
 with tarfile.open(out/'mutants.tar.gz','w:gz') as t:
  for p in sorted((run/'mutants').rglob('*')):
   if p.is_file():t.add(p,arcname=str(p.relative_to(run/'mutants')))
 lookup={r['sha256']:'2026-09-16-stage1-1a-r2/'+r['path'] for r in read(evidence/'2026-09-16-stage1-1a-r2/packet.json')['files']};refs=[]
 for dirname,source in [('native',native),('qualification',qualification)]:
  for p in sorted(source.rglob('*')):
   if not p.is_file():continue
   name=dirname+'/'+str(p.relative_to(source));h=sha(p)
   if h in lookup:refs.append({'path':name,'sha256':h,'evidence_path':lookup[h]})
   else:dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest)
 save(out/'references.json',refs)
 if development:
  with tarfile.open(out/'development.tar.gz','w:gz') as t:
   for directory in development:
    for p in sorted(directory.rglob('*')):
     if p.is_file():t.add(p,arcname=directory.name+'/'+str(p.relative_to(directory)))
 save(out/'development.json',{'failures':['The first compile assumed register arguments in acode CALL; with B the actual arguments are the stack list. Corrected the IR decoder, with its original source and log retained.','The first mutation run exposed a missing exact-2^32 address-sum case: the overflow-limit mutant escaped. Added displacement +2 at pointer 0xfffffffe; the original failed run is retained.','The first native-reference session compiled its sparse-memory binding before DEFVAR had been loaded, leaving it lexical. Moved the declaration before the form.'],'superseded':'Other development captures succeeded and were replaced by the finalized corpus, controls and sources. No original failing bytes were reconstructed.'})
 sources=[p for p in HERE.iterdir() if p.is_file()]+list(REG.glob('*.py'))+list(REG.glob('*.lisp'))+[REG/'payload/wasm32-backend.lisp',REG/'payload/xwasm32-fasload.lisp',HERE.parent/'architecture/generate.py',ROOT/'doc/WASM/tools/r6_registration.py',ROOT/'tests/wasm/native-census/observer.lisp',ROOT/'tests/wasm/native-baseline/tests.lisp',ROOT/'tests/wasm/stage0/abi-decision/decision.json',ROOT/'doc/WASM/contracts/wasm32-layout.v1.json',ROOT/'doc/WASM/contracts/tcr.v1.json',ROOT/'level-0/l0-init.lisp',HERE.parent/'representation/wasm32-backend.lisp']
 pins={}
 for p in sources:
  name=str(p.relative_to(ROOT));dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest);pins[name]=sha(p)
 save(out/'source-pins.json',pins)
 shutil.copy(ROOT/'tests/wasm/stage0/abi-decision/decision.json',out/'abi-decision.json')
 layout=read(ROOT/'doc/WASM/contracts/wasm32-layout.v1.json');constants={r['name']:r['value'] for r in layout['constants']}
 expected={'fixnumshift':2,'fixnummask':3,'target-most-negative-fixnum':-536870912,'target-most-positive-fixnum':536870911,'fulltag-misc':6,'misc-header-offset':-6,'nbits-in-word':32,'num-subtag-bits':8}
 require(all(constants[k]==v for k,v in expected.items()),'LAYOUT_SCHEMA')
 require('#.(expt 2 (- target::nbits-in-word target::num-subtag-bits))' in (ROOT/'level-0/l0-init.lisp').read_text(),'ARRAY_LIMIT_DERIVATION')
 save(out/'coverage.json',{'constants':expected,'array_total_size_limit':2**(constants['nbits-in-word']-constants['num-subtag-bits']),'array_limit_kind':'exclusive','probes':'Every admitted conversion uses actual frontend IR and pass 2. Real header loads below/above 2 GiB and at the memory end; synthetic near-4-GiB conversions are never dereferenced. Array boundaries use arithmetic, not allocation.','stores':{'ID registry next':'raw monotonic counter, no tagged heap store'},'registry_scope':'Single-owner explicit registry passed by address. Code IDs are validated by issuance; no reclamation. Slot signature/role metadata supplied by its trusted owner; this slice validates handles and actual table capacity/presence, not loader metadata authenticity.'})
 save(out/'exception-boundary.json',{'import':'env.conversion_error','parameters':['reason:i32'],'scope':'Checked internal primitive refusal; full Lisp condition objects and signalling remain 1C. No result or registry write on refusal.'})
 shutil.copy(HERE/'abi.json',out/'abi.json')
 tools={}
 for n in ('node','wat2wasm'):
  path=Path('/usr/local/bin')/n;tools[n]={'path':str(path),'sha256':sha(path),'version':subprocess.check_output([str(path),'--version'],text=True).strip()}
 save(out/'toolchain.json',tools);save(out/'options.json',{'profile':'full','workers':1,'memory_pages':32769,'flags':['--enable-threads','--enable-exceptions'],'target':'wasm32','no_target_bootstrap_heap':True})
 manifest(out)

def manifest(out):
 save(out/'packet.json',{'id':'STAGE1-CONVERSIONS-R1','scope':'S1-LL07-a generated typed conversions; NOT_REVIEWED, not integrated.','files':[{'path':str(p.relative_to(out)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.rglob('*')) if p.is_file() and p.name!='packet.json']})

def publish(evidence,packet):
 require('S1-LL07-VERIFIED' in (packet/'verified.log').read_text(),'FRESH_VERIFIER')
 invpath=ROOT/'doc/WASM/stage1/inventory.json';inventory=read(invpath);test=next(t for t in inventory['tests'] if t['id']=='S1-LL07-a');require(test['status']=='EXECUTED' and test['runner']=='tests/wasm/stage1/conversions/run.py','REGISTERED_RUNNER')
 shutil.copy(invpath,packet/'inventory.json');name=packet.name
 artifacts=[]
 refs={r['path']:r for r in read(packet/'references.json')}
 def artifact(path,role):
  if path in refs:artifacts.append({'path':refs[path]['evidence_path'],'sha256':refs[path]['sha256'],'role':role})
  else:artifacts.append({'path':name+'/'+path,'sha256':sha(packet/path),'role':role})
 for path,role in [('source-pins.json','implementation'),('positive/cases.json','test'),('positive/native.json','log'),('positive/compiler.dx64fsl','compiler'),('coverage.json','schema'),('abi.json','abi'),('positive/refusals.json','log'),('exception-boundary.json','schema'),('abi-decision.json','abi'),('options.json','options'),('toolchain.json','host-compiler'),('execution.json','log'),('controls.json','log'),('mutants.tar.gz','test'),('references.json','log'),('verified.log','log'),('native-reference.json','log'),('native/run.json','log'),('native/proposal/unit.json','implementation'),('native/compile-ccl-comparison.json','log'),('native/systems-comparison.json','log'),('qualification/verification.json','log'),('qualification/summary.json','log')]:artifact(path,role)
 for path in read(packet/'source-pins.json'):artifact('source/'+path,'implementation')
 for p in sorted((packet/'positive').glob('*.lisp')):
  if p.name!='cases.lisp':artifact('positive/'+p.name,'source')
 for suffix,role in [('wat','template'),('wasm','module')]:
  for p in sorted((packet/'positive').glob('*.'+suffix)):artifact('positive/'+p.name,role)
 for p in sorted((packet/'positive/installed').glob('*.wasm')):artifact('positive/installed/'+p.name,'installed-binary')
 artifacts.append({'path':'2026-09-16-stage1-1a-r2/native/baseline.image','sha256':sha(evidence/'2026-09-16-stage1-1a-r2/native/baseline.image'),'role':'image'})
 row={'id':test['id'],'variant':'generated','source_revision':inventory['source_revision'],'evidence_kind':test['evidence_kind'],'status':'PASS','review_disposition':'NOT_REVIEWED','test_revision':sha(packet/'source-pins.json'),'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seed':100000,'command':'conversions/native.py, registration/qualify.py, conversions/run.py, conversions/verify.py; exact child commands retained','toolchain':read(packet/'toolchain.json'),'engine':read(packet/'toolchain.json')['node'],'configuration':read(packet/'summary.json'),'skips':[],'substitutions':[],'assertions':[{'id':a['id'],'status':'PASS'} for a in test['assertions']],'artifacts':artifacts}
 report=bind_report({'version':1,'source_revision':inventory['source_revision'],'inventory_sha256':sha(invpath),'results':[row]},inventory,name+'/inventory.json',sha(invpath));out=evidence/(name+'-results.json');require(not out.exists(),'NO_OVERWRITE');save(out,report)
 # Omissions operate on the genuine generated record, with PASS unchanged.
 import copy
 controls=[]
 for role in sorted(set(inventory['required_record_roles']+test['required_record_roles'])):
  damaged=copy.deepcopy(report);damaged['results'][0]['artifacts']=[a for a in row['artifacts'] if a['role']!=role]
  status,reasons=assess(inventory,damaged,sha(invpath),evidence);require(status=='FAIL' and 'missing artifact roles: S1-LL07-a [generated]' in reasons,'ROLE_CONTROL '+role);controls.append({'removed_role':role,'status':'REJECTED','diagnostic':'missing artifact roles: S1-LL07-a [generated]'})
 save(packet/'role-controls.json',controls);manifest(packet);print('Published',out,'with',len(controls),'role omissions refused')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['assemble','publish']);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--packet',type=Path,required=True)
 for n in ('run','native','qualification'):p.add_argument('--'+n,type=Path)
 p.add_argument('--development',type=Path,nargs='*',default=[]);a=p.parse_args()
 if a.mode=='assemble':assemble(a.evidence.resolve(),a.run.resolve(),a.native.resolve(),a.qualification.resolve(),a.packet.resolve(),a.development)
 else:publish(a.evidence.resolve(),a.packet.resolve())
