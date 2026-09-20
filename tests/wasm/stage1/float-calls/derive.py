from pathlib import Path
from backend import HERE,ROOT,replace

def loader():
 s=(ROOT/'runtime/wasm32/loader.mjs').read_text()
 s=replace(s,"import {admitNumericCapabilities} from './numeric-capabilities.mjs';", "import {admitNumericCapabilities} from './numeric-capabilities.mjs';\nimport {admitFloatingCapabilities} from './floating-capabilities.mjs';\nexport const FLOAT_PROFILE='wasm32-shared-B-floating-owner-v1';")
 s=s.replace('[PROFILE,OWNER_PROFILE,NUMERIC_PROFILE]','[PROFILE,OWNER_PROFILE,NUMERIC_PROFILE,FLOAT_PROFILE]')
 s=replace(s,'const numeric=record.profile===NUMERIC_PROFILE,','const floating=record.profile===FLOAT_PROFILE,numeric=floating||record.profile===NUMERIC_PROFILE,')
 s=replace(s,'(numeric?2:ownerRetry?1:0)','(floating?3:numeric?2:ownerRetry?1:0)')
 s=replace(s,"    else if(i.module!=='env')", "    else if(i.module==='floating')need(floating&&i.name==='calculate'&&i.kind==='function'&&same(i.signature,{params:['i32','i32','i32'],results:['i32']}),'FLOAT_IMPORT');\n    else if(i.module!=='env')")
 s=replace(s,"  if(numeric)need(", "  if(floating)need(keys.has('floating.calculate'),'FLOAT_IMPORT_SET');\n  if(numeric)need(")
 s=replace(s,'    if(r.profile===NUMERIC_PROFILE){', "    if(r.profile===FLOAT_PROFILE){\n      const bundle=admitFloatingCapabilities(o.floatingCapabilities,clean.env);\n      need(clean.owner?.ensure===bundle.ensure&&clean.integer?.calculate===bundle.integer&&clean.floating?.calculate===bundle.floating,'FLOAT_IMPORT_CAPABILITY');\n    }else{\n    need(!clean.floating,'UNEXPECTED_FLOAT_CAPABILITY');\n    if(r.profile===NUMERIC_PROFILE){")
 s=replace(s,'    row.imports=clean;', '    }\n    row.imports=clean;')
 return s

def execute():
 s=(HERE.parent/'integer-condition-review/execute.mjs').read_text()
 s=replace(s,"import {CollectorOwner} from './collector-owner.mjs';import {integerService} from './service.mjs';", "import {CollectorOwner} from './collector-owner.mjs';import {floatingCapabilities} from './floating-capabilities.mjs';\nimport {LazyLoader,validate,FLOAT_PROFILE,NUMERIC_PROFILE,sha} from './loader.mjs';")
 s=replace(s,'integerPath,output]','integerPath,output,mode]')
 s=replace(s,"[{module:'integer',name:'calculate',kind:'function'}]","[{module:'floating',name:'calculate',kind:'function'},{module:'integer',name:'calculate',kind:'function'},{module:'owner',name:'ensure',kind:'function'}]")
 s=replace(s,', {high:false,collect:true,tiny:true}',', {high:false,collect:true,tiny:true}') if False else s
 s=replace(s,',{high:false,collect:true,tiny:true},{high:true,collect:true,tiny:true}','')
 s=replace(s,'store(p+28,0);return p+6;','store(p+20,0);store(p+28,0);return p+6;')
 s=replace(s,"const masks=[1,9,31,39,71,393,519,527,1031,2055,4099,7,8199,16391,49159];", "const masks=[1,9,31,39,71,393,519,527,1031,2055,4099,7,8199,16391,49159,81927,147463,278535,540679];")
 s=replace(s,"'ARITHMETIC-ERROR','DIVISION-BY-ZERO'];", "'ARITHMETIC-ERROR','DIVISION-BY-ZERO','FLOATING-POINT-INVALID-OPERATION','FLOATING-POINT-OVERFLOW','FLOATING-POINT-UNDERFLOW','FLOATING-POINT-INEXACT'];")
 s=replace(s,"['OPERATION','OPERANDS','STATUS']];", "['OPERATION','OPERANDS','STATUS'],...Array.from({length:4},()=>['OPERATION','OPERANDS','STATUS'])];")
 s=replace(s,'assert.equal(shapes.length,15)','assert.equal(shapes.length,19)')
 s=replace(s,"for(const [i,n] of ['condition_handlers','condition_restarts','debugger_hook'].entries())", "for(const [i,n] of ['condition_handlers','condition_restarts','debugger_hook','dyn_a'].entries())")
 a=s.index(' const owner=CollectorOwner.create(');b=s.index(' const encode=',a)
 s=s[:a]+''' const owner=CollectorOwner.create(memory,bytes,digest,layout);let moves=0,growths=0,ensures=0;
 const originalEnsure=owner.ensure.bind(owner);
 owner.ensure=n=>{
  ensures++;const from=t(56),spaces=owner.spaces;
  if(collect){for(let p=t(48);p<t(52);p+=8){store(p,NIL);store(p+4,0);}set(48,t(52));}
  let value,error;try{value=originalEnsure(n);}catch(e){error=e;}
  if(t(56)!==from){const grew=!spaces.some(s=>s.start===t(56));moves+=grew?2:1;if(grew)growths++;for(const s of spaces)if(s.start!==t(56))new Uint8Array(memory.buffer,s.start,s.end-s.start).fill(0xdd);}
  if(error)throw error;return value;
 };
 const inputs=read('service-inputs.json');
 const bundle=floatingCapabilities({memory,tcr,owner,callError:call_error,integerBytes,integerDigest,bytes:fs.readFileSync(dir+'/float.wasm'),digest:inputs.float,detectorBytes:fs.readFileSync(dir+'/detector.wasm'),detectorDigest:inputs.detector,pinned:images});
 const imports={env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},symbols,keywords,codes,integer:{calculate:bundle.integer},owner:{ensure:bundle.ensure},floating:{calculate:bundle.floating}};
 const catalog=mods.map((m,i)=>{const b=fs.readFileSync(dir+'/compiled/'+m.name+'.wasm'),info=inspect(b,{ownerRetry:true});return {name:m.name,slot:i+1,code:i+1,version:4,signature:17,role:23,profile:FLOAT_PROFILE,sha256:sha(b),imports:info.imports,entries:Object.fromEntries(info.exports.map(e=>[e.name,{index:e.index,role:e.name}]))};});
 const options={...imports.env,catalog,stub:new WebAssembly.Module(fs.readFileSync(dir+'/stub.wasm')),floatingCapabilities:bundle,readBytes:n=>fs.readFileSync(dir+'/compiled/'+n+'.wasm')};
 const entries={};let loader;
 if(mode==='cold'){
  loader=new LazyLoader(options);for(const m of mods)entries[m.name]=loader.defer(m.name,imports).host_entry;
 }else for(const [i,m] of mods.entries()){
  const instance=new WebAssembly.Instance(modules.get(m.name),imports);entries[m.name]=instance.exports.entry;table.set(i+1,instance.exports.entry);tail_table.set(i+1,instance.exports.tail_entry);
 }
''' +s[b:]
 s=replace(s,"const encode=s=>{if(s==='nil')", """const encode=s=>{if(s.startsWith('f')){const wide=s.startsWith('f64:'),raw=BigInt('0x'+s.slice(4)),p=t(48),size=wide?16:8;assert(p+size<=t(52));store(p,wide?791:271);store(p+4,wide?0:Number(raw));if(wide){store(p+8,Number(raw&0xffffffffn));store(p+12,Number(raw>>32n));}set(48,p+size);return p+6;}if(s.startsWith('cons:')){const car=encode(s.slice(5)),p=t(48);store(p,NIL);store(p+4,car);set(48,p+8);return p+1;}if(s==='NIL')""")
 s=replace(s,"if(s==='t')return T;", "if(s==='T')return T;")
 s=replace(s,"assert.equal(h%256,7);let x=0n;", """if(h===271||h===791){const wide=h===791,raw=wide?(BigInt(get(p+12))<<32n)|BigInt(get(p+8)):BigInt(get(p+4)),exp=wide?0x7ff0000000000000n:0x7f800000n,frac=wide?0xfffffffffffffn:0x7fffffn;if((raw&exp)===exp&&(raw&frac)!==0n)return 'nan';return (wide?'f64:':'f32:')+raw.toString(16).padStart(wide?16:8,'0');}assert.equal(h%256,7);let x=0n;""")
 s=replace(s,'  const before=slow;let pair;', '  if(loader)loader.reset();set(200,c.mask);const before=ensures;let pair;')
 a=s.index("  if(['n_add'");b=s.index('\n }\n if(!tiny)',a)
 s=s[:a]+'''  for(let i=3;i<=6;i++)assert.equal(get(t(104)+4*i),243,'binding vector restored');
  rows.push({high,collect,id:c.id,function:c.function,values,assurances:ensures-before});''' +s[b:]
 a=s.index(' if(!tiny){');b=s.index('\n}\nfs.writeFileSync(output',a)
 s=s[:a]+''' rows.push({high,collect,cases:native.length,ensures,moves,growths,modules:mods.length});
 if(!high&&!collect){
  const first=catalog[0],binary=options.readBytes(first.name);validate(binary,first);
  assert.throws(()=>validate(binary,{...first,profile:NUMERIC_PROFILE}),/OWNER_IMPORT_COUNT/);
  const clean=()=>{for(let i=1;i<table.length;i++){table.set(i,null);tail_table.set(i,null);}};
  for(const [name,change,why] of [
   ['missing-bundle',{floatingCapabilities:undefined},'FLOATING_CAPABILITY'],
   ['copied-bundle',{floatingCapabilities:{...bundle}},'FLOATING_CAPABILITY']]){
   clean();const l=new LazyLoader({...options,...change});assert.throws(()=>l.defer(first.name,imports),new RegExp(why));
  }
  clean();assert.throws(()=>new LazyLoader(options).defer(first.name,{...imports,floating:{calculate:(...a)=>bundle.floating(...a)}}),/FLOAT_IMPORT_CAPABILITY/);
  rows.push({loaderChecks:4,frozen:Object.isFrozen(bundle)});
 }
''' +s[b:]
 return s
