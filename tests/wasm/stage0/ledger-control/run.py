#!/usr/bin/env python3
"""S0-LL24-a: check a real project snapshot and reject damaged ledger inputs."""
import argparse
import copy
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];DOCS=ROOT/'doc/WASM';TOOLS=DOCS/'tools'
sys.path.insert(0,str(TOOLS));from evidence_binding import bind_report,contract_hash
spec=importlib.util.spec_from_file_location('project_ledger',TOOLS/'check-project-ledger.py');ledger=importlib.util.module_from_spec(spec);spec.loader.exec_module(ledger)
ID='S0-LL24-a'
SCOPE='Production ledger and decision metadata: one current authority/status projection, explicit criterion-change records, preservation of 35 accepted records, evidence identity/class and unresolved work. Does not authenticate human authorization, infer truth of prose or revalidate accepted runtime payloads.'
SNAPSHOTS=['stage0/ledger-policy.json','stage0/inventory.json','evidence/current-stage0-gate-result.json','evidence/index.json','evidence/repository.json','STATUS.md','history/changes.md']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def data(x):return (json.dumps(x,indent=2,ensure_ascii=False)+'\n').encode()
def save(p,x):p.write_bytes(data(x))
def require(x,why):
    if not x:raise ValueError(why)
def sources():return [HERE/'run.py',HERE/'inputs.json',TOOLS/'check-project-ledger.py',TOOLS/'evidence_binding.py',TOOLS/'gate.py',DOCS/'stage0/ledger-policy.json']

def exercise(snapshot,evidence):
    base=ledger.Inputs(snapshot,evidence);positive=ledger.assess(base)
    require(positive['status']=='PASS' and positive['project_gate']=='BLOCKED' and positive['accepted_records_preserved']==35 and not positive['accepted_payloads_rescanned'],'PRODUCTION_BASELINE')
    lp=snapshot/'evidence/current-stage0-gate-result.json';ip=snapshot/'stage0/inventory.json';sp=snapshot/'STATUS.md';hp=snapshot/'history/changes.md';xp=snapshot/'evidence/index.json';pp=snapshot/'stage0/ledger-policy.json'
    current=base.json(lp);policy=base.json(pp);accepted=base.evidence_path(policy['baseline_accepted']['locator'])
    pending=base.evidence_path(next(x['locator'] for x in current['active_results'] if x['locator']!=str(accepted)))
    dp=base.evidence_path(policy['criterion_decisions'][0]['locator']);outcomes=[]
    def mutate_json(overrides,path,fn):
        obj=json.loads(overrides.get(str(path.resolve()),base.read(path)));fn(obj);overrides[str(path.resolve())]=data(obj)
    def rebind_envelope(o,path):
        h=hashlib.sha256(o[str(path.resolve())]).hexdigest()
        mutate_json(o,lp,lambda x:[r.update(sha256=h) for r in x['active_results'] if r['locator']==str(path)])
        if path==accepted:
            mutate_json(o,lp,lambda x:x.update(combined_results_sha256=h))
            mutate_json(o,xp,lambda x:[r.update(sha256=h) for r in x['auxiliary_records'] if r['id']=='CURRENT-STAGE0-COMBINED'])
    def change_report(path,fn):
        def apply(o):
            mutate_json(o,path,fn)
            if path==accepted:
                # Preserve the pinned baseline; offer a distinct, changed current
                # envelope at the same evidence-root depth.
                virtual=evidence/'quarantined-current-accepted.json'
                payload=o.pop(str(path.resolve()));o[str(virtual.resolve())]=payload
                h=hashlib.sha256(payload).hexdigest()
                mutate_json(o,lp,lambda x:[r.update(locator=str(virtual),sha256=h) for r in x['active_results'] if r['locator']==str(path)])
                mutate_json(o,lp,lambda x:x.update(combined_results=str(virtual),combined_results_sha256=h))
                mutate_json(o,xp,lambda x:[r.update(locator=str(virtual),sha256=h) for r in x['auxiliary_records'] if r['id']=='CURRENT-STAGE0-COMBINED'])
            else:rebind_envelope(o,path)
        return apply
    def change_inventory(fn):
        def apply(o):
            mutate_json(o,ip,fn);h=hashlib.sha256(o[str(ip.resolve())]).hexdigest();mutate_json(o,lp,lambda x:x['inventory'].update(sha256=h))
        return apply
    def change_decision(fn):
        def apply(o):
            mutate_json(o,dp,fn);h=hashlib.sha256(o[str(dp.resolve())]).hexdigest();mutate_json(o,pp,lambda x:x['criterion_decisions'][0].update(sha256=h))
        return apply
    def accepted_row(obj):return obj['results'][0]
    def current_to_pending(o):
        ref=next(r for r in current['active_results'] if r['locator']==str(pending))
        mutate_json(o,xp,lambda x:[r.update(**ref) for r in x['auxiliary_records'] if r['id']=='CURRENT-STAGE0-COMBINED'])
        mutate_json(o,lp,lambda x:x.update(combined_results=ref['locator'],combined_results_sha256=ref['sha256']))
    cases=[
      ('missing-execution-metadata','MISSING_EXECUTION_METADATA',change_report(pending,lambda x:x['results'][0].pop('engine'))),
      ('alternate-current-authority','LEDGER_AUTHORITY',lambda o:mutate_json(o,pp,lambda x:x.update(ledger='evidence/alternative-current.json'))),
      ('accepted-runner-changed','CONTRACT_BINDING',change_inventory(lambda x:next(t for t in x['tests'] if t['id']=='G0-U1-a').update(runner='tests/wasm/stage0/diagnostics/run.py'))),
      ('conceal-census-gap','LEDGER_RESULT',lambda o:mutate_json(o,lp,lambda x:x['result'].update(reasons=[r for r in x['result']['reasons'] if r!='missing S0-LL15-b [native]']))),
      ('stale-status','STATUS_CURRENT',lambda o:o.update({str(sp.resolve()):base.read(sp).replace(b'35 accepted, 12 missing',b'36 accepted, 12 missing')})),
      ('duplicate-status-row','MULTIPLE_CURRENT_ROWS',lambda o:o.update({str(sp.resolve()):base.read(sp)+next(x for x in base.read(sp).splitlines() if x.startswith(b'| Stage 0 acceptance |'))+b'\n'})),
      ('duplicate-current-index','CURRENT_INDEX',lambda o:mutate_json(o,xp,lambda x:x['auxiliary_records'].append(copy.deepcopy(next(r for r in x['auxiliary_records'] if r['id']=='CURRENT-STAGE0-COMBINED'))))),
      ('pending-as-accepted-index','ACCEPTED_AGGREGATE',current_to_pending),
      ('false-completion','LEDGER_RESULT',lambda o:mutate_json(o,lp,lambda x:x.update(result=dict(status='PASS',reasons=[])))),
      ('same-count-substitution','CONTRACT_BINDING',change_report(pending,lambda x:x['results'][0].update(id='S0-LL24-a'))),
      ('duplicate-result','DUPLICATE_RESULT',change_report(pending,lambda x:x['results'].append(copy.deepcopy(x['results'][0])))),
      ('accepted-scope-promoted','ACCEPTED_SCOPE_CHANGED',change_report(accepted,lambda x:accepted_row(x).update(configuration='CLAIM_FULL_STAGE0_COMPLETION'))),
      ('accepted-result-lost','ACCEPTED_RECORD_LOST',change_report(accepted,lambda x:x['results'].pop())),
      ('hand-built-as-generated','WRONG_EVIDENCE_CLASS',change_report(pending,lambda x:x['results'][0].update(evidence_kind='COMPILER-GENERATED WASM EXECUTION'))),
      ('execution-failed','NON_PASSING_SUBMISSION',change_report(pending,lambda x:x['results'][0].update(status='FAIL'))),
      ('skipped-execution','NON_PASSING_SUBMISSION',change_report(pending,lambda x:x['results'][0].update(skips=['required case']))),
      ('missing-assertion','ASSERTION_COVERAGE',change_report(pending,lambda x:x['results'][0].update(assertions=[]))),
      ('unapproved-criterion','UNAUTHORIZED_CRITERION',change_inventory(lambda x:next(t for t in x['tests'] if t['id']=='S0-LL23-a')['assertions'][0].update(description='A count alone passes'))),
      ('remove-r6','UNAUTHORIZED_CRITERION',change_inventory(lambda x:next(t for t in x['tests'] if t['id']=='S0-LL22-b')['assertions'][0].update(description='No R6 required'))),
      ('remove-required-test','UNAUTHORIZED_CRITERION',change_inventory(lambda x:x.update(tests=[t for t in x['tests'] if t['id']!='S0-LL24-a']))),
      ('weaken-global-roles','UNAUTHORIZED_GLOBAL_CRITERION',change_inventory(lambda x:x.update(required_record_roles=['log']))),
      ('missing-authorization','DECISION_AUTHORIZATION',change_decision(lambda x:x.update(authorization=''))),
      ('wrong-decision-snapshot','DECISION_SNAPSHOT',change_decision(lambda x:x['current_inventory'].update(sha256='0'*64))),
      ('concealed-criterion-change','DECISION_CHANGE_SET',change_decision(lambda x:x['changes'].pop())),
      ('history-missing','HISTORY_LINK',lambda o:o.update({str(hp.resolve()):base.read(hp).replace(policy['history_heading'].encode(),b'undated')})),
      ('history-as-status','HISTORY_SEPARATE',lambda o:mutate_json(o,pp,lambda x:x.update(history='STATUS.md'))),
      ('wrong-envelope-hash','EVIDENCE_IDENTITY',lambda o:mutate_json(o,lp,lambda x:x['active_results'][1].update(sha256='0'*64))),
      ('wrong-new-artifact-hash','NEW_ARTIFACT_IDENTITY',change_report(pending,lambda x:x['results'][0]['artifacts'][0].update(sha256='0'*64))),
      ('missing-required-role','REQUIRED_ARTIFACT_ROLES',change_report(pending,lambda x:x['results'][0].update(artifacts=[a for a in x['results'][0]['artifacts'] if a['role']!='abi']))),
      ('stale-ledger-count','LEDGER_COUNTS',lambda o:mutate_json(o,lp,lambda x:x['counts'].update(missing=11))),
      ('omit-unreviewed-reason','LEDGER_RESULT',lambda o:mutate_json(o,lp,lambda x:x['result'].update(reasons=[r for r in x['result']['reasons'] if not r.startswith('unreviewed')]))),
    ]
    for name,reason,mutate in cases:
        overrides={};mutate(overrides)
        # Input bytes change; the production assessor and its observations do not.
        try:ledger.assess(ledger.Inputs(snapshot,evidence,overrides,base.cache))
        except ValueError as e:require(str(e)==reason,'WRONG_CONTROL '+name+': '+str(e))
        else:raise ValueError('CONTROL_ESCAPED '+name)
        outcomes.append(dict(name=name,status='REJECTED',reason=reason,changed_input_paths=sorted(str(Path(n).relative_to(snapshot)) if Path(n).is_relative_to(snapshot) else str(Path(n).relative_to(evidence)) for n in overrides)))
    return positive,outcomes

def invoke_slot(out,replay=False):
    inv=read(out/'inventory.json');inv['tests']=[t for t in inv['tests'] if t['id']==ID]
    p=out/'slot-inventory.json'
    if replay:require(p.read_bytes()==data(inv),'SLOT_INVENTORY')
    else:save(p,inv)
    r=subprocess.run([sys.executable,str(TOOLS/'gate.py'),'--inventory',str(p),'--results',str(out/'results.json')],capture_output=True,text=True,timeout=30)
    actual=dict(exit_code=r.returncode,result=json.loads(r.stdout),stderr=r.stderr)
    require(actual==dict(exit_code=2,result=dict(status='BLOCKED',reasons=['unreviewed S0-LL24-a [control]']),stderr=''),'SLOT_GATE');return actual

def run(out,evidence):
    require(out!=ROOT and ROOT not in out.parents and not out.exists(),'FRESH_OUTPUT_OUTSIDE_CHECKOUT');out.mkdir(parents=True)
    record=dict(version=1,status='FAIL',timestamp=datetime.now(timezone.utc).isoformat(),command=[sys.executable,*sys.argv],source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources()},evidence_root=str(evidence))
    try:
        snapshot=out/'project';snapshot.mkdir()
        pins=read(HERE/'inputs.json');require(pins['version']==1 and set(pins['files'])==set(SNAPSHOTS),'INPUT_MANIFEST')
        for name in SNAPSHOTS:
            source=evidence/pins['basis']/name;require(sha(source)==pins['files'][name],'INPUT_SNAPSHOT '+name)
            p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(source.read_bytes())
        (out/'source').mkdir()
        for p in sources():(out/'source'/p.name).write_bytes(p.read_bytes())
        positive,controls=exercise(snapshot,evidence);save(out/'observed-ledger.json',positive);save(out/'controls.json',controls)
        save(out/'summary.json',dict(version=1,id=ID,variant='control',status='PASS',review_disposition='NOT_REVIEWED',scope=SCOPE,positive_project_snapshots=1,rejected_controls=len(controls),accepted_records_preserved=35,production_project_gate='BLOCKED'))
        env=dict(python=sys.version,executable=sys.executable,executable_sha256=sha(Path(sys.executable).resolve()));save(out/'environment.json',env)
        (out/'inventory.json').write_bytes((DOCS/'stage0/inventory.json').read_bytes());inv=read(out/'inventory.json');test=next(t for t in inv['tests'] if t['id']==ID)
        require(test['runner']=='tests/wasm/stage0/ledger-control/run.py','RUNNER_REGISTRATION')
        artifacts=[dict(path=p.relative_to(out).as_posix(),sha256=sha(p),role=('implementation' if p.name in ('check-project-ledger.py','evidence_binding.py','gate.py') else 'test' if p.name=='run.py' else 'schema' if p.name in ('ledger-policy.json','inventory.json') else 'log')) for p in sorted(out.rglob('*')) if p.is_file()]
        report=dict(version=1,source_revision=inv['source_revision'],inventory_sha256=sha(out/'inventory.json'),scope=SCOPE,results=[dict(id=ID,variant='control',source_revision=test['source_revision'],evidence_kind=test['evidence_kind'],status='PASS',assertions=[dict(id=a['id'],status='PASS') for a in test['assertions']],artifacts=artifacts,substitutions=[],skips=[],review_disposition='NOT_REVIEWED',command=record['command'],toolchain=env,engine='Python production ledger assessor',timestamp=record['timestamp'],configuration=dict(scope=SCOPE),seed='named ledger mutations',test_revision=sha(HERE/'run.py'))])
        save(out/'results.json',bind_report(report,inv,'inventory.json',sha(out/'inventory.json')));save(out/'slot-gate.json',invoke_slot(out))
        require(record['source_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in sources()},'SOURCE_CHANGED')
        record.update(status='PASS',contract_sha256=contract_hash(inv,ID));print('PASS: S0-LL24-a; real ledger checked, 35 accepted records preserved, 31 controls rejected. Review pending.')
    except BaseException as e:record['error']=type(e).__name__+': '+str(e);raise
    finally:save(out/'run.json',record)

def verify(packet,evidence):
    record=read(packet/'run.json');require(record['status']=='PASS','RUN_STATUS')
    for n,h in record['source_sha256'].items():require(sha(ROOT/n)==h,'SOURCE_PIN '+n)
    pins=read(HERE/'inputs.json')
    for name,h in pins['files'].items():require(sha(packet/'project'/name)==h,'INPUT_SNAPSHOT '+name)
    for a in read(packet/'results.json')['results'][0]['artifacts']:require(sha(packet/a['path'])==a['sha256'],'ARTIFACT '+a['path'])
    positive,controls=exercise(packet/'project',evidence)
    require(positive==read(packet/'observed-ledger.json') and controls==read(packet/'controls.json'),'REPRODUCTION')
    require(invoke_slot(packet,replay=True)==read(packet/'slot-gate.json'),'SLOT_RESULT')
    print('PASS: real retained ledger, accepted scope, decision joins, 31 controls, direct artifacts and slot gate.')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--output',type=Path);g.add_argument('--verify',type=Path);p.add_argument('--evidence-root',type=Path,default=Path('/Users/buildsomething/Source/ccl-evidence'));a=p.parse_args()
    if a.verify:verify(a.verify.resolve(),a.evidence_root.resolve())
    else:run(a.output.resolve(),a.evidence_root.resolve())
