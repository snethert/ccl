"""Focused qualification of the new exit-tag capability and module profile."""
import shutil,subprocess
from support import HERE,save,read,require

def run(positive,out):
 require(not out.exists(),'NO_OVERWRITE');out.mkdir(parents=True)
 for name in ('loader.mjs','binary.mjs'):shutil.copy(HERE/name,out/name)
 subprocess.run(['/usr/local/bin/wat2wasm','--enable-tail-call',str(HERE/'stub.wat'),'-o',str(out/'stub.wasm')],check=True)
 source=(HERE/'loader.mjs').read_text()
 replacements={
 'distinct-tag':("need(options.nonlocal_exit instanceof WebAssembly.Tag&&options.nonlocal_exit!==options.call_error,'DISTINCT_EXIT_TAG');",''),
 'imported-tag':('&&clean.env.nonlocal_exit===o.nonlocal_exit',''),
 'profile':("need(record.profile===PROFILE,'PROFILE');",''),
 'binary-tag':("need(same(fixed,expected),'ENV_IMPORTS');",'')}
 commands=[];controls=[]
 for name,edit in [('positive',None)]+list(replacements.items()):
  target=out/(name+'.mjs')
  if edit:
   old,new=edit;require(source.count(old)==1,'MUTANT_SELECTOR');target.write_text(source.replace(old,new))
  else:target=out/'loader.mjs'
  argv=['/usr/local/bin/node',str(HERE/'loader_controls.mjs'),str(positive),str(out/(name+'.json')),str(target),str(out/'stub.wasm')];commands.append(argv)
  with (out/(name+'.log')).open('w') as log:p=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=60)
  if edit:require(p.returncode!=0 and 'AssertionError' in (out/(name+'.log')).read_text(),'LOADER_MUTANT '+name);controls.append({'name':name,'status':'REJECTED'})
  else:require(p.returncode==0,'LOADER_POSITIVE '+str(out/(name+'.log')))
 save(out/'commands.json',commands);result={'status':'PASS','positive':read(out/'positive.json'),'mutants':controls};save(out/'summary.json',result);return result
