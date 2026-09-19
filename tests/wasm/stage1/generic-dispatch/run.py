"""Generated aliases/redefinition through the accepted, unchanged compiler."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];C=HERE.parent/'constants';PARENT='2026-09-19-stage1-binding-installation-r1'
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
def run(e,out,backend=None,runtime=None):
 out.mkdir(parents=True,exist_ok=False);code=(backend or load('gd_backend',HERE/'backend.py').generate()).encode()
 h=out/'driver';shutil.copytree(C,h,ignore=shutil.ignore_patterns('__pycache__','development','review-followup'));shutil.copy(HERE/'compile.lisp',h/'compile.lisp');shutil.copy(HERE/'runtime.lisp',h/'runtime.lisp');shutil.copy(HERE/'oracle.lisp',h/'oracle.lisp');shutil.copy(HERE/'class-shapes.lisp',h/'class-shapes.lisp')
 p=h/'compile.py';p.write_text(p.read_text().replace("ROOT=HERE.parents[3];REG=HERE.parent/'registration'",'ROOT=Path('+repr(str(ROOT))+');REG=Path('+repr(str(HERE.parent/'registration'))+')'))
 if runtime is not None:(h/'runtime.lisp').write_text(runtime)
 oldpath=sys.path.copy();sys.path.insert(0,str(h));driver=load('binding_compile_driver',p);driver.run(e,out/'compiled',code.decode());sys.path[:]=oldpath
 oldpath=sys.path.copy();sys.path.insert(0,str(C));from pool import compile_pool
 sys.path[:]=oldpath
 graph=json.loads((out/'compiled/pools.json').read_text());symbols={};plan=compile_pool(graph,symbols)
 for base in [1048576,2147483648]:
  material=plan.at(base);save(out/'compiled'/('materialized-'+str(base)+'.json'),dict(base=base,image=material.image.hex(),roots=material.roots,symbols=symbols))
 for n in ['execute.mjs']:shutil.copy(HERE/n,out/n)
 for n in ['loader.mjs','binary.mjs','installer.mjs','ranges.mjs']:shutil.copy(ROOT/'runtime/wasm32'/n,out/n)
 command(['/usr/local/bin/wat2wasm','--enable-tail-call',ROOT/'runtime/wasm32/stub.wat','-o',out/'stub.wasm'],out/'stub.log')
 command(['/usr/local/bin/node',out/'execute.mjs',out/'compiled',out/'execution.json'],out/'execution.log');print('PASS: generated generic dispatch')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--qualify',action='store_true');a=p.parse_args();out=a.output.resolve();e=a.evidence.resolve();run(e,out)
 if a.qualify:
  load('gd_controls',HERE/'controls.py').run(e,out,out/'mutants',run)
  command([sys.executable,HERE/'compatibility.py','--evidence',a.evidence.resolve(),'--output',out/'compatibility'],out/'compatibility.log')
  save(out/'summary.json',load('gd_assessment',HERE/'assessment.py').run(out,out/'assessment'))
