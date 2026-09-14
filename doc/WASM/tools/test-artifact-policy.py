#!/usr/bin/env python3
"""Exercise production role lists with quarantined synthetic gate records."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from evidence_binding import bind_report, contract_hash, binding_errors, safe_path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ['implementation', 'test', 'schema', 'log']
WASM = ['source', 'abi', 'template', 'installed-binary', 'host-compiler', 'options']
NATIVE = ['source', 'host-compiler', 'image', 'options']
TARGETS = {'S0-ENGINE-a': [r for r in WASM if r != 'abi'],
           **{n: WASM for n in ['S0-LL07-a', 'S0-LL13-b', 'S0-LL15-a', 'S0-LL19-a', 'S0-LL21-c', 'S0-LL23-a']},
           **{n: NATIVE for n in ['S0-LL15-b', 'S0-LL15-c', 'S0-LL22-b']}}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def save(p, x): p.write_text(json.dumps(x, indent=2, ensure_ascii=False)+'\n')
def require(x, why):
    if not x: raise ValueError(why)

def exercise(out, inventory):
    require(inventory['required_record_roles'] == BASE, 'GLOBAL_MINIMUM_UNCHANGED')
    tests = {t['id']: t for t in inventory['tests']}
    require({n: tests[n].get('required_record_roles') for n in TARGETS} == TARGETS, 'PRODUCTION_ROLE_POLICY')
    outcomes = []; commands = []
    out.mkdir(parents=True, exist_ok=False)
    save(out/'production-inventory.json', inventory)
    q = out/'quarantine'; q.mkdir()
    (q/'SCOPE.txt').write_text('SYNTHETIC POLICY INPUTS. No compilation or runtime execution. Global context deliberately differs from production.\n')
    roles = list(dict.fromkeys(BASE + WASM + NATIVE))
    for role in roles: (q/(role+'.txt')).write_text('SYNTHETIC POLICY INPUT '+role+'\n')
    def check(name, inv, report, expected):
        d=q/name; d.mkdir(); save(d/'inventory.json', inv)
        for r in report['results']:
            for a in r['artifacts']: a['path']='../'+a['path'] if not a['path'].startswith('../') else a['path']
        # Gate confines artifacts to the report directory; a shared local copy
        # avoids escaping references and keeps each case independently replayable.
        for role in roles: (d/(role+'.txt')).write_bytes((q/(role+'.txt')).read_bytes())
        for r in report['results']:
            for a in r['artifacts']: a['path']=Path(a['path']).name
        bound = bind_report(dict(version=1, source_revision=inv['source_revision'], inventory_sha256=sha(d/'inventory.json'),
                                 results=report['results']), inv, 'inventory.json', sha(d/'inventory.json'))
        save(d/'results.json', bound)
        argv=[sys.executable,str(HERE/'gate.py'),'--inventory',str(d/'inventory.json'),'--results',str(d/'results.json')]
        p=subprocess.run(argv,capture_output=True,text=True,timeout=15)
        commands.append(dict(name=name,argv=argv,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)); save(out/'commands.json',commands)
        actual=json.loads(p.stdout)
        require(actual == expected and p.returncode == {'PASS':0,'FAIL':1}[expected['status']] and not p.stderr, 'GATE '+name+': '+p.stdout)
        outcomes.append(dict(name=name,**actual))
    def base(ident):
        inv=copy.deepcopy(inventory); inv['stage']='QUARANTINED_PRODUCTION_ROLE_POLICY'
        test=copy.deepcopy(tests[ident]); test.update(prerequisites=[],runner='SYNTHETIC-NO-EXECUTION')
        inv['tests']=[test]
        required=list(dict.fromkeys(BASE+test.get('required_record_roles',[])))
        records=[]
        for variant in test['variants']:
            records.append(dict(id=ident,variant=variant,source_revision=test['source_revision'],evidence_kind=test['evidence_kind'],
                status='PASS',assertions=[dict(id=a['id'],status='PASS') for a in test['assertions']],
                artifacts=[dict(role=r,path=r+'.txt',sha256=sha(q/(r+'.txt'))) for r in required],
                substitutions=[],skips=[],review_disposition='ACCEPTED',review_record='QUARANTINED SYNTHETIC FLAG; NO PROJECT ACCEPTANCE',
                **{k:'SYNTHETIC POLICY INPUT; NO EXECUTION' for k in ['command','toolchain','engine','timestamp','configuration','seed','test_revision']}))
        return inv,dict(results=records)
    for ident in [*TARGETS, 'S0-LL22-a']:
        inv, report=base(ident)
        check(ident+'-complete',copy.deepcopy(inv),copy.deepcopy(report),dict(status='PASS',reasons=[]))
        for role in list(dict.fromkeys(BASE+tests[ident].get('required_record_roles',[]))):
            r=copy.deepcopy(report); r['results'][0]['artifacts']=[a for a in r['results'][0]['artifacts'] if a['role']!=role]
            check(ident+'-omit-'+role,copy.deepcopy(inv),r,dict(status='FAIL',reasons=['missing artifact roles: '+ident+' ['+tests[ident]['variants'][0]+']']))
    inv,report=base('S0-LL22-a')
    inv['tests'][0]['required_record_roles']=[]
    r=copy.deepcopy(report);r['results'][0]['artifacts']=[a for a in r['results'][0]['artifacts'] if a['role']!='schema']
    check('empty-local-cannot-waive-global',copy.deepcopy(inv),r,dict(status='FAIL',reasons=['missing artifact roles: S0-LL22-a [control]']))
    for n,value in [('string','abi'),('duplicate',['abi','abi']),('non-string',[None]),('blank',[' '])]:
        bad=copy.deepcopy(inv);bad['tests'][0]['required_record_roles']=value
        check('malformed-'+n,bad,copy.deepcopy(report),dict(status='FAIL',reasons=['invalid artifact-role requirements: S0-LL22-a']))
    # Contract identity already includes complete semantic test entries.
    old=copy.deepcopy(inventory);ident='S0-LL23-a';changed=copy.deepcopy(inventory)
    next(t for t in changed['tests'] if t['id']==ident)['required_record_roles'].append('extra-role')
    require(contract_hash(old,ident)!=contract_hash(changed,ident),'LOCAL_POLICY_NOT_BOUND')
    require(contract_hash(old,'S0-LL22-a')==contract_hash(changed,'S0-LL22-a'),'UNRELATED_CONTRACT_CHANGED')
    save(out/'observations.json',outcomes)
    return dict(status='PASS',production_tests=len(TARGETS),complete_cases=sum(x['status']=='PASS' for x in outcomes),
                rejected_cases=sum(x['status']=='FAIL' for x in outcomes),global_minimum_not_waived=True,
                local_policy_bound=True,unrelated_contract_unchanged=True,scope='Synthetic policy enforcement, no runtime or acceptance.')

def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output',type=Path);g.add_argument('--verify',type=Path);a=p.parse_args()
    if a.verify:
        packet=a.verify.resolve();record=read(packet/'run.json')
        require(record['status']=='PASS','RUN_STATUS')
        for name,digest in record['source_sha256'].items():require(sha(ROOT/name)==digest,'SOURCE_PIN '+name)
        with tempfile.TemporaryDirectory(prefix='ccl-role-policy-verify-') as tmp:
            fresh=Path(tmp)/'replay';summary=exercise(fresh,read(packet/'production-inventory.json'))
            require(summary==read(packet/'summary.json'),'SUMMARY')
            require(read(fresh/'observations.json')==read(packet/'observations.json'),'OBSERVATIONS')
            with zipfile.ZipFile(packet/'quarantine.zip') as z:
                files={p.relative_to(fresh/'quarantine').as_posix():p.read_bytes() for p in (fresh/'quarantine').rglob('*') if p.is_file()}
                require(set(z.namelist())==set(files),'QUARANTINE_BOUND')
                require(all(z.read(n)==b for n,b in files.items()),'QUARANTINE_BYTES')
        print('PASS: retained production role policy, all gate cases, exact quarantine bytes and direct sources.');return
    out=a.output.resolve()
    require(ROOT not in out.parents,'OUTPUT_OUTSIDE_CHECKOUT')
    record=dict(version=1,status='FAIL',timestamp=datetime.now(timezone.utc).isoformat(),argv=sys.argv,
                source_sha256={str(n.relative_to(ROOT)):sha(n) for n in [HERE/'gate.py',HERE/'evidence_binding.py',Path(__file__)]})
    try:
        inventory=read(ROOT/'doc/WASM/stage0/inventory.json');summary=exercise(out,inventory)
        idx=read(ROOT/'doc/WASM/evidence/index.json');current=next(r for r in idx['auxiliary_records'] if r['id']=='CURRENT-STAGE0-COMBINED')
        path=Path(current['locator']);require(sha(path)==current['sha256'],'ACCEPTED_ENVELOPE')
        report=read(path);require(len(report['results'])==35 and all(r['review_disposition']=='ACCEPTED' for r in report['results']),'ACCEPTED_COUNT')
        require(not binding_errors(inventory,report,lambda n:(path.parent/safe_path(n)).read_bytes()),'ACCEPTED_BINDINGS')
        save(out/'binding-check.json',dict(status='PASS',records=35,accepted_report=current['locator'],sha256=current['sha256'],payloads_reverified=False))
        save(out/'summary.json',summary);record['status']='PASS';print(json.dumps(summary))
    except BaseException as e:record['error']=type(e).__name__+': '+str(e);raise
    finally:
        if out.exists():save(out/'run.json',record)
if __name__=='__main__':main()
