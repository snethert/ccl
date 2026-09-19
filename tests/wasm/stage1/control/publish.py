#!/usr/bin/env python3
"""Bind LL19 only after execution, R6 and a fresh complete retained replay."""
import argparse,copy,datetime,shutil,sys
from pathlib import Path
from packet import ROOT,read,save,sha,need,manifest
sys.path.insert(0,str(ROOT/'doc/WASM/tools'))
from evidence_binding import bind_report
from gate import assess

def publish(evidence,packet):
 need(read(packet/'verification.json')['status']=='PASS','fresh retained replay')
 invpath=ROOT/'doc/WASM/stage1/inventory.json';inventory=read(invpath)
 t=next(t for t in inventory['tests'] if t['id']=='S1-LL19-a')
 need(t['status']=='EXECUTED' and t['runner']=='tests/wasm/stage1/control/qualify.py','registered runner')
 summary=read(packet/'summary.json');need(summary['status']=='PASS','complete qualification')
 shutil.copy(invpath,packet/'inventory.json');artifacts=[]
 def artifact(p,role):artifacts.append(dict(path=str(p.relative_to(evidence)),sha256=sha(p),role=role))
 for name,role in [('source-pins.json','implementation'),('source.tar.gz','source'),('wasm32-backend.lisp','implementation'),('scope.json','schema'),('coverage.json','schema'),('abi-decision.json','abi'),('abi-binding.json','abi'),('toolchain.json','host-compiler'),('options.json','options'),('summary.json','log'),('verification.json','log'),('assessment/controls.json','test'),('assessment/assessment.json','log'),('execution.tar.gz','test'),('inherited.tar.gz','test'),('native.tar.gz','log'),('native-references.json','log'),('qualification/summary.json','log'),('qualification/verification.json','log')]:artifact(packet/name,role)
 for p in sorted((packet/'positive').rglob('*')):
  if not p.is_file():continue
  if p.suffix=='.wasm':role='installed-binary' if p.parent.name=='installed' else 'module'
  elif p.suffix=='.wat':role='template'
  elif p.suffix=='.dx64fsl':role='compiler'
  elif p.suffix=='.lisp':role='source'
  else:role='test' if p.name in ('cases.json','refusals.json') else 'schema' if p.name in ('modules.json','root-contracts.json','root-ir.json','native-condition-classes.json') else 'log'
  artifact(p,role)
 toolchain=read(packet/'toolchain.json')
 row=dict(id=t['id'],variant='generated',source_revision=inventory['source_revision'],evidence_kind=t['evidence_kind'],status='PASS',review_disposition='NOT_REVIEWED',test_revision=sha(packet/'source-pins.json'),timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),seed=100000,command='control/native.py; control/qualify.py (component commands retained); control/packet.py verify',toolchain=toolchain,engine=toolchain['node'],configuration=summary,skips=[],substitutions=[],assertions=[dict(id=a['id'],status='PASS') for a in t['assertions']],artifacts=artifacts)
 report=bind_report(dict(version=1,source_revision=inventory['source_revision'],inventory_sha256=sha(invpath),results=[row]),inventory,packet.name+'/inventory.json',sha(invpath))
 dest=evidence/(packet.name+'-results.json');need(not dest.exists(),'never overwrite envelope');save(dest,report)
 controls=[]
 for role in sorted(set(inventory['required_record_roles']+t['required_record_roles'])):
  damaged=copy.deepcopy(report);damaged['results'][0]['artifacts']=[a for a in artifacts if a['role']!=role]
  status,reasons=assess(inventory,damaged,sha(invpath),evidence)
  diagnostic='missing artifact roles: S1-LL19-a [generated]'
  need(status=='FAIL' and diagnostic in reasons,'role omission '+role)
  controls.append(dict(role=role,status='REJECTED',diagnostic=diagnostic))
 save(packet/'role-controls.json',controls);manifest(packet)
 print('S1-LL19-a published NOT_REVIEWED;',len(controls),'role omissions rejected')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--packet',type=Path,required=True);a=p.parse_args();publish(a.evidence.resolve(),a.packet.resolve())
