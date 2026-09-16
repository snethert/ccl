#!/usr/bin/env python3
"""Complete the retained R6 run with independent controls and clean-image replays.

run.py performs the three native builds. This command consumes that retained
run, qualifies it, and is the inventory entry point. It never edits a checkout.
"""
import argparse,hashlib,json,os,shutil,subprocess,tarfile,tempfile
from pathlib import Path
from unit import HERE,ROOT,Unit,sha,save
from check import verify,require,read

def qualify(output,inputs,kernel,destination):
    require(not destination.exists(),'NEVER_OVERWRITE');destination.mkdir(parents=True)
    require(read(output/'run.json')['status']=='PASS','NATIVE_RUN_REQUIRED')
    require(sha(kernel)==read(output/'run.json')['kernel_sha256'],'KERNEL_IDENTITY')
    pins=read(inputs/'pins.json');require(pins==read(output/'run.json')['inputs'],'INPUT_PIN_JOIN')
    for name,digest in pins['inputs'].items():require(sha(inputs/name)==digest,'INPUT_BYTES '+name)
    commands=[]
    with tempfile.TemporaryDirectory(prefix='ccl-stage1-replay-') as tmp:
        work=Path(tmp).resolve();source=work/'ccl';source.mkdir();save(work/'stage1-disposable.json',{'purpose':'verification'})
        with tarfile.open(inputs/'source.tar') as t:t.extractall(source,filter='data')
        with tarfile.open(inputs/'bootstrap.tar.gz') as t:t.extractall(source,filter='data')
        shutil.copy(kernel,source/'dx86cl64');(source/'dx86cl64').chmod(0o755)
        def lisp(name,loads,extra):
            argv=[str(source/'dx86cl64'),'--no-init','--batch']
            for p in loads:argv+=['--load',str(p)]
            env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin','LANG':'C','LC_ALL':'C','CCL_DEFAULT_DIRECTORY':str(source),**extra}
            commands.append({'name':name,'argv':argv,'cwd':str(source),'environment':env});save(destination/'commands.json',commands)
            with (destination/(name+'.log')).open('w') as log:p=subprocess.run(argv,cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
            commands[-1]['exit_code']=p.returncode;save(destination/'commands.json',commands)
            marker='S1-OPERATORS-PASS' if name.endswith('operators') else 'S1-TARGET-PASS'
            require(p.returncode==0 and marker in (destination/(name+'.log')).read_text(),'NATIVE_REPLAY '+name)
        shutil.copy(output/'baseline.image',source/'dx86cl64.image')
        lisp('baseline-operators',[ROOT/'tests/wasm/native-census/observer.lisp',HERE/'operators.lisp'],{'S1_OPERATORS':str(destination/'baseline-operators.json')})
        with Unit(source,output/'proposal'):
            shutil.copy(output/'registered.image',source/'dx86cl64.image')
            lisp('registered-operators',[HERE/'load.lisp',ROOT/'tests/wasm/native-census/observer.lisp',HERE/'operators.lisp'],{'S1_OPERATORS':str(destination/'registered-operators.json')})
            require((destination/'baseline-operators.json').read_bytes()==(destination/'registered-operators.json').read_bytes(),'R6A_MATRIX')
            lisp('target-replay',[HERE/'load.lisp',HERE/'smoke.lisp'],{'S1_OUTPUT':str(destination)+'/'})
            for name in ('wasm32-arch','wasm32-backend','xwasm32fasload'):
                shutil.copy(source/'bin'/(name+'.dx64fsl'),destination/(name+'.dx64fsl'))
            for p in destination.glob('*.wat'):require(p.read_bytes()==(output/p.name).read_bytes(),'EMISSION_REPLAY '+p.name)
            for name in ('generated-cases.json','target-checks.json'):require((destination/name).read_bytes()==(output/name).read_bytes(),'TARGET_REPLAY '+name)
    command=['/usr/local/bin/python3',str(HERE/'execute.py'),'--output',str(destination)]
    # Use the same interpreter that runs the qualifier, never a PATH alias.
    import sys
    command[0]=sys.executable;commands.append({'name':'wasm-replay','argv':command});save(destination/'commands.json',commands)
    with (destination/'wasm-replay.log').open('w') as log:p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    require(p.returncode==0,'WASM_REPLAY')
    for p in destination.glob('*.wasm'):require(p.read_bytes()==(output/p.name).read_bytes(),'BINARY_REPLAY')
    require((destination/'execution.json').read_bytes()==(output/'execution.json').read_bytes(),'EXECUTION_REPLAY')
    result=verify(output,inputs);save(destination/'verification.json',result)
    save(destination/'summary.json',{'status':'PASS','native':result['summary'],'negative_controls':len(result['controls']),'architecture_operator_tables':5,'replayed_generated_modules':len(list(destination.glob('*.wasm')))})
    print('S1-QUALIFICATION-PASS',json.dumps(read(destination/'summary.json')))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('output','inputs','kernel','destination'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();qualify(a.output.resolve(),a.inputs.resolve(),a.kernel.resolve(),a.destination.resolve())
