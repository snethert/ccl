import fs from 'node:fs';import assert from 'node:assert/strict';
export async function install({dir,memory,tcr,get,put,service,collector,config,result,collect,calculateI,calculateF,ensure}){
 const NIL=77825,registry=4096,table=new WebAssembly.Table({element:'anyfunc',initial:2048}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:2048});
 const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const env={memory,tcr,table,tail_table,code_registry:registry,call_error,type_error,nonlocal_exit},symbols={},keywords={},codes={},functions=new Map(),entries=new Map();
 const mods=JSON.parse(fs.readFileSync(dir+'/compiled/modules.json')),material=JSON.parse(fs.readFileSync(dir+'/compiled/materialized.json'));
 new Uint8Array(memory.buffer,2097152,material.image.length/2).set(Buffer.from(material.image,'hex'));let cursor=2097152+material.image.length/2,symbolNext=850000;
 function object(id,pool){const p=cursor;cursor+=32;[1578,id*4,NIL,4,NIL,NIL,pool,0].forEach((v,i)=>put(p+4*i,v));return p+6;}
 function symbol(name){if(symbols[name])return symbols[name];const p=symbolNext;symbolNext+=32;[1850,NIL,NIL,NIL,NIL,NIL,NIL,0].forEach((v,i)=>put(p+4*i,v));return symbols[name]=p+6;}
 const owners=JSON.parse(fs.readFileSync(dir+'/compiled/symbols.json')),ownerWords=new Map(),wordOwners=new Map(),extraRoots=[];
 owners.forEach((row,i)=>{const p=600000+32*i;[1850,NIL,NIL,NIL,NIL,0,NIL,row.package===null?0:4*(i+1)].forEach((v,j)=>put(p+4*j,v));ownerWords.set(row.id,p+6);wordOwners.set(p+6,{symbol:row.id});for(const offset of [4,8,12,16,24])extraRoots.push(p+offset);});
 for(const name of ['list','alist']){keywords[name]=symbol('keyword_'+name);put(keywords[name]-2,keywords[name]);}
 put(registry,2048);put(registry+4,1);
 function register(id,instance){[id,4,17,23].forEach((v,i)=>put(registry+8+16*id+4*i,v));table.set(id,instance.exports.entry);tail_table.set(id,instance.exports.tail_entry);}
 const eql=(await WebAssembly.instantiate(fs.readFileSync(dir+'/eql.wasm'),{env:{memory}})).instance.exports;const hash={run:eql.ht_eql,collect:()=>{throw Error('unexpected EQL collection');},config:0,operation:3,scratch:1800000,scratch_end:1860000,result:1169504};
 const compiled=[];
 for(let i=0;i<mods.length;i++){
  const row=mods[i],wasm=await WebAssembly.compile(fs.readFileSync(dir+'/compiled/'+(row.name==='collector_probe'?'collector_probe_hook':row.name)+'.wasm')),id=i+8;
  codes[row.name]=id*4;functions.set(row.name,object(id,material.roots[i]));if((row.name==='core_gf_identity'||row.name.startsWith('core_key_'))){const raw=functions.get(row.name)-6;put(raw+16,get(material.roots[i]-2));put(raw+20,get(material.roots[i]+2));}compiled.push({row,wasm,id});
  for(const item of WebAssembly.Module.imports(wasm))if(item.module==='symbols')symbol(item.name);
 }
 for(const [name,self] of functions)put(symbol(name)+6,self);
 for(const row of mods)if(row.function)put(ownerWords.get(row.function)+6,functions.get(row.name));
 for(const self of functions.values())extraRoots.push(self+10,self+14,self+18);
  const shapes=JSON.parse(fs.readFileSync(dir+'/compiled/native-condition-classes.json'));
 const masks=[1,9,31,39,71,393,519,527,1031,2055,4099,7,8199,16391,49159,81927,147463,278535,540679,1048583,3145735,4194311,8388615,25165839,34603015,67108903,134217799,268435527];
 function vector(words,tag=250){const p=cursor;cursor+=8*Math.ceil((4+4*words.length)/8);put(p,words.length*256+tag);words.forEach((w,i)=>put(p+4+4*i,w));if(!(words.length&1))put(p+4+4*words.length,0);return p+6;}
 function string(text){return vector(Array.from(text).map(c=>c.codePointAt(0)),191);}
 assert.equal(shapes.length,masks.length);
 symbols.condition_registry=vector(shapes.map((shape,i)=>{
   const name=symbol('class_'+shape.name),fields=vector(shape.slots.map((s,j)=>symbol('slot_'+i+'_'+j)));
   const defaults=vector(shape.slots.map(s=>s.default===null?NIL:typeof s.default==='string'?string(s.default):83));
   const instance=cursor;cursor+=16;[882,0,NIL,NIL].forEach((v,j)=>put(instance+4*j,v));
   put(instance+12,vector([instance+6,name,NIL],106));
   const wrapper=vector([name,4*i,instance+6,fields,NIL,NIL,NIL,NIL,NIL,NIL,NIL,4*i,masks[i]*4]);
   return vector([wrapper,masks[i]*4,defaults]);
 }));
 symbols.error_message=string('Checked Lisp runtime operation failed.');

 owners.forEach((row,i)=>put(600000+32*i+4,string(row.name)));
 [1850,string('T'),77838,NIL,NIL,8,NIL,0].forEach((v,i)=>put(77832+4*i,v));
 [1850,string('NIL'),NIL,NIL,NIL,8,NIL,0].forEach((v,i)=>put(77864+4*i,v));

 for(const {row,wasm,id} of compiled){const instance=new WebAssembly.Instance(wasm,{env,hash,owner:{ensure},probe:{collect},integer:{calculate:calculateI},floating:{calculate:calculateF},symbols:{...symbols,...Object.fromEntries(row.symbols.map(([wire,id])=>[wire,ownerWords.get(id)]))},keywords,codes});register(id,instance);entries.set(row.name,{fn:instance.exports.entry,self:functions.get(row.name)});}
 let invocations=0;
 return {functions,mods,env,symbols,keywords,codes,call_error,imageEnd:cursor,symbolEnd:symbolNext,ownerEnd:600000+32*owners.length,keywords,ownerWords,wordOwners,extraRoots,
  reset(mat){
   new Uint8Array(memory.buffer,get(tcr+56),mat.image.length/2).set(Buffer.from(mat.image,'hex'));
   put(tcr+48,get(tcr+56)+mat.image.length/2);
   mods.forEach((row,i)=>{const self=functions.get(row.name);put(self+18,mat.roots[i]);if((row.name==='core_gf_identity'||row.name.startsWith('core_key_'))){put(self+10,get(mat.roots[i]-2));put(self+14,get(mat.roots[i]+2));}});
   put(tcr+104,650000);put(tcr+108,1024);
   for(let i=0;i<1024;i++)put(650000+4*i,243);
   owners.forEach((row,i)=>{let value=NIL;
    if(row.package==='COMMON-LISP'&&row.name==='*READ-BASE*')value=40;
    if(row.package==='COMMON-LISP'&&row.name==='*PRINT-LEVEL*')value=28;
    if(row.package==='COMMON-LISP'&&row.name==='*PRINT-LENGTH*')value=36;
    if(row.package===null)value=51;if(row.package==='CCL'&&row.name==='%TYPE-ERROR-TYPESPECS%')value=mat.roots[mods.length];if(row.package==='CCL'&&row.name==='*PRINT-STRING-LENGTH*')value=44;
    if(row.package==='CCL'&&row.name==='$NHASH.VECTOR_OVERHEAD')value=56;
    if(row.package==='CCL'&&row.name==='*PATHNAME-ESCAPE-CHARACTER*')value=92*256+75;put(600000+32*i+24,NIL);if(row.package==='KEYWORD')value=ownerWords.get(row.id);
    put(600000+32*i+8,value);
   });
  },
  invoke(name,args){const entry=entries.get(name),incoming=132096,output=132352,owner=132512;
   put(tcr+64,incoming);put(tcr+116,0);put(tcr+120,output);put(tcr+124,owner);args.forEach((v,i)=>put(incoming+4*i,v));
   const bindings=Array.from({length:1024},(_,i)=>get(650000+4*i));
   const before=Array.from({length:64},(_,i)=>get(tcr+4*i));let pair;
   let failure;try{pair=entry.fn(entry.self,args.length);}catch(e){failure=e;}
   for(let i=0;i<64;i++)if(![48,52,56,116].includes(i*4))assert.equal(get(tcr+4*i),before[i],name+' restored TCR '+i*4);
   assert.deepEqual(Array.from({length:1024},(_,i)=>get(650000+4*i)),bindings,name+' restored bindings');
   if(failure){assert.equal(get(tcr+116),before[29],name+' failed MV count');throw Error(name+': '+(failure.is?.(call_error)?'checked '+failure.getArg(call_error,0):failure.is?.(type_error)?'type_error '+failure.getArg(type_error,0):failure));}assert.equal(pair[1]>>>0,get(tcr+116),name+' result count');assert.equal(pair[0]>>>0,pair[1]?get(output):NIL,name+' primary');invocations++;
   const values=Array.from({length:pair[1]>>>0},(_,i)=>get(output+i*4));put(tcr+116,0);return values;
  },summary(){return {invocations,modules:mods.length,delivery:[]};}
 };
}
