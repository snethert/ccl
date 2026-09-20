import argparse,importlib.util,json,shutil,sys,subprocess
from pathlib import Path
from backend import generate
from corpus import SOURCES,cases
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];C=HERE.parent/'constants'
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(argv,log):
 save(log.with_suffix('.command.json'),list(map(str,argv)))
 with log.open('w') as f:subprocess.run(list(map(str,argv)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
def compile(e,out,code=None):
 out.mkdir(parents=True,exist_ok=False);h=out/'driver';shutil.copytree(C,h,ignore=shutil.ignore_patterns('__pycache__','review-followup'));shutil.copy(HERE/'compile.lisp',h/'compile.lisp');shutil.copy(HERE/'class-shapes.lisp',h/'class-shapes.lisp')
 (h/'runtime.lisp').write_text("'("+'\n'.join('('+json.dumps(n)+' '+s+')' for n,s in SOURCES.items())+')\n')
 rows=cases();save(out/'cases.json',rows);(h/'cases.lisp').write_text('('+ '\n'.join('('+json.dumps(r['function'])+' ('+' '.join(('('+x['cons']+')') if isinstance(x,dict) else x for x in r['args'])+'))' for r in rows)+')\n')
 p=h/'compile.py';p.write_text(p.read_text().replace("ROOT=HERE.parents[3];REG=HERE.parent/'registration'",'ROOT=Path('+repr(str(ROOT))+');REG=Path('+repr(str(HERE.parent/'registration'))+')'))
 old=sys.path.copy();sys.path.insert(0,str(h));spec=importlib.util.spec_from_file_location('integer_compile',p);driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver);driver.run(e,out/'compiled',code or generate());sys.path[:]=old
 sys.path.insert(0,str(C));from pool import compile_pool
 sys.path[:]=old
 graph=json.loads((out/'compiled/pools.json').read_text());symbols={};plan=compile_pool(graph,symbols);m=plan.at(786432);save(out/'compiled/materialized.json',dict(base=786432,image=m.image.hex(),roots=m.roots,symbols=symbols))
 native=(out/'compiled/native-results.txt').read_text().splitlines();assert len(native)==len(rows);save(out/'native.json',[dict(c,expected=line.split(',')) for c,line in zip(rows,native)])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--qualify',action='store_true');a=p.parse_args();compile(a.evidence.resolve(),a.output.resolve())

 if a.qualify:
  import controls
  controls.run(a.evidence.resolve(),a.output.resolve(),sys.modules[__name__])
