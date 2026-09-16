#!/usr/bin/env python3
"""Bind and exercise the actual generated registration build, with fatal diagnostics."""
import argparse,copy,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def require(x,reason):
    if not x:raise ValueError(reason)
def assess(result,manifest,disasm):
    require(result['status']=='PASS' and len(result['positive'])==24,'POSITIVE_EXECUTION')
    require(len(result['controls'])==37 and all(r['status']=='REJECTED' for r in result['controls']),'BUILD_CONTROLS')
    entry=next(e for e in manifest['entries'] if e['name']=='identity')
    ops=[]
    for line in disasm.splitlines():
        m=re.match(r'^\s*([0-9a-f]+):\s+[0-9a-f ]+\|\s+(.*)$',line)
        if m:ops.append((int(m[1],16),m[2].split()))
    expected={'load':next(off for off,op in ops if op==['i32.load','2','0']),
              'store':next(off for off,op in ops if op==['i32.store','2','0']),
              'arity':next(off for off,op in ops if op==['unreachable'])}
    require([o['mode'] for o in result['observations']]==['load','store','arity'],'FAULT_POPULATION')
    for row in result['observations']:
        d=row['diagnostic'];f=d['fault'];mode=row['mode']
        require(d['build']==result['build'],'FAULT_BUILD')
        require(f==dict(function_index=0,logical_code_id=entry['logical_code_id'],entry_kind='B',signature=entry['signature'],slot=entry['slot'],operation={'load':'i32.load','store':'i32.store','arity':'unreachable'}[mode],binary_offset=expected[mode]),'FAULT_BINARY_LOCATION')
        require(d['last_observed']['attribution']=='CONTEXT_ONLY' and d['last_observed']['logical_code_id']!=f['logical_code_id'],'CONTEXT_ATTRIBUTION')
    r=result['report'];require(r['first_failure']==result['observations'][0]['diagnostic'],'FIRST_FAILURE')
    require((r['failures'],r['dropped'],len(r['errors']))==(25,22,3) and result['diagnostic_bytes']<=8192,'DIAGNOSTIC_BUDGET')
    require(len(result['unavailable'])==2 and all(x['diagnostic']['fault'] is None and x['diagnostic']['classification']=='UNAVAILABLE' for x in result['unavailable']),'UNAVAILABLE_ATTRIBUTION')
    return {'generated_calls':24,'binding_controls':37,'generated_faults':3,'failure_flood':25,'retained_failures':3,'dropped_failures':22,'unavailable_stacks':2,'worker_count':1}

def run(native,qualification,out):
    require(read(native/'run.json')['status']=='PASS' and read(qualification/'summary.json')['status']=='PASS','R6_PREREQUISITE')
    for file,target in [('wasm32-backend.lisp','compiler/WASM32/wasm32-backend.lisp'),('xwasm32-fasload.lisp','xdump/xwasm32-fasload.lisp')]:
        require((HERE.parent/'registration/payload'/file).read_bytes()==(native/'proposal/files'/target).read_bytes(),'COMPILER_SOURCE_JOIN')
    require(read(native/'target-checks.json')['refusals']==read(qualification/'summary.json')['native']['unsupported_refusals'],'QUALIFICATION_JOIN')
    out.mkdir(parents=True,exist_ok=False);shutil.copytree(native,out/'native');shutil.copytree(qualification,out/'qualification')
    (out/'schemas').mkdir();(out/'installed').mkdir();(out/'source').mkdir();(out/'controls').mkdir()
    for name,path in [('tcr.json','doc/WASM/contracts/tcr.v1.json'),('layout.json','doc/WASM/contracts/wasm32-layout.v1.json')]:shutil.copy(ROOT/path,out/'schemas'/name)
    save(out/'schemas/abi.json',{'version':1,'candidate':'B','entry_kind':'B','signature':'(i32,i32)->(i32,i32)','parameters':['self','nargs'],'arguments':'value stack at TCR.vsp','results':['value0','nvalues'],'result_region':'caller-owned at TCR.mv_base; count includes value0','scope':'nonallocating required-argument leaf subset; no heap constants, tail transfers, dynamic calls or Lisp condition path'})
    options={'profile':'full','workers':1,'wat2wasm':['--enable-threads'],'target':'wasm32','source_revision':read(native/'run.json')['source_revision'],'diagnostic_engine':'V8','native_test_revision':read(native/'run.json')['inputs']['test_revision']};save(out/'options.json',options)
    toolchain={}
    for name,command in [('node',['/usr/local/bin/node','--version']),('wat2wasm',['/usr/local/bin/wat2wasm','--version']),('wasm-objdump',['/usr/local/bin/wasm-objdump','--version'])]:toolchain[name]={'path':command[0],'sha256':sha(Path(command[0])),'version':subprocess.check_output(command,text=True).strip()}
    toolchain['python']={'path':sys.executable,'sha256':sha(Path(sys.executable)),'version':sys.version}
    toolchain['native_kernel_sha256']=read(native/'run.json')['kernel_sha256'];save(out/'host-compiler.json',toolchain)
    save(out/'test.json',{'native_test_revision':options['native_test_revision'],'calls':read(native/'generated-cases.json'),'unsupported':read(native/'target-checks.json')})
    sources=list((ROOT/'tests/wasm/stage1').rglob('*'))+[ROOT/'tests/wasm/stage0/diagnostics/reporter.mjs',ROOT/'doc/WASM/tools/r6_registration.py',ROOT/'tests/wasm/native-census/observer.lisp',ROOT/'tests/wasm/native-baseline/tests.lisp',ROOT/'xdump/faslenv.lisp',ROOT/'level-0/nfasload.lisp',ROOT/'level-1/l1-reader.lisp']
    pins={}
    for p in sorted(set(sources)):
        if not p.is_file() or '__pycache__' in p.parts:continue
        name=str(p.relative_to(ROOT));dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest);pins[name]=sha(p)
    save(out/'source-pins.json',pins)
    files=[]
    def artifact(path,role):files.append({'path':path,'role':role,'sha256':sha(out/path)})
    for path,role in [('native/registered.image','image'),('qualification/wasm32-backend.dx64fsl','compiler'),('host-compiler.json','host-compiler'),('schemas/abi.json','abi'),('schemas/tcr.json','schema'),('schemas/layout.json','schema'),('options.json','options'),('test.json','test'),('native/target.log','log'),('source-pins.json','implementation')]:artifact(path,role)
    for name in pins:artifact('source/'+name,'implementation')
    cases=read(native/'generated-cases.json');names=sorted({c['name'] for c in cases});entries=[]
    for i,name in enumerate(names,1):
        shutil.copy(native/(name+'.wasm'),out/'installed'/(name+'.wasm'))
        for suffix,role in [('lisp','source'),('wat','template'),('wasm','module')]:artifact('native/'+name+'.'+suffix,role)
        artifact('installed/'+name+'.wasm','installed-binary')
        entries.append({'name':name,'logical_code_id':i,'slot':i,'entry_kind':'B','signature':'(i32,i32)->(i32,i32)','source':'native/'+name+'.lisp','template':'native/'+name+'.wat','module':'native/'+name+'.wasm','binary':'installed/'+name+'.wasm'})
    manifest={'version':1,'profile':'stage1-full-one-worker-leaf','files':files,'entries':entries};save(out/'build.json',manifest)
    reporter=ROOT/'tests/wasm/stage0/diagnostics/reporter.mjs';commands=[]
    def execute(name,reporter):
        dest=out/(name+'.json');argv=['/usr/local/bin/node',str(HERE/'execute.mjs'),str(out),str(reporter),str(dest)];commands.append({'name':name,'argv':argv});save(out/'commands.json',commands)
        with (out/(name+'.log')).open('w') as log:p=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=180)
        commands[-1]['exit_code']=p.returncode;save(out/'commands.json',commands)
        return p.returncode,dest
    code,result=execute('execution',reporter);require(code==0,'POSITIVE_DRIVER '+str(out/'execution.log'))
    disasm=subprocess.check_output(['/usr/local/bin/wasm-objdump','-d',str(out/'native/identity.wasm')],text=True);(out/'identity.disassembly').write_text(disasm)
    summary=assess(read(result),manifest,disasm);mutants=[]
    substitutions={
      'wrong-code':('logical_code_id:fn.logical_code_id','logical_code_id:fn.logical_code_id+1'),
      'wrong-slot':('slot:fn.slot','slot:fn.slot+1'),
      'wrong-signature':('signature:fn.signature',"signature:'(i32)->(i32)'"),
      'wrong-operation':('operation:op.name',"operation:'last-observed'"),
      'wrong-offset':('binary_offset:offset','binary_offset:offset+1'),
      'overwrite-first':('report.first_failure ??= diagnostic','report.first_failure = diagnostic'),
      'unbounded-output':('report.errors.length<MAX_ERRORS','true'),
      'skip-unreadable-top':('if(!match)break;','if(!match)continue;')}
    original=reporter.read_text()
    for name,(old,new) in substitutions.items():
        require(original.count(old)==1,'MUTANT_SITE '+name);mutant=out/'controls'/(name+'.mjs');mutant.write_text(original.replace(old,new))
        code,result=execute('controls/'+name,mutant)
        if code==0:
            try:assess(read(result),manifest,disasm)
            except ValueError as e:reason=str(e)
            else:raise ValueError('MUTANT_ESCAPED '+name)
        else:
            text=(out/('controls/'+name+'.log')).read_text();require('AssertionError' in text,'MUTANT_HARNESS_FAILURE '+name);reason='semantic assertion (retained log)'
        mutants.append({'name':name,'status':'REJECTED','reason':reason})
    save(out/'summary.json',{'status':'PASS',**summary,'diagnostic_mutants':mutants,'native_fasl_controls':read(qualification/'verification.json')['controls'],'scope':'Initial generated leaf build only. Host compiler image is bound; a target bootstrap image does not yet exist. V8 stack parser; no browser stack claim.'})
    print('S1-1A-BUILD-PASS',json.dumps({k:v for k,v in read(out/'summary.json').items() if k not in ('diagnostic_mutants','native_fasl_controls')}))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('native','qualification','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();run(a.native.resolve(),a.qualification.resolve(),a.output.resolve())
