import argparse,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
from backend import generate,ROOT
HERE=Path(__file__).resolve().parent;C=HERE.parent/'constants'
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def load(name,path):
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
def run(e,out,backend=None):
 out.mkdir(parents=True,exist_ok=False)
 load('metadata_compile_driver',HERE/'compile.py').run(e,out/'compiled',backend)
 oldpath=sys.path.copy();sys.path.insert(0,str(C));from pool import compile_pool
 sys.path[:]=oldpath
 graph=json.loads((out/'compiled/pools.json').read_text());keys=sorted({v['symbol'] for obj in graph['objects'] for v in obj['value'].get('elements',[]) if 'symbol' in v})
 symbols={k:620006+32*i for i,k in enumerate(keys)}
 plan=compile_pool(graph,symbols);material=plan.at(1048576)
 save(out/'compiled/materialized.json',dict(base=material.base,image=material.image.hex(),roots=material.roots,objects=[dict(id=i,offset=o,tag=t) for i,o,t in plan.objects],symbols=symbols))
 for n in ['execute.mjs','snapshot-controls.mjs']:shutil.copy(HERE/n,out/n)
 for n in ['loader.mjs','binary.mjs']:shutil.copy(ROOT/'runtime/wasm32'/n,out/n)
 for n in ['snapshot.mjs','transport.mjs']:
  s=(C/n).read_text().replace("new URL('../../../../doc/WASM/contracts/wasm32-layout.v1.json', import.meta.url)",repr(str(ROOT/'doc/WASM/contracts/wasm32-layout.v1.json')))
  if n=='snapshot.mjs':
   s=s.replace('export const digest', "tags.function = schema.subtags.find(x => x.name === 'subtag-function').value;\nexport const digest")
   s=s.replace("if (tag === tags['simple-vector']) payload = 4*count;", "if (tag === tags.function) {check(count === 6, 'function count'); payload = 4*count;}\n      else if (tag === tags['simple-vector']) payload = 4*count;")
   s=s.replace("if (tag === tags['simple-vector']) for", "if (tag === tags.function || tag === tags['simple-vector']) for")
  (out/n).write_text(s)
 command(['/usr/local/bin/wat2wasm','--enable-tail-call',ROOT/'runtime/wasm32/stub.wat','-o',out/'stub.wasm'],out/'stub.log')
 command(['/usr/local/bin/node',out/'execute.mjs',out/'compiled',out/'execution.json'],out/'execution.log')
 command(['/usr/local/bin/node',out/'snapshot-controls.mjs',out/'compiled/snapshot.json',out/'snapshot-controls.json'],out/'snapshot-controls.log')
 print('PASS: callable metadata at three placements')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--qualify',action='store_true');a=p.parse_args();e=a.evidence.resolve();out=a.output.resolve();run(e,out)
 if a.qualify:
  load('metadata_mutants',HERE/'controls.py').run(e,out/'mutants',run)
  load('metadata_runtime_mutants',HERE/'runtime-controls.py').run(out,out/'runtime-mutants')
  load('metadata_compatibility',HERE/'compatibility.py').run(e,out/'compatibility')

 if a.qualify:
  result=load('metadata_assessment',HERE/'assessment.py').run(out,out/'assessment');save(out/'summary.json',result);print(result)
