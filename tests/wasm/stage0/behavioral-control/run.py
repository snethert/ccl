#!/usr/bin/env python3
"""S0-LL02-b: unchanged semantic assertions against actual mutated Wasm modules."""
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
ID='S0-LL02-b'
CONTROLS={'drop-extra':('first-escape','all six values',1),
          'remove-capture':('mutate-escaped-state','primary result and count',2),
          'skip-cleanup':('first-escape','observable cleanup order',1),
          'skip-unwind-cleanup':('exceptional-cleanup','observable cleanup order',4),
          'reverse-cleanup':('first-escape','observable cleanup order',1)}
NAMES=['first-escape','mutate-escaped-state','independent-environment','exceptional-cleanup','state-after-exception']
SCOPE=('Hand-built Wasm control corpus: an escaping mutable environment, B-shaped indirect calls, '
       'all six values and nested normal/exceptional cleanup. Minimal descriptor and fixed caller areas; '
       'no complete CCL object layout, generated compiler, collector, threading or full bootstrap qualification.')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def require(ok,why):
    if not ok:raise ValueError(why)
def sources():return [HERE/n for n in ('program.mjs','assertions.mjs','execute.mjs','run.py')]+[TOOLS/'gate.py',TOOLS/'evidence_binding.py']

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
    q=out/'quarantine';q.mkdir();(q/'SCOPE.txt').write_text(SCOPE+'\nMutant failures are ineligible for project acceptance.\n')
    observations=[]
    for mode in ('normal',*CONTROLS):
        directory=q/mode;directory.mkdir()
        # The only mutation input goes to the WAT generator, never assertions or execution.
        js='import {program} from '+json.dumps((HERE/'program.mjs').as_uri())+'; process.stdout.write(program(process.argv[1]));'
        wat_text=invoke([str(node),'--input-type=module','--eval',js,mode],commands,out)
        (directory/'program.wat').write_text(wat_text)
        invoke([str(wat),'--enable-exceptions',str(directory/'program.wat'),'-o',str(directory/'program.wasm')],commands,out)
        invoke([str(node),str(HERE/'execute.mjs'),str(directory/'program.wasm'),str(directory/'observed.json')],commands,out,0 if mode=='normal' else 1)
        observed=read(directory/'observed.json')
        require(observed['binary_sha256']==sha(directory/'program.wasm'),'EXECUTED_BINARY')
        require(observed['node']==env['node'],'ENGINE_IDENTITY')
        if mode=='normal':
            require(observed['status']=='PASS' and 'error' not in observed and [r['name'] for r in observed['cases']]==NAMES,'NORMAL_CORPUS')
            require(len(set(observed['closures']))==2,'DISTINCT_CLOSURES')
            normal=observed
            failure=None
        else:
            name,diagnostic,count=CONTROLS[mode]
            require(observed['status']=='FAIL' and observed['error']['name']=='AssertionError'
                    and observed['error']['code']=='ERR_ASSERTION' and observed['error']['message'].split('\n')[0]==diagnostic,'MUTANT_ASSERTION '+mode)
            require(len(observed['cases'])==count and [r['name'] for r in observed['cases']]==NAMES[:count]
                    and observed['cases'][-1]['name']==name,'FIRST_FAILURE '+mode)
            require(observed['cases'][:-1]==normal['cases'][:count-1],'EARLIER_CASES '+mode)
            if mode=='drop-extra':require(observed['cases'][0]['returned']==normal['cases'][0]['returned']
                    and observed['cases'][0]['values'][:4]==normal['cases'][0]['values'][:4]
                    and observed['cases'][0]['values'][5]==73,'PRIMARY_NOT_ISOLATED')
            if 'cleanup' in mode:require(observed['cases'][-1]['exception']==normal['cases'][count-1]['exception']
                    and observed['cases'][-1]['capture']==normal['cases'][count-1]['capture'],'CLEANUP_NOT_ISOLATED')
            failure=dict(case=name,assertion=diagnostic)
        observations.append(dict(mode=mode,status='PASS' if mode=='normal' else 'REJECTED',
                                 executed_cases=len(observed['cases']),failure=failure,binary_sha256=sha(directory/'program.wasm')))
    save(out/'observations.json',observations)
    save(out/'summary.json',dict(version=1,id=ID,status='PASS',positive_cases=5,rejected_mutants=5,
        modules=6,scope=SCOPE,assertions_sha256=sha(HERE/'assertions.mjs'),review_disposition='NOT_REVIEWED'))
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
            'implementation' if p.name in ('program.mjs','program.wasm') else 'test' if p.suffix in ('.mjs','.py') else
            'schema' if p.name=='inventory.json' else 'log')) for p in sorted(out.rglob('*')) if p.is_file()]
        report=dict(version=1,source_revision=inv['source_revision'],inventory_sha256=sha(out/'inventory.json'),scope=SCOPE,
            results=[dict(id=ID,variant='control',source_revision=test['source_revision'],evidence_kind=test['evidence_kind'],status='PASS',
                assertions=[dict(id=a['id'],status='PASS') for a in test['assertions']],artifacts=artifacts,substitutions=[],skips=[],
                review_disposition='NOT_REVIEWED',command=record['command'],toolchain=read(out/'environment.json'),engine='Node/V8 actual hand-built Wasm execution',
                timestamp=record['timestamp'],configuration=dict(scope=SCOPE,mutants=list(CONTROLS)),seed='deterministic behavioral mutations',
                test_revision=sha(HERE/'assertions.mjs'))])
        save(out/'results.json',bind_report(report,inv,'inventory.json',sha(out/'inventory.json')))
        save(out/'slot-gate.json',slot(out))
        require(record['source_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in sources()},'SOURCE_CHANGED')
        record.update(status='PASS',contract_sha256=contract_hash(inv,ID))
        print('PASS: five positive Wasm calls, five rejected semantic mutants; slot blocked only for acceptance.')
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
        for mode in ('normal',*CONTROLS):
            for name in ('program.wat','program.wasm','observed.json'):
                require((replay/'quarantine'/mode/name).read_bytes()==(packet/'quarantine'/mode/name).read_bytes(),'REPLAY_BYTES '+mode+'/'+name)
        require(slot(packet)==read(packet/'slot-gate.json'),'RETAINED_SLOT')
        save(replay/'verification.json',dict(status='PASS',command=[sys.executable,*sys.argv],byte_identical_modules=6,
            byte_identical_observations=6,source_pins=len(record['source_sha256'])))
        print('PASS: retained and fresh semantic controls; six byte-identical modules/observations; source pins and slot envelope.')
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
