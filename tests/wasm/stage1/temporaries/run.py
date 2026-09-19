import argparse,importlib.util,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from backend import generate,ROOT
HERE=Path(__file__).resolve().parent
CLANG='/usr/local/opt/llvm/bin/clang'
FLAGS=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer']
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def command(argv,log):
 save(log.with_suffix('.command.json'),list(map(str,argv)))
 with log.open('w') as f:subprocess.run(list(map(str,argv)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
def prepare(out):
 sys.path.insert(0,str(HERE.parent/'constructor-retry'))
 retry=load('temporary_harness',HERE.parent/'constructor-retry/run.py');h=retry.prepare(out)
 (h/'wasm32-backend.lisp').write_text(generate())
 for n in ['compile.lisp','root-contracts.lisp']:
  p=h/n;p.write_text(p.read_text().replace('compile-retrying-call-module','compile-call-module'))
 shutil.copy(ROOT/'runtime/wasm32/collector.c',h/'collector.c');command([CLANG,*FLAGS,h/'collector.c','-o',h/'collector.wasm'],h/'collector-build.log')
 shutil.copy(HERE/'probe.py',h/'temporary_probe.py');shutil.copy(HERE/'refusals.py',h/'temporary_refusals.py');return h

def run(e,out,qualify=False):
 out.mkdir(parents=True,exist_ok=False);h=prepare(out/'harness')
 command([sys.executable,h/'temporary_probe.py',e,out/'generated',h/'wasm32-backend.lisp'],out/'execution.log')
 r=json.loads((out/'generated/execution.json').read_text());summary=dict(status='PASS',modules=r['modules'],comparisons=r['comparisons'],collections=len(r['moved_vectors']))
 if qualify:
  command([sys.executable,h/'temporary_refusals.py',e,out/'refusals',h/'wasm32-backend.lisp'],out/'refusals.log')
  summary['source_refusals']=len(json.loads((out/'refusals/refusals.json').read_text()))
  summary['mutants']=len(load('temporary_controls',HERE/'controls.py').run(e,out/'mutants',h,command))
  # Recompile the reviewed opt-in constructor corpus, whose language is unchanged.
  compat=out/'compat-harness';shutil.copytree(h,compat,ignore=shutil.ignore_patterns('__pycache__'))
  for n in ['compile.lisp','root-contracts.lisp']:
   p=compat/n;p.write_text(p.read_text().replace('compile-call-module','compile-retrying-call-module'))
  command([sys.executable,compat/'retry_probe.py',e,out/'compatibility',h/'wasm32-backend.lisp'],out/'compatibility.log')
  count=0
  with tarfile.open(e/'2026-09-19-stage1-collector-qualification-r1/execution.tar.gz') as archive:
   for member in archive.getmembers():
    n=Path(member.name)
    if len(n.parts)==2 and n.parts[0]=='generated' and n.suffix in ('.wat','.wasm'):
     assert archive.extractfile(member).read()==(out/'compatibility'/n.name).read_bytes(),n.name;count+=1
  assert count==152;summary['inherited_identical']=count
 save(out/'summary.json',summary)
 if qualify:load('temporary_assessment',HERE/'assessment.py').run(out,out/'assessment')
 print('PASS',summary)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--qualify',action='store_true');a=p.parse_args();run(a.evidence.resolve(),a.output.resolve(),a.qualify)
