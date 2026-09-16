#!/usr/bin/env python3
"""Retain a compact representation packet with references to unchanged inputs."""
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
 save(out/'development.json',{'failures':['First capture omitted native interface databases; the next used the complete pristine bootstrap archive.','Second capture had an unmatched parenthesis in the native export helper.','First JS oracle transcribed canonical T incorrectly (77854 rather than the accepted 77838); its assertion failed.','The second JS run extended a guard past the end of memory; its RangeError is retained. The final guard stops at the actual memory end.'],'scope':'No compiler defect found during these initial attempts. Original failing sources, logs and necessary binaries are retained; the final compiler mutants are in their separate archive.'})
 sources=list(HERE.glob('*'))+list(REG.glob('*.py'))+list(REG.glob('*.lisp'))+[REG/'payload/wasm32-backend.lisp',REG/'payload/xwasm32-fasload.lisp',HERE.parent/'architecture/generate.py',ROOT/'doc/WASM/tools/r6_registration.py',ROOT/'tests/wasm/native-census/observer.lisp',ROOT/'tests/wasm/native-baseline/tests.lisp',ROOT/'tests/wasm/stage0/abi-decision/decision.json',ROOT/'doc/WASM/contracts/wasm32-layout.v1.json',ROOT/'doc/WASM/contracts/tcr.v1.json']
 pins={}
 for p in sources:
  if not p.is_file():continue
  name=str(p.relative_to(ROOT));dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest);pins[name]=sha(p)
 save(out/'source-pins.json',pins)
 shutil.copy(ROOT/'tests/wasm/stage0/abi-decision/decision.json',out/'abi-decision.json')
 layout=read(ROOT/'doc/WASM/contracts/wasm32-layout.v1.json');cons=next(x for x in layout['objects'] if x['name']=='cons');constants={r['name']:r['value'] for r in layout['constants']}
 require((cons['tag_value'],cons['alignment'],cons['size_bytes'])==(1,8,8),'CONS_SCHEMA')
 require([(c['name'],c['raw_offset'],c['tagged_displacement']) for c in cons['cells']]==[('cdr',0,-1),('car',4,3)],'CONS_CELLS')
 expected={'canonical-nil-value':77825,'canonical-t-value':77838,'fulltagmask':7,'fulltag-cons':1,'fixnumshift':2,'target-most-negative-fixnum':-536870912,'target-most-positive-fixnum':536870911};require(all(constants[k]==v for k,v in expected.items()),'CONSTANT_SCHEMA')
 tcr=read(ROOT/'doc/WASM/contracts/tcr.v1.json');fields={f['name']:f for f in tcr['fields']};require(all((fields[n]['offset'],fields[n]['width'])==(off,4) for n,off in [('vsp',64),('mv_count',116),('mv_base',120)]),'TCR_SCHEMA')
 save(out/'coverage.json',{'cons':cons,'constants':expected,'tcr_fields':{n:fields[n] for n in ('vsp','mv_count','mv_base')},'probes':'153 native/logical graphs x four placements; 128 independent raw-tag probes; bytewise field/result/guard comparisons; 15 compiler mutants. Unused schema descriptions are not claimed.','stores':{'cons.car':'tagged heap field; collector/barrier obligation remains','cons.cdr':'tagged heap field; collector/barrier obligation remains','caller result word':'tagged stack root','TCR.mv_count':'raw metadata'}})
 save(out/'exception-boundary.json',{'import':'env.type_error','kind':'Wasm exception tag','parameters':['datum:i32','expected_kind:i32'],'expected_kinds':{'1':'LIST','2':'CONS'},'scope':'Typed failure boundary only; construction/signalling of Lisp condition objects and handler/restart semantics remain 1C.'})
 tools={}
 for n in ('node','wat2wasm'):
  path=Path('/usr/local/bin')/n;tools[n]={'path':str(path),'sha256':sha(path),'version':subprocess.check_output([str(path),'--version'],text=True).strip()}
 save(out/'toolchain.json',tools);save(out/'options.json',{'profile':'full','workers':1,'memory_pages':32769,'flags':['--enable-threads','--enable-exceptions'],'target':'wasm32','no_target_bootstrap_heap':True})
 manifest(out)

def manifest(out):
 save(out/'packet.json',{'id':'STAGE1-REPRESENTATION-R1','scope':'S1-LL04-a generated cons representation; NOT_REVIEWED, not integrated.','files':[{'path':str(p.relative_to(out)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.rglob('*')) if p.is_file() and p.name!='packet.json']})

def publish(evidence,packet):
 require('S1-LL04-VERIFIED' in (packet/'verified.log').read_text(),'FRESH_VERIFIER')
 invpath=ROOT/'doc/WASM/stage1/inventory.json';inventory=read(invpath);test=next(t for t in inventory['tests'] if t['id']=='S1-LL04-a');require(test['status']=='EXECUTED' and test['runner']=='tests/wasm/stage1/representation/run.py','REGISTERED_RUNNER')
 shutil.copy(invpath,packet/'inventory.json');name=packet.name
 artifacts=[]
 refs={r['path']:r for r in read(packet/'references.json')}
 def artifact(path,role):
  if path in refs:artifacts.append({'path':refs[path]['evidence_path'],'sha256':refs[path]['sha256'],'role':role})
  else:artifacts.append({'path':name+'/'+path,'sha256':sha(packet/path),'role':role})
 for path,role in [('source-pins.json','implementation'),('positive/cases.json','test'),('positive/native.json','log'),('positive/compiler.dx64fsl','compiler'),('coverage.json','schema'),('exception-boundary.json','schema'),('abi-decision.json','abi'),('options.json','options'),('toolchain.json','host-compiler'),('execution.json','log'),('controls.json','log'),('mutants.tar.gz','test'),('references.json','log'),('verified.log','log'),('native-reference.json','log'),('native/run.json','log'),('native/proposal/unit.json','implementation'),('native/compile-ccl-comparison.json','log'),('native/systems-comparison.json','log'),('qualification/verification.json','log'),('qualification/summary.json','log')]:artifact(path,role)
 for path in read(packet/'source-pins.json'):artifact('source/'+path,'implementation')
 for p in sorted((packet/'positive').glob('*.lisp')):
  if p.name!='cases.lisp':artifact('positive/'+p.name,'source')
 for suffix,role in [('wat','template'),('wasm','module')]:
  for p in sorted((packet/'positive').glob('*.'+suffix)):artifact('positive/'+p.name,role)
 for p in sorted((packet/'positive/installed').glob('*.wasm')):artifact('positive/installed/'+p.name,'installed-binary')
 artifacts.append({'path':'2026-09-16-stage1-1a-r2/native/baseline.image','sha256':sha(evidence/'2026-09-16-stage1-1a-r2/native/baseline.image'),'role':'image'})
 row={'id':test['id'],'variant':'generated','source_revision':inventory['source_revision'],'evidence_kind':test['evidence_kind'],'status':'PASS','review_disposition':'NOT_REVIEWED','test_revision':sha(packet/'source-pins.json'),'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seed':100000,'command':'representation/native.py, registration/qualify.py, representation/run.py, representation/verify.py; exact child commands retained','toolchain':read(packet/'toolchain.json'),'engine':read(packet/'toolchain.json')['node'],'configuration':read(packet/'summary.json'),'skips':[],'substitutions':[],'assertions':[{'id':a['id'],'status':'PASS'} for a in test['assertions']],'artifacts':artifacts}
 report=bind_report({'version':1,'source_revision':inventory['source_revision'],'inventory_sha256':sha(invpath),'results':[row]},inventory,name+'/inventory.json',sha(invpath));out=evidence/(name+'-results.json');require(not out.exists(),'NO_OVERWRITE');save(out,report)
 # Omissions operate on the genuine generated record, with PASS unchanged.
 import copy
 controls=[]
 for role in sorted(set(inventory['required_record_roles']+test['required_record_roles'])):
  damaged=copy.deepcopy(report);damaged['results'][0]['artifacts']=[a for a in row['artifacts'] if a['role']!=role]
  status,reasons=assess(inventory,damaged,sha(invpath),evidence);require(status=='FAIL' and 'missing artifact roles: S1-LL04-a [generated]' in reasons,'ROLE_CONTROL '+role);controls.append({'removed_role':role,'status':'REJECTED','diagnostic':'missing artifact roles: S1-LL04-a [generated]'})
 save(packet/'role-controls.json',controls);manifest(packet);print('Published',out,'with',len(controls),'role omissions refused')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['assemble','publish']);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--packet',type=Path,required=True)
 for n in ('run','native','qualification'):p.add_argument('--'+n,type=Path)
 p.add_argument('--development',type=Path,nargs='*',default=[]);a=p.parse_args()
 if a.mode=='assemble':assemble(a.evidence.resolve(),a.run.resolve(),a.native.resolve(),a.qualification.resolve(),a.packet.resolve(),a.development)
 else:publish(a.evidence.resolve(),a.packet.resolve())
