#!/usr/bin/env python3
"""S0-LL07-a: execute checked conversion families in real Wasm memory."""
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
from binary import decode
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];TOOLS=ROOT/'doc/WASM/tools'
sys.path.insert(0,str(TOOLS));from evidence_binding import bind_report,contract_hash
ID='S0-LL07-a'
SCOPE='Hand-built wasm32 conversions on macOS Node/V8, one mutator, actual memory grown to 2 GiB plus one page; checked scalar fixnums, pointers, logical IDs and typed table slots. No production allocator, GC, C linker, B compiler output, browser or full D1 object-layout claim.'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def require(x,why):
    if not x:raise ValueError(why)
def sources():return [HERE/n for n in ('program.wat','abi.json','binary.py','execute.mjs','cases.json','oracle.py','run.py')]+[TOOLS/'gate.py',TOOLS/'evidence_binding.py',ROOT/'doc/WASM/contracts/layout.json']
def invoke(argv,commands,out,cwd=None,code=0):
    try:p=subprocess.run(argv,cwd=cwd or ROOT,capture_output=True,text=True,timeout=60)
    except subprocess.TimeoutExpired as e:
        commands.append(dict(argv=argv,error=str(e)));save(out/'commands.json',commands);raise
    commands.append(dict(argv=argv,cwd=str(cwd or ROOT),exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr));save(out/'commands.json',commands)
    require(p.returncode==code,'COMMAND_EXIT '+repr(commands[-1]));return p.stdout

# Each mutation changes one unique source expression. Cases and oracle are fixed.
CONTROLS = {
 'unbox-logical-shift': ('wat', 'unbox--4', '(i32.shr_s (local.get $word) (i32.const 2))', '(i32.shr_u (local.get $word) (i32.const 2))'),
 'box-range-omitted': ('wat', 'box-refuse-536870912', '(i32.or (i32.lt_s (local.get $n) (i32.const -536870912)) (i32.gt_s (local.get $n) (i32.const 536870911)))', '(i32.const 0)'),
 'raw-as-signed-fixnum': ('wat', 'raw-refuse-fixnum-4294967280', '(i32.gt_u (local.get $raw) (i32.const 536870911))', '(i32.gt_s (local.get $raw) (i32.const 536870911))'),
 'car-displacement': ('wat', 'low-car', '(i32.load (i32.add (local.get $ptr) (i32.const 3)))', '(i32.load (i32.add (local.get $ptr) (i32.const 4)))'),
 'cdr-unadjusted': ('wat', 'low-cdr', '(i32.load (i32.sub (local.get $ptr) (i32.const 1)))', '(i32.load (local.get $ptr))'),
 'header-unadjusted': ('wat', 'low-header-load', '(i32.load (i32.sub (local.get $ptr) (i32.const 6)))', '(i32.load (local.get $ptr))'),
 'javascript-signed-address': ('js', 'tag-2147483648-1', 'return value >>> 0;', 'return value | 0;'),
 'javascript-raw-signed-result': ('js', 'tag-2147483648-1', 'return value >>> 0;', 'return value;'),
 'double-tagged-id': ('wat', 'allocate-id-1', '(i32.shl (local.get $id) (i32.const 2)) (i32.const 0))\n  (func (export "id_encode")', '(i32.shl (local.get $id) (i32.const 4)) (i32.const 0))\n  (func (export "id_encode")'),
 'id-exhaustion-omitted': ('wat', 'id-exhaustion', '(i32.ge_u (global.get $next) (i32.const 536870912))', '(i32.const 0)'),
 'id-unissued-accepted': ('wat', 'id-unissued', '(i32.ge_u (local.get $id) (global.get $next))', '(i32.const 0)'),
 'slot-one-past-capacity': ('wat', 'slots-zero-refusal', '(i32.ge_u (local.get $slot) (global.get $capacity))', '(i32.gt_u (local.get $slot) (global.get $capacity))'),
 'reserved-slots-ignored': ('wat', 'slot-reserved-0', '(i32.lt_u (local.get $slot) (global.get $reserved))', '(i32.const 0)'),
 'handle-kind-ignored': ('wat', 'slot-tagged-id-same-bits', '(i32.ne (local.get $kind) (i32.const 3))', '(i32.const 0)'),
 'signature-ignored': ('wat', 'slot-wrong-signature', '(i32.ne (local.get $sig) (i32.const 1))', '(i32.const 0)'),
 'role-ignored': ('wat', 'slot-wrong-role', '(i32.ne (local.get $role) (i32.const 1))', '(i32.const 0)'),
 'uninstalled-dispatch': ('wat', 'slot-uninstalled', '(i32.eqz (i32.load (i32.add (i32.const 64) (i32.mul (local.get $slot) (i32.const 4)))))', '(i32.const 0)'),
 'span-wraparound': ('wat', 'real-wraparound', '(i64.add (i64.extend_i32_u (local.get $raw)) (i64.const 8))', '(i64.extend_i32_u (i32.add (local.get $raw) (i32.const 8)))'),
 'host-input-unchecked': ('js', 'host-raw-overflow', 'return Number.isInteger(value) && value >= low && value <= high;', 'return true;'),
}


def build(bundle, bias, wat, node, compiler, commands, output, environment):
    bundle.mkdir(parents=True)
    (bundle/'source.wat').write_text(wat)
    (bundle/'template.wat').write_text(wat.replace('@BIAS@', str(bias)))
    (bundle/'abi.json').write_bytes((HERE/'abi.json').read_bytes())
    options=dict(compiler_arguments=['template.wat','-o','module.wasm'],node_arguments=[],
                 bias=bias,profile='full',abi='conversions-v1')
    save(bundle/'options.json',options)
    save(bundle/'host-compiler.json',dict(compiler=str(compiler),version=environment['wabt'],sha256=sha(compiler)))
    invoke([str(compiler),*options['compiler_arguments']],commands,output,cwd=bundle)
    save(bundle/'map.json',decode((bundle/'module.wasm').read_bytes(),read(bundle/'abi.json')))
    save(bundle/'manifest.json',dict(version=1,files={n:sha(bundle/n) for n in
         ('module.wasm','template.wat','source.wat','abi.json','map.json','options.json','host-compiler.json')}))


def exercise(out):
    out.mkdir(parents=True,exist_ok=False)
    commands=[]
    require(platform.system()=='Darwin','MACOS_REFERENCE')
    node=Path(shutil.which('node')).resolve()
    compiler=Path(shutil.which('wat2wasm')).resolve()
    environment=dict(node=invoke([str(node),'--version'],commands,out).strip(),
                     wabt=invoke([str(compiler),'--version'],commands,out).strip(),
                     executable_sha256={str(p):sha(p) for p in (node,compiler)},
                     python=sys.version,platform=platform.platform())
    save(out/'environment.json',environment)
    wat=(HERE/'program.wat').read_text()
    js=(HERE/'execute.mjs').read_text()
    cases=read(HERE/'cases.json')
    require(len(cases)==136 and len({c['name'] for c in cases})==len(cases),'CASE_COUNT')
    observations=[]
    for name,bias,control in [('a',7,None),('b',9,None)]+[(k,7,v) for k,v in CONTROLS.items()]:
        bundle=out/('bundle-'+name if control is None else 'quarantine/'+name)
        source=wat
        executor=HERE/'execute.mjs'
        if control:
            kind,case,old,new=control
            require((wat if kind=='wat' else js).count(old)==1,'UNIQUE_MUTATION '+name)
            if kind=='wat':source=wat.replace(old,new)
        build(bundle,bias,source,node,compiler,commands,out,environment)
        if control:
            save(bundle/'mutation.json',dict(name=name,kind=kind,old=old,new=new,first_case=case))
            if kind=='js':
                executor=bundle/'execute.mjs'
                executor.write_text(js.replace(old,new))
        invoke([str(node),str(executor),str(bundle),str(HERE/'cases.json'),str(bundle/'observed.json')],commands,out)
        if control is None:
            observations.append(dict(name=name,**check(read(bundle/'observed.json'),cases,bundle)))
        else:
            try:
                check(read(bundle/'observed.json'),cases,bundle)
            except ValueError as e:
                require(str(e)=='CASE '+case,'MUTANT_ORACLE '+name+': '+str(e))
            else:
                raise ValueError('MUTANT_ESCAPED '+name)
            observations.append(dict(name=name,status='REJECTED',first_case=case))
    require(sha(out/'bundle-a/source.wat')==sha(out/'bundle-b/source.wat') and
            sha(out/'bundle-a/module.wasm')!=sha(out/'bundle-b/module.wasm'),'MATERIALIZED_VARIANTS')
    save(out/'observations.json',observations)
    save(out/'summary.json',dict(version=1,id=ID,variant='full',status='PASS',scope=SCOPE,
         review_disposition='NOT_REVIEWED',cohorts=2,cases_per_cohort=len(cases),
         families=observations[0]['families'],mutants_rejected=len(CONTROLS),
         actual_memory_bytes=2147549184,synthetic_address_max=4294967286,
         reserved_slots=observations[0]['registered_slots']))
    return observations


def retain(p,value,replay):
    if replay:require(p.read_text()==json.dumps(value,indent=2)+'\n','RETAINED_BYTES '+str(p))
    else:save(p,value)

def slot(out,replay=False):
    inv=read(out/'inventory.json');inv['tests']=[t for t in inv['tests'] if t['id']==ID];retain(out/'slot-inventory.json',inv,replay)
    argv=[sys.executable,str(TOOLS/'gate.py'),'--inventory',str(out/'slot-inventory.json'),'--results',str(out/'results.json')]
    p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=30);value=dict(exit_code=p.returncode,result=json.loads(p.stdout),stderr=p.stderr)
    require(value==dict(exit_code=2,result=dict(status='BLOCKED',reasons=['unreviewed S0-LL07-a [full]']),stderr=''),'REAL_SLOT_GATE');return value

def omissions(out,replay=False):
    inv=read(out/'slot-inventory.json');base=read(out/'results.json');outcomes=[]
    for role in list(dict.fromkeys(inv['required_record_roles']+inv['tests'][0]['required_record_roles'])):
        report=copy.deepcopy(base);report['results'][0]['artifacts']=[a for a in report['results'][0]['artifacts'] if a['role']!=role]
        p=out/('omit-'+role+'.json');retain(p,report,replay)
        run=subprocess.run([sys.executable,str(TOOLS/'gate.py'),'--inventory',str(out/'slot-inventory.json'),'--results',str(p)],capture_output=True,text=True,timeout=30)
        value=json.loads(run.stdout);require(run.returncode==1 and not run.stderr and value==dict(status='FAIL',reasons=['missing artifact roles: S0-LL07-a [full]','unreviewed S0-LL07-a [full]']),'REAL_ROLE_OMISSION '+role)
        outcomes.append(dict(role=role,exit_code=run.returncode,result=value))
    retain(out/'role-omissions.json',outcomes,replay)

def run(out):
    require(ROOT not in out.parents and out!=ROOT,'OUTPUT_OUTSIDE_CHECKOUT');require(not out.exists(),'FRESH_OUTPUT')
    snapshots={str(p.relative_to(ROOT)):p.read_bytes() for p in sources()}
    record=dict(version=1,status='FAIL',command=[sys.executable,*sys.argv],timestamp=datetime.now(timezone.utc).isoformat(),source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources()})
    try:
        inv_path=ROOT/'doc/WASM/stage0/inventory.json';inv=read(inv_path);test=next(t for t in inv['tests'] if t['id']==ID)
        require(test['runner']==str(HERE.relative_to(ROOT)/'run.py'),'RUNNER_REGISTRATION')
        exercise(out);(out/'inventory.json').write_bytes(inv_path.read_bytes());(out/'source').mkdir()
        for p in sources():(out/'source'/p.name).write_bytes(p.read_bytes())
        def role(p):
            if p.parent.name in ('bundle-a','bundle-b'):
                return {'module.wasm':'installed-binary','template.wat':'template','source.wat':'source','abi.json':'abi','host-compiler.json':'host-compiler','options.json':'options'}.get(p.name,'log')
            if p.name in ('program.wat','binary.py'):return 'implementation'
            if p.name in ('oracle.py','run.py','execute.mjs'):return 'test'
            return 'schema' if p.name in ('inventory.json','cases.json') else 'log'
        artifacts=[dict(path=p.relative_to(out).as_posix(),sha256=sha(p),role=role(p)) for p in sorted(out.rglob('*')) if p.is_file()]
        report=dict(version=1,source_revision=inv['source_revision'],inventory_sha256=sha(out/'inventory.json'),scope=SCOPE,results=[dict(
            id=ID,variant='full',source_revision=test['source_revision'],evidence_kind=test['evidence_kind'],status='PASS',assertions=[dict(id=a['id'],status='PASS') for a in test['assertions']],
            artifacts=artifacts,substitutions=[],skips=[],review_disposition='NOT_REVIEWED',command=record['command'],toolchain=read(out/'environment.json'),engine='Node/V8 real hand-built Wasm conversions',
            timestamp=record['timestamp'],configuration=dict(scope=SCOPE),seed='four named conversion families and single-site mutants',test_revision=sha(HERE/'oracle.py'))])
        save(out/'results.json',bind_report(report,inv,'inventory.json',sha(out/'inventory.json')));save(out/'slot-gate.json',slot(out));omissions(out)
        require(record['source_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in sources()},'SOURCE_CHANGED')
        record.update(status='PASS',contract_sha256=contract_hash(inv,ID));print('PASS: S0-LL07-a; 272 conversion cases, 19 conversion mutants and 10 real production-role omissions. Review pending.')
    except BaseException as e:record['error']=type(e).__name__+': '+str(e);raise
    finally:
        if out.exists():
            save(out/'run.json',record)
            (out/'source').mkdir(exist_ok=True)
            for name,data in snapshots.items():(out/'source'/Path(name).name).write_bytes(data)

def verify(packet):
    record=read(packet/'run.json');require(record['status']=='PASS','RUN_STATUS')
    for name,h in record['source_sha256'].items():require(sha(ROOT/name)==h,'SOURCE_PIN '+name)
    for a in read(packet/'results.json')['results'][0]['artifacts']:require(sha(packet/a['path'])==a['sha256'],'ARTIFACT '+a['path'])
    tmp=Path(tempfile.mkdtemp(prefix='ccl-conversions-verify-'))
    try:
        fresh=tmp/'replay';observations=exercise(fresh)
        require(observations==read(packet/'observations.json'),'OBSERVATION_REPRODUCTION')
        require(read(fresh/'summary.json')==read(packet/'summary.json'),'SUMMARY_REPRODUCTION')
        names=[p.relative_to(fresh) for p in fresh.rglob('*') if p.is_file() and p.name not in ('commands.json',)]
        for n in names:require((fresh/n).read_bytes()==(packet/n).read_bytes(),'DETERMINISTIC_BYTES '+str(n))
        require(slot(packet,replay=True)==read(packet/'slot-gate.json'),'SLOT_RESULT')
        omissions(packet,replay=True)
    except BaseException as error:
        save(tmp/'failure.json',dict(status='FAIL',packet=str(packet),source_sha256=record['source_sha256'],error=str(error)))
        print('Original verification failure retained at '+str(tmp),file=sys.stderr)
        raise
    else:
        shutil.rmtree(tmp)
    print('PASS: fresh Wasm execution, independent integer/set and binary-interface oracles, '+str(len(names))+' exact deterministic files, direct pins and production role omissions.')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--output',type=Path);g.add_argument('--verify',type=Path);a=p.parse_args()
    if a.verify:verify(a.verify.resolve())
    else:run(a.output.resolve())
