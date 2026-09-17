#!/usr/bin/env python3
"""Publish the two LL05 records only after qualified execution and retained replay."""
import argparse,datetime,copy,shutil,sys
from pathlib import Path
from support import ROOT,read,save,sha,require
sys.path.insert(0,str(ROOT/'doc/WASM/tools'))
from evidence_binding import bind_report
from gate import assess
from retain import manifest
IDS=('S1-LL05-a','S1-LL05-b')
def publish(evidence,packet):
 require('S1-LL05-VERIFIED' in (packet/'verified.log').read_text(),'FRESH_REPLAY')
 invpath=ROOT/'doc/WASM/stage1/inventory.json';inventory=read(invpath)
 tests=[next(t for t in inventory['tests'] if t['id']==id) for id in IDS]
 for t in tests:require(t['status']=='EXECUTED' and t['runner']=='tests/wasm/stage1/b-call-errors/run.py','REGISTERED_RUNNER')
 require(read(packet/'summary.json')['status']=='PASS','COMPLETE_EXECUTION')
 shutil.copy(invpath,packet/'inventory.json')
 name=packet.name;refs={r['path']:r for r in read(packet/'references.json')};artifacts=[]
 toolchain=read(evidence/refs['toolchain.json']['evidence_path']) if 'toolchain.json' in refs else read(packet/'toolchain.json')
 def artifact(path,role):
  if path in refs:r=refs[path];artifacts.append(dict(path=r['evidence_path'],sha256=r['sha256'],role=role))
  else:artifacts.append(dict(path=name+'/'+path,sha256=sha(packet/path),role=role))
 for path,role in [('source-pins.json','implementation'),('scope.json','schema'),('abi-decision.json','abi'),('abi-binding.json','abi'),('coverage.json','schema'),('options.json','options'),('toolchain.json','host-compiler'),('summary.json','log'),('verified.log','log'),('controls.json','test'),('mutants.tar.gz','test'),('condition-controls.tar.gz','test'),('error-controls.tar.gz','test'),('full-loader.tar.gz','test'),('native-reference.json','log'),('references.json','log'),('native/run.json','log'),('qualification/summary.json','log'),('qualification/verification.json','log')]:artifact(path,role)
 for path in read(packet/'source-pins.json'):artifact('source/'+path,'implementation')
 for prefix in ('positive','conditions/compiled','call-errors/compiled'):
  for path,role in [('cases.json','test'),('native.json','log'),('compiler.dx64fsl','compiler'),('root-ir.json','schema'),('root-contracts.json','schema')]:artifact(prefix+'/'+path,role)
  modules=read(packet/prefix/'modules.json') if (packet/prefix/'modules.json').exists() else read(evidence/refs[prefix+'/modules.json']['evidence_path'])
  for m in modules:
   n=m['name']
   if 'source' in m:artifact(prefix+'/'+n+'.lisp','source')
   for suffix,role in [('.wat','template'),('.wasm','module')]:artifact(prefix+'/'+n+suffix,role)
   artifact(prefix+'/installed/'+n+'.wasm','installed-binary')
 for path in ('execution.json','conditions/execution.json','call-errors/execution.json','lazy-composition/summary.json','condition-lazy/summary.json','call-error-lazy/summary.json'):artifact(path,'log')
 artifacts.append(dict(path='2026-09-16-stage1-1a-r2/native/baseline.image',sha256=sha(evidence/'2026-09-16-stage1-1a-r2/native/baseline.image'),role='image'))
 rows=[]
 for t in tests:
  rows.append(dict(id=t['id'],variant='generated:B',source_revision=inventory['source_revision'],evidence_kind=t['evidence_kind'],status='PASS',review_disposition='NOT_REVIEWED',test_revision=sha(packet/'source-pins.json'),timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),seed=100000,command='b-call-errors/native.py; registration/qualify.py; b-call-errors/run.py; b-call-errors/verify.py; exact child commands retained',toolchain=toolchain,engine=toolchain['node'],configuration=read(packet/'summary.json'),skips=[],substitutions=[],assertions=[dict(id=a['id'],status='PASS') for a in t['assertions']],artifacts=artifacts))
 report=bind_report(dict(version=1,source_revision=inventory['source_revision'],inventory_sha256=sha(invpath),results=rows),inventory,name+'/inventory.json',sha(invpath))
 result=evidence/(name+'-results.json');require(not result.exists(),'NO_OVERWRITE');save(result,report)
 controls=[]
 for i,t in enumerate(tests):
  for role in sorted(set(inventory['required_record_roles']+t['required_record_roles'])):
   damaged=copy.deepcopy(report);damaged['results'][i]['artifacts']=[a for a in artifacts if a['role']!=role]
   status,reasons=assess(inventory,damaged,sha(invpath),evidence)
   diagnostic='missing artifact roles: '+t['id']+' [generated:B]'
   require(status=='FAIL' and diagnostic in reasons,'ROLE_OMISSION '+role)
   controls.append(dict(test=t['id'],role=role,status='REJECTED',diagnostic=diagnostic))
 save(packet/'role-controls.json',controls);manifest(packet)
 print('Published LL05-a/b, pending review;',len(controls),'artifact-role omissions rejected')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--packet',type=Path,required=True);a=p.parse_args();publish(a.evidence.resolve(),a.packet.resolve())
