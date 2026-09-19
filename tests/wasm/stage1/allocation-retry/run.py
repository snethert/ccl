import argparse,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
from backend import generate,replace
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def command(argv,log):
 with log.open('w') as f:subprocess.run(list(map(str,argv)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
def prepare(out):
 # Import the accepted runner with its own backend, then replace only the
 # proposed compiler in this disposable fixture. Never write shared source.
 sys.path.insert(0,str(HERE.parent/'collector-live'))
 live=load('retry_live_runner',HERE.parent/'collector-live/run.py');h=live.prepare(out)
 (h/'wasm32-backend.lisp').write_text(generate());shutil.copy(HERE/'probe.py',h/'retry_probe.py')
 for name in ['compile.lisp','root-contracts.lisp']:
  p=h/name;p.write_text(p.read_text().replace('wasm32-compiler::compile-call-module','wasm32-compiler::compile-retrying-call-module'))
 return h

def run(e,out,qualify=False):
 out.mkdir(parents=True,exist_ok=False);h=prepare(out/'harness')
 accepted=e/'2026-09-19-stage1-collector-live-r1'
 for n in ['collector.c','collector.wasm']:assert (h/n).read_bytes()==(accepted/n).read_bytes(),n
 command([sys.executable,h/'retry_probe.py',e,out/'compiled',h/'wasm32-backend.lisp'],out/'compile.log')
 for n in ['execute.mjs','allocation-service.mjs']:shutil.copy(HERE/n,out/n)
 shutil.copy(ROOT/'runtime/wasm32/collector-owner.mjs',out/'collector-owner.mjs')
 shutil.copy(ROOT/'runtime/wasm32/binary.mjs',out/'binary.mjs')
 command(['/usr/local/bin/node',out/'execute.mjs',out/'compiled',h/'collector.wasm',out/'execution.json'],out/'execution.log')
 result=json.loads((out/'execution.json').read_text())
 if qualify:
  result['compiler_mutants']=len(load('retry_controls',HERE/'controls.py').run(e,out/'controls',h,out/'execute.mjs')['mutants'])
  command([sys.executable,HERE/'compatibility.py',e,out/'compatibility'],out/'compatibility.log')
  result['default_mode']=json.loads((out/'compatibility/compatibility.json').read_text())
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='rows'})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--qualify',action='store_true');a=p.parse_args();run(a.evidence.resolve(),a.output.resolve(),a.qualify)
