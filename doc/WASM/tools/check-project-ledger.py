#!/usr/bin/env python3
"""Check the current project ledger, acceptance preservation and criterion decisions."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from evidence_binding import binding_errors, canonical, contract_hash, safe_path
from gate import required_roles

DOCS=Path(__file__).resolve().parents[1]
ROOT=DOCS.parents[1]
OPERATIONAL={'status','review_disposition','runner'}
def require(x,reason):
    if not x:raise ValueError(reason)
def digest(b):return hashlib.sha256(b).hexdigest()
def criterion(test):return {k:v for k,v in test.items() if k not in OPERATIONAL}
def context(inv):return {k:v for k,v in inv.items() if k not in ('tests','acceptance_note')}
def status_row(counts,status):
    return ('| Stage 0 acceptance | '+status+' | '+str(counts['required'])+' required variants: '+str(counts['accepted'])+
            ' accepted, '+str(counts['missing'])+' missing and '+str(counts['unreviewed'])+
            ' unreviewed. [Current ledger](evidence/current-stage0-gate-result.json). |')

class Inputs:
    def __init__(self,docs=DOCS,evidence=None,overrides=None,cache=None):
        self.docs=Path(docs).resolve();self.root=ROOT
        self.evidence=Path(evidence or json.loads((self.docs/'evidence/repository.json').read_text())['path']).resolve()
        self.overrides=overrides or {};self.cache=cache if cache is not None else {};self.read_payloads=[]
    def read(self,path):
        p=Path(path).resolve();key=str(p)
        if key in self.overrides:return self.overrides[key]
        if key not in self.cache:self.cache[key]=p.read_bytes()
        return self.cache[key]
    def json(self,path):return json.loads(self.read(path))
    def evidence_path(self,name):
        p=Path(name);p=(p if p.is_absolute() else self.evidence/p).resolve()
        require(p.is_relative_to(self.evidence),'EVIDENCE_ESCAPE');return p
    def bound(self,ref):
        require(set(ref)=={'locator','sha256'},'INVALID_REFERENCE')
        p=self.evidence_path(ref['locator']);data=self.read(p)
        require(digest(data)==ref['sha256'],'EVIDENCE_IDENTITY');return p,json.loads(data)

def policies(inputs,policy,current):
    _,base=inputs.bound(policy['criterion_baseline']);approved=base;decision_ids=[]
    require(len({t['id'] for t in base['tests']})==len(base['tests']),'BASELINE_TEST_IDS')
    for ref in policy['criterion_decisions']:
        path,decision=inputs.bound(ref)
        require(decision.get('operation')=='AUTHORIZED_CRITERION_CHANGE' and
                isinstance(decision.get('authorization'),str) and decision['authorization'].strip() and
                isinstance(decision.get('rationale'),str) and decision['rationale'].strip() and
                re.match(r'^\d{4}-\d\d-\d\dT',decision.get('timestamp','')),'DECISION_AUTHORIZATION')
        snapshots=[]
        for name in ('previous_inventory','current_inventory'):
            pin=decision[name];p=(path.parent/safe_path(pin['path'])).resolve()
            require(p.is_relative_to(path.parent),'DECISION_PATH')
            data=inputs.read(p);require(digest(data)==pin['sha256'],'DECISION_SNAPSHOT');snapshots.append(json.loads(data))
        before,after=snapshots;require(before==approved,'DECISION_CHAIN')
        a,b=({t['id']:t for t in inv['tests']} for inv in snapshots)
        require(set(a)==set(b),'UNSUPPORTED_DECISION_TEST_SET')
        expected=[dict(id=k,before=a[k],after=b[k],previous_contract_sha256=contract_hash(before,k),
                       current_contract_sha256=contract_hash(after,k)) for k in b if a[k]!=b[k]]
        require(decision['changes']==expected,'DECISION_CHANGE_SET')
        approved=after;decision_ids.append(ref['sha256'])
    require(context(current)==context(approved),'UNAUTHORIZED_GLOBAL_CRITERION')
    require({t['id']:criterion(t) for t in current['tests']}=={t['id']:criterion(t) for t in approved['tests']},'UNAUTHORIZED_CRITERION')
    require(len({t['id'] for t in current['tests']})==len(current['tests']),'DUPLICATE_TEST')
    return decision_ids

def assess(inputs,policy_path=None):
    policy=inputs.json(policy_path or inputs.docs/'stage0/ledger-policy.json')
    require(policy['version']==1 and policy['ledger']=='evidence/current-stage0-gate-result.json' and policy['status']=='STATUS.md','LEDGER_AUTHORITY')
    require(policy['history']=='history/changes.md' and policy['history']!=policy['status'],'HISTORY_SEPARATE')
    ledger=inputs.json(inputs.docs/policy['ledger']);inventory=inputs.json(inputs.docs/'stage0/inventory.json')
    require(ledger['version']==2 and ledger['inventory']==dict(locator='stage0/inventory.json',sha256=digest(inputs.read(inputs.docs/'stage0/inventory.json'))),'CURRENT_INVENTORY')
    ids=[t['id'] for t in inventory['tests']]
    require(ids and len(ids)==len(set(ids)),'INVENTORY_TEST_IDS')
    for test in inventory['tests']:
        variants=test.get('variants',[]);assertions=[a['id'] for a in test.get('assertions',[])]
        require(variants and len(variants)==len(set(variants)) and assertions and len(assertions)==len(set(assertions)), 'INVENTORY_COVERAGE')
        require(all(p in ids for p in test.get('prerequisites',[])),'INVENTORY_PREREQUISITES')
        required_roles(inventory,test)
    decisions=policies(inputs,policy,inventory)
    history=inputs.read(inputs.docs/policy['history']).decode()
    require(history.splitlines().count(policy['history_heading'])==1 and policy['history_heading'].startswith('## 2026-09-14 — '),'HISTORY_LINK')
    index=inputs.json(inputs.docs/'evidence/index.json')
    refs=[r for r in index['auxiliary_records'] if r['id']=='CURRENT-STAGE0-COMBINED'];require(len(refs)==1,'CURRENT_INDEX')
    current_ref={k:refs[0][k] for k in ('locator','sha256')}
    require(current_ref in ledger['active_results'] and ledger['combined_results']==current_ref['locator'] and
            ledger['combined_results_sha256']==current_ref['sha256'],'CURRENT_AGGREGATE')
    baseline_path,baseline=inputs.bound(policy['baseline_accepted'])
    baseline_records={(r['id'],r['variant']):r for r in baseline['results']}
    require(len(baseline_records)==policy['baseline_accepted_count'] and all(r['review_disposition']=='ACCEPTED' for r in baseline_records.values()),'ACCEPTED_BASELINE')
    records={};origins={};envelopes=[]
    for ref in ledger['active_results']:
        path,report=inputs.bound(ref)
        require(report.get('version')==2 and isinstance(report.get('results'),list),'RESULT_ENVELOPE')
        for r in report['results']:
            key=(r['id'],r['variant']);require(key not in records,'DUPLICATE_RESULT');records[key]=r;origins[key]=path
        envelopes.append((path,report))
    for key,old in baseline_records.items():
        require(key in records,'ACCEPTED_RECORD_LOST')
        require(records[key]==old,'ACCEPTED_SCOPE_CHANGED')
    for path,report in envelopes:
        errors=binding_errors(inventory,report,lambda n:inputs.read(path.parent/safe_path(n)))
        require(not errors,'CONTRACT_BINDING')
    aggregate=next(report for path,report in envelopes if str(path)==str(inputs.evidence_path(current_ref['locator'])))
    require(all(r.get('review_disposition')=='ACCEPTED' for r in aggregate['results']) and
            {(r['id'],r['variant']) for r in aggregate['results']}=={k for k,r in records.items() if r.get('review_disposition')=='ACCEPTED'},'ACCEPTED_AGGREGATE')
    required={(t['id'],v):t for t in inventory['tests'] for v in t['variants']}
    require(set(records)<=set(required),'EXTRA_RESULT')
    accepted=0;unreviewed=0;new_artifacts=0
    for key,r in records.items():
        test=required[key]
        require(r.get('status')=='PASS' and r.get('skips')==[] and r.get('substitutions')==[],'NON_PASSING_SUBMISSION')
        require(all(r.get(f) is not None and r.get(f)!='' for f in ['command','toolchain','engine','timestamp','configuration','seed','test_revision']),'MISSING_EXECUTION_METADATA')
        require(r['source_revision']==test['source_revision'] and r['evidence_kind']==test['evidence_kind'],'WRONG_EVIDENCE_CLASS')
        require(test.get('runner') and (inputs.root/safe_path(test['runner'])).is_file(),'RUNNER_LINK')
        require(r['assertions']==[dict(id=a['id'],status='PASS') for a in test['assertions']],'ASSERTION_COVERAGE')
        artifacts=r['artifacts'];require(isinstance(artifacts,list) and artifacts,'ARTIFACTS')
        roles=set()
        for a in artifacts:
            require(isinstance(a,dict) and isinstance(a.get('role'),str) and re.fullmatch(r'[0-9a-f]{64}',a.get('sha256','')),'ARTIFACT_IDENTITY')
            roles.add(a['role'])
            if key not in baseline_records:
                p=(origins[key].parent/safe_path(a['path'])).resolve()
                require(p.is_relative_to(origins[key].parent),'NEW_ARTIFACT_ESCAPE')
                require(digest(inputs.read(p))==a['sha256'],'NEW_ARTIFACT_IDENTITY');new_artifacts+=1
        require(required_roles(inventory,test)<=roles,'REQUIRED_ARTIFACT_ROLES')
        if r.get('review_disposition')=='ACCEPTED':
            require(r.get('review_record'),'ACCEPTANCE_REFERENCE');accepted+=1
            if key not in baseline_records:
                p=(origins[key].parent/safe_path(r['review_record'])).resolve()
                require(p.is_relative_to(origins[key].parent) and any(a['path']==r['review_record'] for a in artifacts),'ACCEPTANCE_REFERENCE')
                d=inputs.json(p)
                require(d.get('operation')=='PROJECT_ACCEPTANCE_NO_EXECUTION' and d.get('authorization') and d.get('scope'),'ACCEPTANCE_DECISION')
                require(any(x['id']==key[0] and x['variant']==key[1] and x['test_revision']==r['test_revision'] and
                    x['contract_sha256']==r['contract_binding']['contract_sha256'] for x in d.get('records',[])),'ACCEPTANCE_TARGET')
        else:unreviewed+=1
    missing=[key for key in required if key not in records]
    counts=dict(accepted=accepted,missing=len(missing),unreviewed=unreviewed,required=len(required))
    require(ledger['counts']==counts,'LEDGER_COUNTS')
    reasons=[]
    for key in required:
        if key not in records:reasons.append('missing '+key[0]+' ['+key[1]+']')
        elif records[key].get('review_disposition')!='ACCEPTED':reasons.append('unreviewed '+key[0]+' ['+key[1]+']')
    status='BLOCKED' if reasons else 'PASS'
    require(ledger['result']['status']==status and sorted(ledger['result']['reasons'])==sorted(reasons) and len(ledger['result']['reasons'])==len(reasons),'LEDGER_RESULT')
    status_text=inputs.read(inputs.docs/policy['status']).decode()
    rows=[line for line in status_text.splitlines() if line.startswith('| Stage 0 acceptance |')]
    require(len(rows)==1,'MULTIPLE_CURRENT_ROWS');require(rows[0]==status_row(counts,status),'STATUS_CURRENT')
    return dict(status='PASS',project_gate=status,counts=counts,accepted_records_preserved=len(baseline_records),
        accepted_payloads_rescanned=False,new_artifact_references_verified=new_artifacts,authorized_criterion_decisions=decisions,
        unresolved_dependencies=[dict(id=t['id'],missing_prerequisites=[p for p in t.get('prerequisites',[]) if
            any((p,v) not in records or records[(p,v)].get('review_disposition')!='ACCEPTED' for v in next(x for x in inventory['tests'] if x['id']==p)['variants'])])
            for t in inventory['tests'] if any((t['id'],v) not in records for v in t['variants'])])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--docs',type=Path,default=DOCS);p.add_argument('--evidence-root',type=Path);a=p.parse_args()
    try:answer=assess(Inputs(a.docs,a.evidence_root))
    except (ValueError,KeyError,TypeError,OSError) as e:print(json.dumps(dict(status='FAIL',reason=str(e))));return 1
    print(json.dumps(answer,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
