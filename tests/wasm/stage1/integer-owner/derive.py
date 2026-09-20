"""Anchored runtime and test overlays; the integrated compiler is unchanged."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
COMPILER='d328c6bc7882631d98bb49a878110c3b90b691583405a021e79ebef1f9192df4'
PINS={
 'runtime/wasm32/loader.mjs':'9a5ddd004c2150ffacc9a1417fcfa290edea5ad9d68237c5855e193af4dc62e3',
 'runtime/wasm32/collector-owner.mjs':'d986bd397fb9fc9e73dde7afdb820085af100d336e951907f79430e885d00761',
}
def pinned(path):
 s=(ROOT/path).read_text();assert hashlib.sha256(s.encode()).hexdigest()==PINS[path],path;return s
def replace(s,a,b,n=1):
 assert s.count(a)==n,(a,s.count(a),n);return s.replace(a,b)
def compiler():
 s=(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text();assert hashlib.sha256(s.encode()).hexdigest()==COMPILER;return s
def owner():
 return replace(pinned('runtime/wasm32/collector-owner.mjs'),' get view(){',' get tcr(){return this.#layout.tcr;}\n get view(){')
def loader():
 s=pinned('runtime/wasm32/loader.mjs')
 s=replace(s,"import {inspect} from './binary.mjs';","import {inspect} from './binary.mjs';\nimport {admitNumericCapabilities} from './numeric-capabilities.mjs';")
 s=replace(s,"export const OWNER_PROFILE=", "export const NUMERIC_PROFILE='wasm32-shared-B-integer-owner-v1';\nexport const OWNER_PROFILE=")
 s=replace(s,'[PROFILE,OWNER_PROFILE]','[PROFILE,OWNER_PROFILE,NUMERIC_PROFILE]')
 s=replace(s,'const ownerRetry=record.profile===OWNER_PROFILE;','const numeric=record.profile===NUMERIC_PROFILE,ownerRetry=numeric||record.profile===OWNER_PROFILE;')
 s=replace(s,'(ownerRetry?1:0)','(numeric?2:ownerRetry?1:0)')
 s=replace(s,"else if(i.module!=='env')", "else if(i.module==='integer')need(numeric&&i.name==='calculate'&&i.kind==='function'&&same(i.signature,{params:['i32','i32'],results:['i32']}),'INTEGER_IMPORT');\n    else if(i.module!=='env')")
 s=replace(s,"  need(same(m.imports,record.imports)","  if(numeric)need(keys.has('owner.ensure')&&keys.has('integer.calculate'),'NUMERIC_IMPORT_SET');\n  need(same(m.imports,record.imports)")
 s=replace(s,"    if(r.profile===OWNER_PROFILE)","    need([PROFILE,OWNER_PROFILE,NUMERIC_PROFILE].includes(r.profile),'PROFILE');\n    if(r.profile===NUMERIC_PROFILE){\n      const bundle=admitNumericCapabilities(o.numericCapabilities,clean.env);\n      need(clean.owner?.ensure===bundle.ensure&&clean.integer?.calculate===bundle.calculate,'NUMERIC_IMPORT_CAPABILITY');\n    }else{\n    need(!clean.integer,'UNEXPECTED_INTEGER_CAPABILITY');\n    if(r.profile===OWNER_PROFILE)")
 s=replace(s,"    row.imports=clean;", "    }\n    row.imports=clean;")
 s=replace(s,'// No start, segments or getters; the sole admitted function import is\n      // the owner allocation capability. Instantiation cannot','// No start, segments or getters. The admitted functions are trusted\n      // owner capabilities. Instantiation cannot')
 return s
def execute():
 s=(HERE.parent/'integer-condition-review/execute.mjs').read_text()
 s=replace(s,"import {CollectorOwner} from './collector-owner.mjs';import {integerService} from './service.mjs';", "import {CollectorOwner} from './collector-owner.mjs';import {numericCapabilities} from './numeric-capabilities.mjs';\nimport {LazyLoader,validate,NUMERIC_PROFILE,sha} from './loader.mjs';\nimport {admissionControls} from './admission.mjs';")
 s=replace(s,'store(p+28,0);return p+6;','store(p+20,0);store(p+28,0);return p+6;')
 s=replace(s,'integerPath,output]','integerPath,output,mode]')
 s=replace(s,"[{module:'integer',name:'calculate',kind:'function'}]","[{module:'integer',name:'calculate',kind:'function'},{module:'owner',name:'ensure',kind:'function'}]")
 s=replace(s,'{high:false,collect:true,tiny:true},{high:true,collect:true,tiny:true}', '{high:false,collect:true,tiny:true},{high:true,collect:true,tiny:true}')
 s=replace(s,"[{module:'integer',name:'calculate',kind:'function'},{module:'owner',name:'ensure',kind:'function'}]", "[{module:'integer',name:'calculate',kind:'function'},{module:'owner',name:'ensure',kind:'function'},...(mode==='pressure'?[{module:'pressure',name:'fill',kind:'function'}]:[])]")
 s=replace(s,'for(const [i,n] of [\'condition_handlers\',\'condition_restarts\',\'debugger_hook\'].entries())if(symbols[n])store(symbols[n]+22,4*(i+3));',"const bindingIndices={condition_handlers:31,condition_restarts:127,debugger_hook:255,dyn_a:63};\n for(const [n,i] of Object.entries(bindingIndices))if(symbols[n])store(symbols[n]+22,4*i);")
 a=s.index(' const owner=CollectorOwner.create(');b=s.index(' const encode=',a)
 s=s[:a]+''' const owner=CollectorOwner.create(memory,bytes,digest,layout);
 let moves=0,growths=0,ensures=0,pendingKind=0;const requests=[],pressureCounts={1:0,2:0,3:0};
 const originalEnsure=owner.ensure.bind(owner);
 owner.ensure=n=>{
  ensures++;const kind=pendingKind;pendingKind=0;const from=t(56),spaces=owner.spaces,liveBefore=t(48)-from;
  if(collect){for(let p=t(48);p<t(52);p+=8){store(p,NIL);store(p+4,0);}set(48,t(52));}
  let answer,error;try{answer=originalEnsure(n);}catch(e){error=e;}
  const moved=t(56)!==from,grew=moved&&!spaces.some(s=>s.start===t(56));
  if(moved){moves+=grew?2:1;if(grew)growths++;for(const s of spaces)if(s.start!==t(56))new Uint8Array(memory.buffer,s.start,s.end-s.start).fill(0xdd);}
  requests.push({bytes:n,kind,liveBefore,moved,grew,refused:!!error});if(error)throw error;return answer;
 };
 const bundle=numericCapabilities({memory,tcr,owner,callError:call_error,bytes:integerBytes,digest:integerDigest,pinned:images});
 const imports={env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},symbols,keywords,codes,owner:{ensure:bundle.ensure},integer:{calculate:bundle.calculate}};
 if(mode==='pressure')imports.pressure={fill:kind=>{pressureCounts[kind]++;pendingKind=kind;for(let p=t(48);p<t(52);p+=8){store(p,NIL);store(p+4,0);}set(48,t(52));}};
 const catalog=mods.map((m,i)=>{const b=fs.readFileSync(dir+'/compiled/'+m.name+'.wasm'),info=inspect(b,{ownerRetry:true});return {name:m.name,slot:i+1,code:i+1,version:4,signature:17,role:23,profile:NUMERIC_PROFILE,sha256:sha(b),imports:info.imports,entries:Object.fromEntries(info.exports.map(e=>[e.name,{index:e.index,role:e.name}]))};});
 const stub=new WebAssembly.Module(fs.readFileSync(dir+'/stub.wasm'));
 const options={...imports.env,catalog,stub,numericCapabilities:bundle,readBytes:name=>fs.readFileSync(dir+'/compiled/'+name+'.wasm')};
 if(mode!=='pressure'&&!high&&!collect&&!tiny)admissionControls({dir,options,imports,owner,integerBytes,integerDigest,images,mode});
 if(mode==='pressure')for(const r of catalog)assert.throws(()=>validate(options.readBytes(r.name),r),/OWNER_IMPORT_COUNT/);
 const installationHash=()=>sha(Buffer.concat([...regions,...images,...layout.spaces].map(r=>Buffer.from(new Uint8Array(memory.buffer,r.start,r.end-r.start)))));
 const entries={};let loader;
 if(mode==='cold'){
  loader=new LazyLoader(options);const before=installationHash();
  for(const m of mods)entries[m.name]=loader.defer(m.name,imports).host_entry;
  // Force every catalog member through admission, including inner modules.
  for(const r of catalog)loader.install(r.slot);
  assert.equal(ensures,0,'instantiation called owner');assert.equal(installationHash(),before,'instantiation wrote memory');
 }else for(const [i,m] of mods.entries()){
  const instance=new WebAssembly.Instance(modules.get(m.name),imports);entries[m.name]=instance.exports.entry;table.set(i+1,instance.exports.entry);tail_table.set(i+1,instance.exports.tail_entry);
 }
''' +s[b:]
 s=replace(s,"const encode=s=>{if(s==='nil')", "const encode=s=>{if(s==='dyn_a')return symbols.dyn_a;if(s==='nil')")
 s=replace(s,'  set(48,t(56));set(64,ROOT+8);set(128,ROOT);set(120,OUT);set(124,OUT+64);set(140,0);', '  if(loader)loader.reset();set(104,266240);set(108,8);for(let i=0;i<8;i++)store(266240+4*i,243);\n  set(48,t(56));set(64,ROOT+8);set(128,ROOT);set(120,OUT);set(124,OUT+64);set(140,0);')
 s=replace(s,'  const before=slow;let pair;',"  if(collect&&!tiny){for(let p=t(48);p<t(52);p+=8){store(p,NIL);store(p+4,0);}set(48,t(52));}\n  const before=ensures;let pair;")
 a=s.index("  if(['n_add'");b=s.index('\n }\n if(!tiny)',a)
 s=s[:a]+'''  for(const i of Object.values(bindingIndices))if(i<t(108))assert.equal(get(t(104)+4*i),243,'binding vector restored');
  rows.push({high,collect,tiny:!!tiny,id:c.id,function:c.function,values,assurances:ensures-before});''' +s[b:]
 # Refusal subcases do not need the previous invocation's evacuated binding vector.
 s=replace(s,' if(!tiny){',' set(104,266240);set(108,8);\n if(!tiny){')
 s=replace(s,"  assert.equal(new Set(fast).size,6);rows.push({high,collect,cases:native.length,slow,moves,growths,modules:mods.length,refusals,nested:6,inline_checks:fast.length,inline_operations:[...new Set(fast)].sort()});", "  rows.push({high,collect,cases:native.length,ensures,moves,growths,modules:mods.length,refusals,nested:6,...(mode==='pressure'?{pressureCounts}: {})});")
 s=replace(s,"  // Refuse a host attempt", """  for(const name of ['e_restart','e_owner_special','e_type_left']){
   if(loader)loader.reset();set(104,266240);set(108,8);set(48,t(56));set(64,ROOT+8);set(128,ROOT);set(140,0);set(148,0);set(120,OUT);set(124,OUT+64);store(ROOT+4,2);store(ROOT+8,28);store(ROOT+12,12);
   // The type case needs a nonnumeric operand. The other two enter binding
   // growth before their body; every path attempts an owner entry.
   const count=name==='e_owner_special'?2:1;store(ROOT+4,count);if(name==='e_type_left')store(ROOT+8,NIL);
   for(let p=t(48);p<t(52);p+=8){store(p,NIL);store(p+4,0);}set(48,t(52));
   let refused;try{owner.atSafepoint(()=>entries[name](handles[name],count));}catch(e){assert(e.is?.(call_error));refused=e.getArg(call_error,0);}
   assert.equal(refused,6,'nested '+name);assert.equal(t(128),ROOT);assert.equal(t(64),ROOT+8);assert.equal(t(140),0);
   refusals.push({name:'nested-'+name,code:6});
  }
  // Refuse a host attempt""")
 s=replace(s,'cases:1,slow,moves,growths','cases:1,ensures,moves,growths')
 s=replace(s,'}\nfs.writeFileSync(output'," if(mode==='pressure'&&!tiny){for(const kind of [1,2,3])assert(requests.some(r=>r.kind===kind&&r.moved),'constructor '+kind+' did not collect');}\n fs.writeFileSync(dir+'/'+mode+'-'+Number(high)+'-'+Number(collect)+'-'+Number(!!tiny)+'-assurances.json',JSON.stringify(requests,null,2)+'\\n');\n}\nfs.writeFileSync(output")
 return s
