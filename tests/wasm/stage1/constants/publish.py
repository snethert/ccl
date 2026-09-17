#!/usr/bin/env python3
"""Publish LL10 only after execution, retention and a fresh complete replay."""
import argparse,copy,datetime,shutil,sys
from pathlib import Path
from run import ROOT,read,save,sha,require
from retain import manifest
sys.path.insert(0,str(ROOT/'doc/WASM/tools'))
from evidence_binding import bind_report
from gate import assess

def publish(evidence,packet):
 require('S1-LL10-VERIFIED' in (packet/'verified.log').read_text(),'REPLAY_REQUIRED')
 invpath=ROOT/'doc/WASM/stage1/inventory.json';inventory=read(invpath);test=next(t for t in inventory['tests'] if t['id']=='S1-LL10-a')
 require(test['status']=='EXECUTED' and test['runner']=='tests/wasm/stage1/constants/run.py','RUNNER')
 shutil.copy(invpath,packet/'inventory.json');name=packet.name;artifacts=[]
 def artifact(path,role):artifacts.append({'path':name+'/'+path,'role':role,'sha256':sha(packet/path)})
 for path,role in [('source-pins.json','implementation'),('source/tests/wasm/stage1/constants/compile.lisp','source'),('source/tests/wasm/stage1/constants/function-layout.json','schema'),('source/tests/wasm/stage0/abi-decision/decision.json','abi'),('toolchain.json','host-compiler'),('coverage.json','schema'),('summary.json','options'),('summary.json','log'),('verified.log','log'),('compiler-controls.tar.gz','test'),('image-controls.tar.gz','test'),('inherited.tar.gz','test'),('supporting.json','test'),('native-reference.json','log'),('native/run.json','log'),('qualification/summary.json','log'),('positive/compiler.dx64fsl','compiler'),('positive/native.json','log'),('positive/snapshot.json','image'),('positive/execution.json','log')]:artifact(path,role)
 for path in read(packet/'source-pins.json'):artifact('source/'+path,'implementation')
 installed=packet/'installed';installed.mkdir(exist_ok=False)
 for p in sorted((packet/'positive').glob('*.wat')):
  artifact('positive/'+p.name,'template');binary=p.with_suffix('.wasm');artifact('positive/'+binary.name,'module');shutil.copy(binary,installed/binary.name);artifact('installed/'+binary.name,'installed-binary')
 row={'id':'S1-LL10-a','variant':'generated','source_revision':inventory['source_revision'],'evidence_kind':test['evidence_kind'],'status':'PASS','review_disposition':'NOT_REVIEWED','test_revision':sha(packet/'source-pins.json'),'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seed':100000,'command':'constants/native.py; constants/run.py; constants/verify_ll10.py; exact native commands retained','toolchain':read(packet/'toolchain.json'),'engine':read(packet/'toolchain.json')['node'],'configuration':read(packet/'summary.json'),'skips':[],'substitutions':[],'assertions':[{'id':a['id'],'status':'PASS'} for a in test['assertions']],'artifacts':artifacts}
 report=bind_report({'version':1,'source_revision':inventory['source_revision'],'inventory_sha256':sha(invpath),'results':[row]},inventory,name+'/inventory.json',sha(invpath))
 status,reasons=assess(inventory,report,sha(invpath),evidence)
 require(status=='BLOCKED' and 'unreviewed S1-LL10-a [generated]' in reasons and all(r.startswith('missing ') or r.startswith('unreviewed ') or r.startswith('prerequisite ') for r in reasons),'POSITIVE_GATE '+repr((status,reasons)))
 result=evidence/(name+'-results.json');require(not result.exists(),'NO_OVERWRITE');save(result,report)
 controls=[]
 for role in sorted(set(inventory['required_record_roles']+test['required_record_roles'])):
  damaged=copy.deepcopy(report);damaged['results'][0]['artifacts']=[a for a in artifacts if a['role']!=role]
  status,reasons=assess(inventory,damaged,sha(invpath),evidence);diagnostic='missing artifact roles: S1-LL10-a [generated]'
  require(status=='FAIL' and diagnostic in reasons,'ROLE_OMISSION '+role);controls.append({'role':role,'status':'REJECTED','diagnostic':diagnostic})
 save(packet/'role-controls.json',controls);manifest(packet);print('S1-LL10-PUBLISHED pending review;',len(controls),'role omissions rejected')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--packet',type=Path,required=True);a=p.parse_args();publish(a.evidence.resolve(),a.packet.resolve())
