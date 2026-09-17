"""Cold-install the identical condition modules with the reviewed loader."""
from pathlib import Path
import shutil,subprocess
from support import HERE,require,read,save

def run(positive,expected,out,call_errors=False):
 out.mkdir()
 s="import {LazyLoader} from './loader.mjs';\n"+(HERE/'conditions.mjs').read_text()
 if call_errors:
  a=s.index("  for(const fault of ['fixnum'");b=s.index('\n }\n}',a);s=s[:a]+s[b:]
 a=s.index(' for(const m of mods){\n  const codes=');b=s.index('\n function installObjects(){',a)
 # Keep independent entry inspection while replacing only installation.
 t=s[a:b];aobs=t.index('observe:(self,n,context)=>')+len('observe:');bobs=t.index('}}}}).exports.entry:tail);')
 tail=t[aobs:bobs]+'}}'
 replace=''' for(let i=0;i<table.length;i++){table.set(i,null);tail_table.set(i,null);}
 const loader=new LazyLoader({catalog:read('catalog.json'),memory,table,tail_table,call_error,nonlocal_exit,
   stub:new WebAssembly.Module(fs.readFileSync(path.join(dir,'lazy-stub.wasm'))),observer,tailObserver,
   readBytes:name=>fs.readFileSync(path.join(dir,'installed',name+'.wasm'))});
 for(const m of mods){
  const codes=Object.fromEntries(mods.map((m,i)=>[m.name,4*(i+1)]));
  const pair=loader.defer(m.name,{env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},symbols,keywords,codes},
    observed?{entry:()=>{publicDispatches++;assert.fail('compiled public entry');},tail_entry:TAIL}:null);
  functions.set(m.name,pair.host_entry);
 }
'''.replace('TAIL',tail)
 s=s[:a]+replace+s[b:];s=s.replace(' function installObjects(){',' function installObjects(){\n  loader.reset();')
 (out/'harness.mjs').write_text(s)
 for name in ('loader.mjs','binary.mjs','catalog.mjs'):shutil.copy(HERE/name,out/name)
 for name in ('installed','modules.json','cases.json','root-contracts.json'):(out/name).symlink_to(positive/name)
 commands=[['/usr/local/bin/wat2wasm','--enable-tail-call',str(HERE/'stub.wat'),'-o',str(out/'lazy-stub.wasm')],['/usr/local/bin/node',str(out/'catalog.mjs'),str(out),str(out/'catalog.json')],['/usr/local/bin/node',str(out/'harness.mjs'),str(out),str(out/'execution.json')]]
 save(out/'commands.json',commands)
 try:
  for i,cmd in enumerate(commands):
   with (out/(str(i)+'.log')).open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=180)
   require(r.returncode==0,'CONDITION_LAZY '+str(out/(str(i)+'.log')))
  want=read(expected);got=read(out/'execution.json')
  require(got==want,'CONDITION_LAZY_ORACLE')
  summary=dict(status='PASS',comparisons=got['comparisons'],modules=got['modules'],refusals=len(got['condition_refusals']))
  save(out/'summary.json',summary);return summary
 finally:
  for name in ('installed','modules.json','cases.json','root-contracts.json'):(out/name).unlink()
