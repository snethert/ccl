"""Publish LL18-b only after a full retained replay, with production role refusals."""
import argparse,copy,datetime,shutil,sys
from pathlib import Path
from packet import ROOT,read,save,sha,manifest
def need(ok,why):
 if not ok:raise ValueError(why)
sys.path.insert(0,str(ROOT/'doc/WASM/tools'))
from evidence_binding import bind_report
from gate import assess
TEST='S1-LL18-b'
def role_controls(e,inventory,report,inventory_hash):
 t=next(t for t in inventory['tests'] if t['id']==TEST);controls=[]
 for role in sorted(set(inventory['required_record_roles']+t['required_record_roles'])):
  damaged=copy.deepcopy(report);r=damaged['results'][0];r['artifacts']=[a for a in r['artifacts'] if a['role']!=role]
  status,reasons=assess(inventory,damaged,inventory_hash,e);diagnostic='missing artifact roles: S1-LL18-b [hash-tables]'
  need(status=='FAIL' and diagnostic in reasons,'role omission '+role);controls.append(dict(role=role,status='REJECTED',diagnostic=diagnostic))
 return controls

def publish(e,p):
 need(read(p/'verification.json')['status']=='PASS','fresh replay');invpath=ROOT/'doc/WASM/stage1/inventory.json';inventory=read(invpath)
 t=next(t for t in inventory['tests'] if t['id']==TEST);need(t['status']=='EXECUTED' and t['runner']=='tests/wasm/stage1/hash-tables/run.py','registered runner')
 shutil.copy(invpath,p/'inventory.json');artifacts=[]
 def add(f,role):artifacts.append(dict(path=str(f.relative_to(e)),sha256=sha(f),role=role))
 for n,role in [('source-pins.json','implementation'),('sources.tar.gz','source'),('wasm32-backend.lisp','implementation'),('hash.c','source'),('collector.c','source'),('adapter.wat','template'),('scope.json','schema'),('coverage.json','schema'),('abi-decision.json','abi'),('abi-binding.json','abi'),('toolchain.json','host-compiler'),('options.json','options'),('summary.json','log'),('verification.json','log'),('controls.json','test'),('assessment.json','log'),('publication-controls.json','test'),('native-reuse.json','log')]:add(p/n,role)
 for f in sorted((p/'execution').rglob('*')):
  if not f.is_file():continue
  if f.parent.name=='installed':role='installed-binary'
  else:role={'.wasm':'module','.wat':'template','.dx64fsl':'compiler'}.get(f.suffix,'test')
  add(f,role)
 toolchain=read(p/'toolchain.json');summary=read(p/'summary.json');need(summary['status']=='PASS','qualified result')
 row=dict(id=TEST,variant='hash-tables',source_revision=inventory['source_revision'],evidence_kind=t['evidence_kind'],status='PASS',review_disposition='NOT_REVIEWED',test_revision=sha(p/'source-pins.json'),timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),seed=395,command='hash-tables/run.py; packet.py verify (all subprocess commands retained)',toolchain=toolchain,engine=next(r['version'] for r in toolchain['tools'] if r['path'].endswith('/node')),configuration=summary,skips=[],substitutions=[],assertions=[dict(id=a['id'],status='PASS') for a in t['assertions']],artifacts=artifacts)
 report=bind_report(dict(version=1,source_revision=inventory['source_revision'],inventory_sha256=sha(invpath),results=[row]),inventory,p.name+'/inventory.json',sha(invpath))
 dest=e/(p.name+'-results.json');need(not dest.exists(),'never overwrite envelope');save(dest,report)
 controls=role_controls(e,inventory,report,sha(invpath));save(p/'role-controls.json',controls);manifest(p);print(TEST,'published NOT_REVIEWED;',len(controls),'role omissions rejected')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--packet',type=Path,required=True);v=a.parse_args();publish(v.evidence.resolve(),v.packet.resolve())
