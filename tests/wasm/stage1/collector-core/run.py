import argparse,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
from backend import generate,replace
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('gc_ll17_runner',HERE.parent/'binding-vector/run.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
CLANG='/usr/local/opt/llvm/bin/clang'
FLAGS=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer']
def command(argv,log):
 with log.open('w') as f:subprocess.run(list(map(str,argv)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
def prepare(out):
 prior.generate=generate;h=prior.prepare(out);(h/'wasm32-backend.lisp').write_text(generate())
 shutil.copy(HERE/'collector.c',h/'collector.c');shutil.copy(HERE/'check.mjs',h/'core-check.mjs')
 command([CLANG,*FLAGS,h/'collector.c','-o',h/'collector.wasm'],h/'collector-build.log')
 shutil.copy(HERE/'probe.py',h/'collector_probe.py')
 p=h/'conditions.mjs';s=p.read_text()
 s=replace(s,'const dv=new DataView(memory.buffer);','const dv=new DataView(memory.buffer);const collector=await WebAssembly.instantiate(await WebAssembly.compile(fs.readFileSync('+json.dumps(str(h/"collector.wasm"))+')),{env:{memory}});')
 s=replace(s,'let relocations=0,','let collectionOrigin=0;let relocations=0,')
 s=replace(s,'currentControlCase=c;relocations=0;','currentControlCase=c;relocations=0;collectionOrigin=heap;')
 s=replace(s,(HERE.parent/'binding-vector/observer.mjs').read_text(),(HERE/'observe.mjs').read_text().replace('setCollector=','const setCollector='))
 # Moving objects naturally change physical locations; the same semantic oracle
 # runs, but allocated range/tail checks follow the published active semispace.
 s=replace(s,'x>=heap+6&&x+26<=get(48)','x>=get(56)+6&&x+26<=get(48)')
 s=replace(s,'x>=heap+1&&x+7<=get(48)&&(x-heap-1)%8===0','x>=get(56)+1&&x+7<=get(48)&&(x-get(56)-1)%8===0')
 s=replace(s,"assert(get(48)>=heap&&get(48)<=heapLimit,c.id+': allocation within owner extent');assert(new Uint8Array(memory.buffer,get(48),heapLimit-get(48)).every(x=>x===0xcd),c.id+': heap tail untouched');", "assert(get(48)>=get(56)&&get(48)<=get(52),c.id+': allocation within current semispace');")
 p.write_text(s);return h

def run(e,out):
 out.mkdir(parents=True,exist_ok=False);h=prepare(out/'harness')
 shutil.copy(h/'collector.wasm',out/'collector.wasm')
 command(['/usr/local/bin/node',h/'core-check.mjs',h/'collector.wasm',out/'core-checks.json'],out/'core.log')
 command([sys.executable,h/'collector_probe.py',e,out/'generated',h/'wasm32-backend.lisp'],out/'generated.log')
 r=json.loads((out/'generated/execution.json').read_text());assert r['comparisons']==56
 # Only observed runs install the boundary observer: two placements, thirteen polls.
 assert len(r['moved_vectors'])==34,(len(r['moved_vectors']),r['moved_vectors'])
 spec=importlib.util.spec_from_file_location('core_mutants',HERE/'mutants.py');mutants=importlib.util.module_from_spec(spec);spec.loader.exec_module(mutants)
 controls=mutants.run(h,out/'mutants',CLANG,FLAGS,HERE/'check.mjs')
 spec=importlib.util.spec_from_file_location('core_unbind',HERE/'unbind.py');unbind=importlib.util.module_from_spec(spec);spec.loader.exec_module(unbind);unbind.run(out/'unbind')
 stale=generate();old='(b-wat "(i32.load offset=~d (i32.sub (i32.load offset=2 (i32.load offset=40 (local.get $context))) (i32.const 6)))" (+ 4 (* 4 n)))';new='(b-wat "(i32.load offset=~d (local.get $closure_env))" (+ 4 (* 4 n)))';assert stale.count(old)==1
 (out/'stale-environment.lisp').write_text(stale.replace(old,new))
 try:command([sys.executable,h/'collector_probe.py',e,out/'stale-environment',out/'stale-environment.lisp'],out/'stale-environment.log')
 except subprocess.CalledProcessError:
  failure=out/'stale-environment/execution.log';assert failure.exists() and 'g_live_closure: checked failure, not engine trap' in failure.read_text()
 else:raise AssertionError('stale environment escaped')
 stale=generate();old='(let ((self (if (eq op \'b-self) "(i32.load offset=40 (local.get $context))"';new='(let ((self (if (eq op \'b-self) "(local.get $self)"';assert stale.count(old)==1
 (out/'stale-self.lisp').write_text(stale.replace(old,new))
 try:command([sys.executable,h/'collector_probe.py',e,out/'stale-self',out/'stale-self.lisp'],out/'stale-self.log')
 except subprocess.CalledProcessError:
  failure=out/'stale-self/execution.log';assert failure.exists() and 'g_recursive: native/logical result' in failure.read_text() and 'DESIGNATOR' in failure.read_text()
 else:raise AssertionError('stale self escaped')
 result=dict(status='PASS',modules=r['modules'],comparisons=r['comparisons'],collections=len(r['moved_vectors']),checks=len(json.loads((out/'core-checks.json').read_text())['tests']),collector_mutants=len(controls),compiler_controls=3,scope='Auxiliary collector core, not full LL18 qualification')
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
