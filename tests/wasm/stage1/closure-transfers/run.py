import argparse,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
from backend import generate,ROOT
HERE=Path(__file__).resolve().parent
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def command(argv,log):
 save(log.with_suffix('.command.json'),list(map(str,argv)))
 with log.open('w') as f:subprocess.run(list(map(str,argv)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
def prepare(out):
 old=load('transfers_harness',HERE.parent/'temporaries/run.py');h=old.prepare(out)
 (h/'wasm32-backend.lisp').write_text(generate());shutil.copy(HERE/'probe.py',h/'transfer_probe.py');shutil.copy(HERE/'refusals.py',h/'transfer_refusals.py');return h

def run(e,out,qualify=False):
 out.mkdir(parents=True,exist_ok=False);h=prepare(out/'harness')
 command([sys.executable,h/'transfer_probe.py',e,out/'generated',h/'wasm32-backend.lisp'],out/'execution.log')
 r=json.loads((out/'generated/execution.json').read_text());summary=dict(status='PASS',modules=r['modules'],comparisons=r['comparisons'],collections=len(r['moved_vectors']))
 command([sys.executable,h/'temporary_probe.py',e,out/'inherited',h/'wasm32-backend.lisp'],out/'inherited.log')
 summary['inherited_comparisons']=json.loads((out/'inherited/execution.json').read_text())['comparisons']
 shape=load('transfer_shapes',HERE/'shape.py').inspect(out/'generated/compiled');save(out/'shape.json',shape);summary['shape_checks']=len(shape)
 compat=load('transfer_compatibility',HERE/'compatibility.py').check(e,out/'inherited/compiled');save(out/'compatibility.json',compat);summary['unchanged_nonloop_files']=compat['files']
 if qualify:
  command([sys.executable,h/'transfer_refusals.py',e,out/'refusals',h/'wasm32-backend.lisp'],out/'refusals.log')
  summary['source_refusals']=len(json.loads((out/'refusals/refusals.json').read_text()))
  summary['mutants']=len(load('transfer_controls',HERE/'controls.py').run(e,out/'mutants',h,command))
 save(out/'summary.json',summary)
 if qualify:load('transfer_assessment',HERE/'assessment.py').run(out,out/'assessment')
 print(summary)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--qualify',action='store_true');a=p.parse_args();run(a.evidence.resolve(),a.output.resolve(),a.qualify)
