"""Requalify every installation rule against this generated compiler corpus."""
import importlib.util,sys,shutil,subprocess
from pathlib import Path
from support import HERE,read,save,require
LAZY=HERE.parent/'b-lazy-calls'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def run(positive,lazy,out):
 out.mkdir();sys.path.insert(0,str(LAZY))
 tools=load('ll05_lazy_run',LAZY/'run.py');mutants=load('ll05_lazy_mutants',LAZY/'mutants.py')
 for p in lazy.iterdir():
  if p.is_file() and p.suffix in ('.mjs','.json','.wasm'):shutil.copy(p,out/p.name)
 for n in ('modules.json','cases.json','root-contracts.json'):shutil.copy(positive/n,out/n)
 shutil.copy(HERE/'stub.wat',out/'stub.wat')
 (out/'installed').symlink_to(positive/'installed',target_is_directory=True)
 base=out/'base';base.mkdir();(base/'positive').symlink_to(positive,target_is_directory=True)
 s=(LAZY/'controls.mjs').read_text().replace('initial:8,maximum:32769','initial:16,maximum:32769')
 s=s.replace(" const call_error=new WebAssembly.Tag", " const nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});\n const call_error=new WebAssembly.Tag")
 s=s.replace('tail_table,call_error,stub','tail_table,call_error,nonlocal_exit,stub').replace('call_error,type_error}', 'call_error,type_error,nonlocal_exit}')
 s=s.replace(' const options={', ''' symbols.condition_handlers=600006;
 store(600000,1850);store(600008,77825);store(600028,4);
 store(256+104,610000);store(256+108,2);store(610000,243);store(610004,243);
 const options={''')
 # Compiled calls use internal stubs; exercise public stubs explicitly with
 # a freshly created closure whose SELF is semantically necessary.
 public_probe="""{const h=setup();h.init([28]);let closure;
 assert.doesNotThrow(()=>{closure=h.pairs.get('factory').entry(h.self('factory'),1)[0];},'public stub count');
 const cursor=h.view.getUint32(256+48,true),code=h.view.getUint32(closure-2,true)/4;
 const record=catalog.find(r=>r.code===code);assert(record,'closure code identity');
 h.init([]);h.store(256+48,cursor);
 assert.doesNotThrow(()=>assert.deepEqual(h.pairs.get(record.name).entry(closure,0),[28,1]),'public stub closure self');
 assert.equal(h.view.getUint32(73728,true),28,'public stub value delivery');
 results.push({name:'public-stub-count-and-closure-self',status:'PASS'});}
"""
 s=s.replace('const install=h=>',public_probe+'const install=h=>')
 (out/'controls.mjs').write_text(s)
 original_mutations=mutants.mutations
 def mutations(folder):
  rows=original_mutations(folder)
  for name in ('stub-drops-self','stub-drops-count'):
   file,text,_=rows[name];rows[name]=(file,text,'controls')
  return rows
 mutants.mutations=mutations
 try:
  tools.malformed(base,out)
  require(tools.command(['/usr/local/bin/node',str(out/'controls.mjs'),str(out),str(out/'full-controls.json')],out,'full-controls')==0,'FULL_LOADER '+str(out/'full-controls.log'))
  rows=mutants.run(out,tools.command)
  result=dict(status='PASS',cases=len(read(out/'full-controls.json')['cases']),mutants=len(rows));save(out/'summary.json',result);return result
 finally:
  for p in list(out.rglob('*')):
   if p.is_symlink():p.unlink()
  sys.path.remove(str(LAZY))
if __name__=='__main__':
 print(run(*[Path(a).resolve() for a in sys.argv[1:]]))
