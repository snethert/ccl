import os,argparse,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
from backend import generate,replace
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def command(argv,log,env=None):
 with log.open('w') as f:subprocess.run(list(map(str,argv)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300,env=env)
def prepare(out):
 # Import the accepted runner with its own backend, then replace only the
 # proposed compiler in this disposable fixture. Never write shared source.
 sys.path.insert(0,str(HERE.parent/'collector-live'))
 live=load('retry_live_runner',HERE.parent/'collector-live/run.py');h=live.prepare(out)
 (h/'wasm32-backend.lisp').write_text(generate());shutil.copy(HERE/'probe.py',h/'retry_probe.py');shutil.copy(HERE.parent/'allocation-retry/probe.py',h/'inherited_retry_probe.py')
 for name in ['compile.lisp','root-contracts.lisp']:
  p=h/name;p.write_text(p.read_text().replace('wasm32-compiler::compile-call-module','wasm32-compiler::compile-retrying-call-module'))
 return h

def run(e,out,qualify=False):
 out.mkdir(parents=True,exist_ok=False);h=prepare(out/'harness')
 accepted=e/'2026-09-19-stage1-collector-live-r1'
 assert (HERE/'allocation-service.mjs').read_bytes()==(ROOT/'runtime/wasm32/allocation-service.mjs').read_bytes()
 for n in ['collector.c','collector.wasm']:assert (h/n).read_bytes()==(accepted/n).read_bytes(),n
 command([sys.executable,h/'retry_probe.py',e,out/'compiled',h/'wasm32-backend.lisp'],out/'compile.log')
 for n in ['execute.mjs','allocation-service.mjs','binary.mjs','loader.mjs','loader-controls.mjs']:shutil.copy(HERE/n,out/n)
 shutil.copy(ROOT/'runtime/wasm32/collector-owner.mjs',out/'collector-owner.mjs')
 command(['/usr/local/bin/wat2wasm','--enable-tail-call',h/'stub.wat','-o',out/'stub.wasm'],out/'stub.log')
 command(['/usr/local/bin/node',out/'execute.mjs',out/'compiled',h/'collector.wasm',out/'execution.json'],out/'execution.log')
 result=json.loads((out/'execution.json').read_text())
 load('constructor_pressure',HERE/'instrument.py').run(out/'compiled',out/'pressure')
 command(['/usr/local/bin/node',out/'execute.mjs',out/'pressure',h/'collector.wasm',out/'pressure.json'],out/'pressure.log',dict(os.environ,CONSTRUCTOR_PRESSURE='1'))
 result['pressure']=json.loads((out/'pressure.json').read_text());pressure_rows=result['pressure'].pop('rows')
 result['pressure']['constructor_entries']=[sum(r.get('constructors',[0,0,0])[i] for r in pressure_rows) for i in range(3)]
 assert all(result['pressure']['constructor_entries']),'each raw constructor executed under forced shortage'
 command(['/usr/local/bin/node',out/'execute.mjs',out/'compiled',h/'collector.wasm',out/'lazy.json'],out/'lazy.log',dict(os.environ,LAZY_OWNER='1'))
 assert json.loads((out/'lazy.json').read_text())==json.loads((out/'execution.json').read_text()),'eager/cold owner equality'
 result['lazy_comparisons']=result['comparisons']
 command(['/usr/local/bin/node',out/'execute.mjs',out/'compiled',h/'collector.wasm',out/'nested.json'],out/'nested.log',dict(os.environ,LAZY_OWNER='1',OWNER_NESTED='1',RETRY_CASE='pair'))
 result['nested_refusals']=json.loads((out/'nested.json').read_text())['resource_refusals']
 if qualify:
  result['compiler_mutants']=len(load('retry_controls',HERE/'controls.py').run(e,out/'controls',h,out/'execute.mjs')['mutants'])
  command([sys.executable,HERE/'compatibility.py',e,out/'compatibility'],out/'compatibility.log')
  result['default_mode']=json.loads((out/'compatibility/compatibility.json').read_text())
 shutil.copy(ROOT/'runtime/wasm32/binary.mjs',out/'legacy-binary.mjs')
 command(['/usr/local/bin/node',out/'loader-controls.mjs',out/'compiled',out/'stub.wasm',out/'loader-controls']+([out/'compatibility/default'] if qualify else []),out/'loader-controls.log')
 result['loader_controls']=json.loads((out/'loader-controls/controls.json').read_text())['checks']
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='rows'})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--qualify',action='store_true');a=p.parse_args();run(a.evidence.resolve(),a.output.resolve(),a.qualify)
