#!/usr/bin/env python3
"""S0-LL01-a: fail closed across real Wasm initializer exceptions."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
TOOLS=ROOT/'doc/WASM/tools'
sys.path.insert(0,str(TOOLS))
from evidence_binding import bind_report,contract_hash
ID='S0-LL01-a'
CONTROLS={
 'accept-partial':('late','AGGREGATE',0,
   "if(report.errors.length||report.steps.some(s=>s.state!=='COMPLETED'))return finish();","if(false)return finish();"),
 'overwrite-first':('diagnostic-two-failures','FIRST_FAILURE',1,
   "report.first_failure ??= error;","report.first_failure = error;"),
 'publish-before-check':('middle','NO_PARTIAL_PUBLICATION',1,
   "if(report.errors.length||report.steps.some(s=>s.state!=='COMPLETED'))return finish();",
   "publish({scope:'QUARANTINED_PREMATURE_PUBLICATION'});\n  if(report.errors.length||report.steps.some(s=>s.state!=='COMPLETED'))return finish();"),
 'conceal-step-failure':('middle','STEP_RESULTS',1,
   "step.state='FAILED';","step.state='COMPLETED';")}
SCOPE=('Stage 0 hand-built Wasm initializer harness: three modules/nine required initializers, '
       'fail-fast and diagnostic continuation, exact first failure, module omission and withheld ready publication. '
       'No CCL image restore, generated compiler, collector, threads, initializer timeout or production Stage 1 loader qualification.')
from oracle import check,STATES

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def require(ok,why):
    if not ok:raise ValueError(why)
def sources():return [HERE/n for n in ('program.mjs','bootstrap.mjs','execute.mjs','cases.json','oracle.py','run.py')]+[TOOLS/'gate.py',TOOLS/'evidence_binding.py']

def invoke(argv,commands,out,expected=0):
    try:
        p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=30)
        command=dict(argv=argv,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)
    except subprocess.TimeoutExpired as e:
        commands.append(dict(argv=argv,error=str(e)));save(out/'commands.json',commands);raise
    commands.append(command);save(out/'commands.json',commands)
    require(p.returncode==expected,'COMMAND_EXIT '+repr(command))
    return p.stdout

def exercise(out):
    out.mkdir(parents=True,exist_ok=False)
    node=Path(shutil.which('node')).resolve()
    wat=Path('/opt/homebrew/bin/wat2wasm' if Path('/opt/homebrew/bin/wat2wasm').exists() else '/usr/local/bin/wat2wasm').resolve()
    commands=[]
    env=dict(node=invoke([str(node),'--version'],commands,out).strip(),wabt=invoke([str(wat),'--version'],commands,out).strip(),
       python=sys.version,platform=platform.platform(),executables={str(p):sha(p) for p in (node,wat,Path(sys.executable).resolve())})
    save(out/'environment.json',env)
    bundle=out/'bundle';bundle.mkdir();manifest=dict(version=1,modules=[],initializers=[])
    for n,name in enumerate(('core','types','startup')):
        js='import {program} from '+json.dumps((HERE/'program.mjs').as_uri())+'; process.stdout.write(program(Number(process.argv[1])));'
        text=invoke([str(node),'--input-type=module','--eval',js,str(n)],commands,out)
        (bundle/(name+'.wat')).write_text(text)
        invoke([str(wat),'--enable-exceptions',str(bundle/(name+'.wat')),'-o',str(bundle/(name+'.wasm'))],commands,out)
        manifest['modules'].append(dict(id=name,file=name+'.wasm',sha256=sha(bundle/(name+'.wasm'))))
        for i in range(n*3,n*3+3):manifest['initializers'].append(dict(index=i,id=f'{name}/init-{i}',module=name,
                    export=f'init_{i}',requires=[i-1] if i%3 else [],expected=100+i))
    save(bundle/'manifest.json',manifest)
    q=out/'quarantine';q.mkdir();(q/'SCOPE.txt').write_text(SCOPE+'\nInner ready artifacts are synthetic test products, never project-accepted CCL images.\n')
    cases=read(HERE/'cases.json');require([c['name'] for c in cases]==list(STATES),'CASE_INVENTORY');observations=[]
    loader=(HERE/'bootstrap.mjs').read_text()
    for name,case,mutation in [(c['name'],c,None) for c in cases]+[(n,next(c for c in cases if c['name']==v[0]),v) for n,v in CONTROLS.items()]:
        d=q/name;d.mkdir();save(d/'config.json',case)
        source=HERE/'bootstrap.mjs'
        if mutation:
            _,reason,code,old,new=mutation;require(loader.count(old)==1,'MUTATION_SITE '+name)
            source=d/'bootstrap.mjs';source.write_text(loader.replace(old,new))
        else:code=0 if name=='complete' else 1
        invoke([str(node),str(HERE/'execute.mjs'),str(bundle),str(d/'config.json'),str(source),str(d)],commands,out,code)
        o=read(d/'observed.json');require(o['node']==env['node'],'ENGINE_IDENTITY')
        require(o['ready_artifact']==(d/'boot-ready.json').exists(),'READY_ARTIFACT')
        if o['ready_artifact']:require(read(d/'boot-ready.json')==o['publications'][-1],'READY_BYTES')
        if not mutation:observations.append(check(o,case,manifest))
        else:
            try:check(o,case,manifest)
            except ValueError as e:require(str(e)==reason,'WRONG_MUTANT '+name+': '+str(e))
            else:raise ValueError('MUTANT_ESCAPED '+name)
            observations.append(dict(name=name,status='REJECTED_LOADER_MUTANT',case=case['name'],reason=reason,loader_sha256=sha(source)))
    save(out/'observations.json',observations)
    save(out/'summary.json',dict(version=1,id=ID,status='PASS',positive_bootstraps=1,rejected_bootstraps=8,
       rejected_loader_mutants=4,modules=3,initializers=9,scope=SCOPE,review_disposition='NOT_REVIEWED'))
    return observations

def slot(out):
    inv=read(out/'inventory.json');inv['tests']=[t for t in inv['tests'] if t['id']==ID]
    if (out/'slot-inventory.json').exists():require(read(out/'slot-inventory.json')==inv,'SLOT_INVENTORY')
    else:save(out/'slot-inventory.json',inv)
    p=subprocess.run([sys.executable,str(TOOLS/'gate.py'),'--inventory',str(out/'slot-inventory.json'),'--results',str(out/'results.json')],cwd=ROOT,capture_output=True,text=True,timeout=30)
    result=dict(exit_code=p.returncode,result=json.loads(p.stdout),stderr=p.stderr)
    require(result==dict(exit_code=2,result=dict(status='BLOCKED',reasons=['unreviewed '+ID+' [control]']),stderr=''),'REAL_SLOT_GATE')
    return result

def run(out):
    require(out!=ROOT and ROOT not in out.parents,'OUTPUT_OUTSIDE_CHECKOUT')
    record=dict(version=1,status='FAIL',command=[sys.executable,*sys.argv],timestamp=datetime.now(timezone.utc).isoformat(),
                source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources()})
    require(not out.exists(),'FRESH_OUTPUT')
    try:
        inv_path=ROOT/'doc/WASM/stage0/inventory.json';inv=read(inv_path);test=next(t for t in inv['tests'] if t['id']==ID)
        require(test['runner']==str(HERE.relative_to(ROOT)/'run.py') and test['variants']==['control'],'RUNNER_REGISTRATION')
        exercise(out)
        (out/'inventory.json').write_bytes(inv_path.read_bytes())
        (out/'source').mkdir()
        for p in sources():(out/'source'/p.name).write_bytes(p.read_bytes())
        artifacts=[dict(path=str(p.relative_to(out)),sha256=sha(p),role=(
            'implementation' if p.name in ('program.mjs','bootstrap.mjs','core.wasm','types.wasm','startup.wasm') else 'test' if p.suffix in ('.mjs','.py') else
            'schema' if p.name=='inventory.json' else 'log')) for p in sorted(out.rglob('*')) if p.is_file()]
        report=dict(version=1,source_revision=inv['source_revision'],inventory_sha256=sha(out/'inventory.json'),scope=SCOPE,
            results=[dict(id=ID,variant='control',source_revision=test['source_revision'],evidence_kind=test['evidence_kind'],status='PASS',
                assertions=[dict(id=a['id'],status='PASS') for a in test['assertions']],artifacts=artifacts,substitutions=[],skips=[],
                review_disposition='NOT_REVIEWED',command=record['command'],toolchain=read(out/'environment.json'),engine='Node/V8 actual hand-built Wasm execution',
                timestamp=record['timestamp'],configuration=dict(scope=SCOPE,mutants=list(CONTROLS)),seed='deterministic behavioral mutations',
                test_revision=sha(HERE/'oracle.py'))])
        save(out/'results.json',bind_report(report,inv,'inventory.json',sha(out/'inventory.json')))
        save(out/'slot-gate.json',slot(out))
        require(record['source_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in sources()},'SOURCE_CHANGED')
        record.update(status='PASS',contract_sha256=contract_hash(inv,ID))
        print('PASS: one complete and eight refused bootstraps; four loader mutants rejected; slot awaits review/acceptance.')
    except BaseException as e:record['error']=type(e).__name__+': '+str(e);raise
    finally:
        if out.exists():save(out/'run.json',record)

def verify(packet,replay):
    require(replay!=ROOT and ROOT not in replay.parents and replay!=packet and packet not in replay.parents,'FRESH_REPLAY_OUTSIDE_PACKET')
    record=read(packet/'run.json');require(record['status']=='PASS','RUN_STATUS')
    for n,d in record['source_sha256'].items():require(sha(ROOT/n)==d,'SOURCE_PIN '+n)
    try:
        observed=exercise(replay)
        require(observed==read(packet/'observations.json'),'REPLAY_OBSERVATIONS')
        compared=[]
        for p in sorted(replay.rglob('*')):
            if p.is_file() and p.name not in ('commands.json','environment.json'):
                name=p.relative_to(replay)
                require((packet/name).read_bytes()==p.read_bytes(),'REPLAY_BYTES '+str(name));compared.append(str(name))
        require(slot(packet)==read(packet/'slot-gate.json'),'RETAINED_SLOT')
        save(replay/'verification.json',dict(status='PASS',command=[sys.executable,*sys.argv],byte_identical_files=compared,byte_identical_modules=3,byte_identical_observations=13,source_pins=len(record['source_sha256'])))
        print('PASS: retained and fresh initializer controls; three identical modules, thirteen observations, source pins and slot gate.')
    except BaseException as e:
        if replay.exists():save(replay/'verification.json',dict(status='FAIL',error=type(e).__name__+': '+str(e)))
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output',type=Path);g.add_argument('--verify',type=Path);p.add_argument('--replay-output',type=Path)
    a=p.parse_args()
    if a.verify:
        if not a.replay_output:p.error('--verify needs a fresh --replay-output')
        verify(a.verify.resolve(),a.replay_output.resolve())
    else:run(a.output.resolve())
