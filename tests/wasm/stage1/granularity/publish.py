"""Bind LL21-b only after retained replay; exercise every artifact-role omission."""
import argparse,copy,datetime,shutil,sys
from pathlib import Path
from packet import ROOT,read,save,sha,manifest
sys.path.insert(0,str(ROOT/'doc/WASM/tools'))
from evidence_binding import bind_report
from gate import assess
TEST='S1-LL21-b'
def role_controls(e,inventory,report,inventory_hash):
 t=next(t for t in inventory['tests'] if t['id']==TEST);rows=[]
 for role in sorted(set(inventory['required_record_roles']+t['required_record_roles'])):
  bad=copy.deepcopy(report);bad['results'][0]['artifacts']=[a for a in bad['results'][0]['artifacts'] if a['role']!=role]
  status,reasons=assess(inventory,bad,inventory_hash,e);diagnostic='missing artifact roles: S1-LL21-b [granularity]'
  assert status=='FAIL' and diagnostic in reasons,(role,reasons)
  rows.append(dict(role=role,status='REJECTED',diagnostic=diagnostic))
 return rows
def publish(e,p):
 assert read(p/'verification.json')['status']=='PASS'
 invpath=ROOT/'doc/WASM/stage1/inventory.json';inventory=read(invpath);t=next(t for t in inventory['tests'] if t['id']==TEST)
 assert t['status']=='EXECUTED' and t['runner']=='tests/wasm/stage1/granularity/run.py'
 shutil.copy(invpath,p/'inventory.json');artifacts=[]
 def add(f,role):artifacts.append(dict(path=str(f.relative_to(e)),sha256=sha(f),role=role))
 for n,role in [('source-pins.json','implementation'),('sources.tar.gz','source'),('scope.json','schema'),('coverage.json','schema'),('abi-decision.json','abi'),('abi-binding.json','abi'),('toolchain.json','host-compiler'),('benchmark-policy.json','options'),('summary.json','log'),('verification.json','log'),('execution/faults.json','test'),('assessment.json','log'),('publication-controls.json','test'),('measurement-check.json','log')]:add(p/n,role)
 for f in sorted((p/'execution').rglob('*')):
  if not f.is_file():continue
  parts=f.relative_to(p/'execution').parts
  if f.suffix=='.wasm' and parts[0] in ['full','precompiled_callback'] and len(parts)==2:role='installed-binary'
  else:role={'.wasm':'module','.wat':'template','.dx64fsl':'compiler'}.get(f.suffix,'test')
  add(f,role)
 summary=read(p/'summary.json');assert summary['status']=='PASS';toolchain=read(p/'toolchain.json')
 row=dict(id=TEST,variant='granularity',source_revision=inventory['source_revision'],evidence_kind=t['evidence_kind'],status='PASS',review_disposition='NOT_REVIEWED',test_revision=sha(p/'source-pins.json'),timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),seed='DETERMINISTIC',command='granularity/run.py; packet.py verify (exact subprocess commands retained)',toolchain=toolchain,engine=next(r['version'] for r in toolchain['tools'] if r['path'].endswith('/node')),configuration=summary,skips=[],substitutions=[],assertions=[dict(id=a['id'],status='PASS') for a in t['assertions']],artifacts=artifacts)
 report=bind_report(dict(version=1,source_revision=inventory['source_revision'],inventory_sha256=sha(invpath),results=[row]),inventory,p.name+'/inventory.json',sha(invpath))
 dest=e/(p.name+'-results.json');assert not dest.exists();save(dest,report)
 save(p/'role-controls.json',role_controls(e,inventory,report,sha(invpath)));manifest(p)
 print(TEST,'published NOT_REVIEWED')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True);v=a.parse_args();publish(v.evidence.resolve(),v.packet.resolve())
