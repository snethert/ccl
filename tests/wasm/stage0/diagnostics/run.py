#!/usr/bin/env python3
"""S0-LL23-a: execute and identify real Wasm faults at retained byte offsets."""
import argparse
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from oracle import check
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];TOOLS=ROOT/'doc/WASM/tools'
sys.path.insert(0,str(TOOLS));from evidence_binding import bind_report,contract_hash
ID='S0-LL23-a'
SCOPE='Hand-built scalar Wasm diagnostics on Node/V8: exact binary-offset fault attribution, build/entry/signature/slot identities, first failure and bounded reporting. Not CCL B execution, browser-stack support, GC, threads or a production debugger.'
FAULT='const fault=frames[0]??null;'
CONTROLS={
 'skip-unrecognized-frame':('obscured-top','NO_FALSE_ATTRIBUTION','if(!match)break;','if(!match)continue;'),
 'wrong-build':('unreachable','DIAGNOSTIC_BUILD',"const diagnostic={phase:'execution',build,","const diagnostic={phase:'execution',build:{...build,binary_sha256:'0'.repeat(64)},"),
 'wrong-code':('unreachable','FAULT_FRAME',FAULT,"const fault=frames[0]?{...frames[0],logical_code_id:999}:null;"),
 'last-event-as-fault':('unreachable','FAULT_FRAME',FAULT,"const fault=frames[0]?{...frames[0],logical_code_id:lastObserved?.logical_code_id}:null;"),
 'wrong-kind':('unreachable','FAULT_FRAME',FAULT,"const fault=frames[0]?{...frames[0],entry_kind:'bridge'}:null;"),
 'wrong-signature':('unreachable','FAULT_FRAME',FAULT,"const fault=frames[0]?{...frames[0],signature:'()->(i64)'}:null;"),
 'wrong-slot':('unreachable','FAULT_FRAME',FAULT,"const fault=frames[0]?{...frames[0],slot:4}:null;"),
 'wrong-operation':('unreachable','FAULT_FRAME',FAULT,"const fault=frames[0]?{...frames[0],operation:'i32.load'}:null;"),
 'overwrite-first':('first-failure','FIRST_FAILURE','report.first_failure ??= diagnostic;','report.first_failure = diagnostic;'),
 'unbounded':('bounded-flood','REPORT_BOUNDS','if(report.errors.length<MAX_ERRORS)','if(true)'),
 'invent-unavailable':('unavailable','NO_FALSE_ATTRIBUTION',FAULT,"const fault=frames[0]??{logical_code_id:lastObserved?.logical_code_id};"),
 'drop-first':('unreachable','FIRST_FAILURE','report.first_failure ??= diagnostic;','void diagnostic;')}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def require(x,why):
    if not x:raise ValueError(why)
def sources():return [HERE/n for n in ('program.wat','abi.json','map.mjs','reporter.mjs','execute.mjs','cases.json','oracle.py','run.py')]+[TOOLS/'gate.py',TOOLS/'evidence_binding.py']
def invoke(argv,commands,out,cwd=None,code=0):
    try:p=subprocess.run(argv,cwd=cwd or ROOT,capture_output=True,text=True,timeout=30)
    except subprocess.TimeoutExpired as e:
        commands.append(dict(argv=argv,error=str(e)));save(out/'commands.json',commands);raise
    commands.append(dict(argv=argv,cwd=str(cwd or ROOT),exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr));save(out/'commands.json',commands)
    require(p.returncode==code,'COMMAND_EXIT '+repr(commands[-1]));return p.stdout

def build(out,commands):
    node=Path(shutil.which('node')).resolve();wabt=Path(shutil.which('wat2wasm')).resolve();dump=Path(shutil.which('wasm-objdump')).resolve()
    tools=dict(node=invoke([str(node),'--version'],commands,out).strip(),wabt=invoke([str(wabt),'--version'],commands,out).strip(),
               executable_sha256={str(p):sha(p) for p in (node,wabt,dump)},python=sys.version,platform=platform.platform())
    save(out/'environment.json',tools)
    bundles={}
    for cohort,bias in [('a',7),('b',9)]:
        b=out/('bundle-'+cohort);b.mkdir();bundles[cohort]=b
        (b/'source.wat').write_bytes((HERE/'program.wat').read_bytes());(b/'template.wat').write_text((HERE/'program.wat').read_text().replace('@BIAS@',str(bias)))
        (b/'abi.json').write_bytes((HERE/'abi.json').read_bytes())
        options=dict(compiler_arguments=['template.wat','-o','module.wasm'],profile='full',bias=bias,abi='scalar-diagnostics-v1')
        save(b/'options.json',options);save(b/'host-compiler.json',dict(compiler=str(wabt),version=tools['wabt'],sha256=sha(wabt)))
        invoke([str(wabt),*options['compiler_arguments']],commands,out,cwd=b)
        dis=invoke([str(dump),'-d','module.wasm'],commands,out,cwd=b);(b/'disassembly.txt').write_text(dis)
        script='import fs from "node:fs";import {decode} from '+json.dumps((HERE/'map.mjs').as_uri())+';process.stdout.write(JSON.stringify(decode(fs.readFileSync("module.wasm"),JSON.parse(fs.readFileSync("abi.json"))),null,2)+"\\n");'
        (b/'map.json').write_text(invoke([str(node),'--input-type=module','--eval',script],commands,out,cwd=b))
        files={n:sha(b/n) for n in ('module.wasm','template.wat','source.wat','abi.json','options.json','host-compiler.json')}
        save(b/'manifest.json',dict(version=1,module=cohort,files=files,map_sha256=sha(b/'map.json')))
    return node,bundles

def exercise(out):
    out.mkdir(parents=True,exist_ok=False);commands=[];node,bundles=build(out,commands)
    q=out/'quarantine';q.mkdir();cases=read(HERE/'cases.json');observations=[];reporter=(HERE/'reporter.mjs').read_text()
    require(len(cases)==16 and len({c['name'] for c in cases})==16,'CASE_BOUND')
    for name,case,mutation in [(c['name'],c,None) for c in cases]+[(n,next(c for c in cases if c['name']==v[0]),v) for n,v in CONTROLS.items()]:
        d=q/name;d.mkdir();save(d/'config.json',case);b=bundles[case['cohort']];reporter_path=HERE/'reporter.mjs'
        if case.get('preflight'):
            b=d/'bundle';shutil.copytree(bundles[case['cohort']],b);manifest=read(b/'manifest.json')
            if case['preflight']=='stale-binary':(b/'module.wasm').write_bytes((bundles['b']/'module.wasm').read_bytes())
            elif case['preflight']=='stale-map':
                m=read(b/'map.json');m['functions'][0]['operations'][0]['offset']+=1;save(b/'map.json',m);manifest['map_sha256']=sha(b/'map.json')
            elif case['preflight']=='abi-signature':
                abi=read(b/'abi.json');abi['functions'][0]['signature']='()->(i64)';save(b/'abi.json',abi);manifest['files']['abi.json']=sha(b/'abi.json')
            save(b/'manifest.json',manifest)
        if mutation:
            _,reason,old,new=mutation;require(reporter.count(old)==1,'MUTATION_SITE '+name)
            reporter_path=d/'reporter.mjs';reporter_path.write_text(reporter.replace(old,new))
        invoke([str(node),str(HERE/'execute.mjs'),str(b),str(d/'config.json'),str(reporter_path),str(d)],commands,out)
        o=read(d/'observed.json')
        if o.get('report') is not None:require((d/'diagnostics.json').read_text()==json.dumps(o['report'],separators=(',',':'),ensure_ascii=False)+'\n','DIAGNOSTIC_BYTES')
        if not mutation:observations.append(check(o,case,b))
        else:
            try:check(o,case,b)
            except ValueError as e:require(str(e)==reason,'WRONG_MUTANT '+name+': '+str(e))
            else:raise ValueError('MUTANT_ESCAPED '+name)
            observations.append(dict(name=name,status='REJECTED_REPORTER_MUTANT',reason=reason,case=case['name']))
    save(out/'observations.json',observations)
    save(out/'summary.json',dict(version=1,id=ID,variant='full',status='PASS',review_disposition='NOT_REVIEWED',scope=SCOPE,
        modules=2,execution_cases=13,preflight_refusals=3,reporter_mutants_rejected=len(CONTROLS),normal_returns=2,
        observed_runtime_or_host_failures=37,maximum_diagnostic_bytes=max(r.get('bytes',0) for r in observations)))
    return observations

def retain(p,value,replay):
    if replay:require(p.read_text()==json.dumps(value,indent=2)+'\n','RETAINED_BYTES '+str(p))
    else:save(p,value)

def slot(out,replay=False):
    inv=read(out/'inventory.json');inv['tests']=[t for t in inv['tests'] if t['id']==ID];retain(out/'slot-inventory.json',inv,replay)
    argv=[sys.executable,str(TOOLS/'gate.py'),'--inventory',str(out/'slot-inventory.json'),'--results',str(out/'results.json')]
    p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=30);value=dict(exit_code=p.returncode,result=json.loads(p.stdout),stderr=p.stderr)
    require(value==dict(exit_code=2,result=dict(status='BLOCKED',reasons=['unreviewed S0-LL23-a [full]']),stderr=''),'REAL_SLOT_GATE');return value

def omissions(out,replay=False):
    inv=read(out/'slot-inventory.json');base=read(out/'results.json');outcomes=[]
    for role in list(dict.fromkeys(inv['required_record_roles']+inv['tests'][0]['required_record_roles'])):
        report=copy.deepcopy(base);report['results'][0]['artifacts']=[a for a in report['results'][0]['artifacts'] if a['role']!=role]
        p=out/('omit-'+role+'.json');retain(p,report,replay)
        run=subprocess.run([sys.executable,str(TOOLS/'gate.py'),'--inventory',str(out/'slot-inventory.json'),'--results',str(p)],capture_output=True,text=True,timeout=30)
        value=json.loads(run.stdout);require(run.returncode==1 and not run.stderr and value==dict(status='FAIL',reasons=['missing artifact roles: S0-LL23-a [full]','unreviewed S0-LL23-a [full]']),'REAL_ROLE_OMISSION '+role)
        outcomes.append(dict(role=role,exit_code=run.returncode,result=value))
    retain(out/'role-omissions.json',outcomes,replay)

def run(out):
    require(ROOT not in out.parents and out!=ROOT,'OUTPUT_OUTSIDE_CHECKOUT');require(not out.exists(),'FRESH_OUTPUT')
    record=dict(version=1,status='FAIL',command=[sys.executable,*sys.argv],timestamp=datetime.now(timezone.utc).isoformat(),source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources()})
    try:
        inv_path=ROOT/'doc/WASM/stage0/inventory.json';inv=read(inv_path);test=next(t for t in inv['tests'] if t['id']==ID)
        require(test['runner']==str(HERE.relative_to(ROOT)/'run.py'),'RUNNER_REGISTRATION')
        exercise(out);(out/'inventory.json').write_bytes(inv_path.read_bytes());(out/'source').mkdir()
        for p in sources():(out/'source'/p.name).write_bytes(p.read_bytes())
        def role(p):
            if p.parent.name in ('bundle-a','bundle-b'):
                return {'module.wasm':'installed-binary','template.wat':'template','source.wat':'source','abi.json':'abi','host-compiler.json':'host-compiler','options.json':'options'}.get(p.name,'log')
            if p.name in ('map.mjs','reporter.mjs'):return 'implementation'
            if p.name in ('oracle.py','run.py','execute.mjs'):return 'test'
            return 'schema' if p.name in ('inventory.json','cases.json') else 'log'
        artifacts=[dict(path=p.relative_to(out).as_posix(),sha256=sha(p),role=role(p)) for p in sorted(out.rglob('*')) if p.is_file()]
        report=dict(version=1,source_revision=inv['source_revision'],inventory_sha256=sha(out/'inventory.json'),scope=SCOPE,results=[dict(
            id=ID,variant='full',source_revision=test['source_revision'],evidence_kind=test['evidence_kind'],status='PASS',assertions=[dict(id=a['id'],status='PASS') for a in test['assertions']],
            artifacts=artifacts,substitutions=[],skips=[],review_disposition='NOT_REVIEWED',command=record['command'],toolchain=read(out/'environment.json'),engine='Node/V8 real hand-built Wasm traps',
            timestamp=record['timestamp'],configuration=dict(scope=SCOPE),seed='named deterministic faults and reporter mutants',test_revision=sha(HERE/'oracle.py'))])
        save(out/'results.json',bind_report(report,inv,'inventory.json',sha(out/'inventory.json')));save(out/'slot-gate.json',slot(out));omissions(out)
        require(record['source_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in sources()},'SOURCE_CHANGED')
        record.update(status='PASS',contract_sha256=contract_hash(inv,ID));print('PASS: S0-LL23-a; 13 execution cases, 3 build refusals, 12 reporter mutants and 10 real production-role omissions. Review pending.')
    except BaseException as e:record['error']=type(e).__name__+': '+str(e);raise
    finally:
        if out.exists():save(out/'run.json',record)

def verify(packet):
    record=read(packet/'run.json');require(record['status']=='PASS','RUN_STATUS')
    for name,h in record['source_sha256'].items():require(sha(ROOT/name)==h,'SOURCE_PIN '+name)
    for a in read(packet/'results.json')['results'][0]['artifacts']:require(sha(packet/a['path'])==a['sha256'],'ARTIFACT '+a['path'])
    with tempfile.TemporaryDirectory(prefix='ccl-diagnostics-verify-') as tmp:
        fresh=Path(tmp)/'replay';observations=exercise(fresh)
        require(observations==read(packet/'observations.json'),'OBSERVATION_REPRODUCTION')
        require(read(fresh/'summary.json')==read(packet/'summary.json'),'SUMMARY_REPRODUCTION')
        names=[p.relative_to(fresh) for p in fresh.rglob('*') if p.is_file() and p.name not in ('commands.json',)]
        for n in names:require((fresh/n).read_bytes()==(packet/n).read_bytes(),'DETERMINISTIC_BYTES '+str(n))
    require(slot(packet,replay=True)==read(packet/'slot-gate.json'),'SLOT_RESULT')
    omissions(packet,replay=True)
    print('PASS: fresh Wasm execution, independent disassembly oracle, exact deterministic bytes, direct pins and production role omissions.')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--output',type=Path);g.add_argument('--verify',type=Path);a=p.parse_args()
    if a.verify:verify(a.verify.resolve())
    else:run(a.output.resolve())
