import fs from 'node:fs';import assert from 'node:assert/strict';
export async function install({dir,memory,tcr,get,put,service,collector,config,result,collect}){
 const NIL=77825,registry=4096,table=new WebAssembly.Table({element:'anyfunc',initial:128}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:128});
 const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const env={memory,tcr,table,tail_table,code_registry:registry,call_error,type_error,nonlocal_exit},symbols={},keywords={},codes={},functions=new Map(),entries=new Map();
 const mods=JSON.parse(fs.readFileSync(dir+'/compiled/modules.json')),material=JSON.parse(fs.readFileSync(dir+'/compiled/materialized.json'));
 new Uint8Array(memory.buffer,2097152,material.image.length/2).set(Buffer.from(material.image,'hex'));let cursor=2097152+material.image.length/2,symbolNext=620000;
 function object(id,pool){const p=cursor;cursor+=32;[1578,id*4,NIL,4,NIL,NIL,pool,0].forEach((v,i)=>put(p+4*i,v));return p+6;}
 function symbol(name){if(symbols[name])return symbols[name];const p=symbolNext;symbolNext+=32;[1850,NIL,NIL,NIL,NIL,NIL,NIL,0].forEach((v,i)=>put(p+4*i,v));return symbols[name]=p+6;}
 const owners=JSON.parse(fs.readFileSync(dir+'/compiled/symbols.json')),ownerWords=new Map(),wordOwners=new Map(),extraRoots=[];
 owners.forEach((row,i)=>{const p=600000+32*i;[1850,NIL,NIL,NIL,NIL,0,NIL,4*(i+1)].forEach((v,j)=>put(p+4*j,v));ownerWords.set(row.id,p+6);wordOwners.set(p+6,{symbol:row.id});extraRoots.push(p+8);});
 for(const name of ['list','alist']){keywords[name]=symbol('keyword_'+name);put(keywords[name]-2,keywords[name]);}
 put(registry,128);put(registry+4,1);
 function register(id,instance){[id,4,17,23].forEach((v,i)=>put(registry+8+16*id+4*i,v));table.set(id,instance.exports.entry);tail_table.set(id,instance.exports.tail_entry);}
 const compiled=[];
 for(let i=0;i<mods.length;i++){
  const row=mods[i],wasm=await WebAssembly.compile(fs.readFileSync(dir+'/compiled/'+(row.name==='collector_probe'?'collector_probe_hook':row.name)+'.wasm')),id=i+8;
  codes[row.name]=id*4;functions.set(row.name,object(id,material.roots[i]));compiled.push({row,wasm,id});
  for(const item of WebAssembly.Module.imports(wasm))if(item.module==='symbols')symbol(item.name);
 }
 for(const [name,self] of functions)put(symbol(name)+6,self);
 for(const row of mods)if(row.function)put(ownerWords.get(row.function)+6,functions.get(row.name));
 for(const self of functions.values())extraRoots.push(self+18);
 for(const {row,wasm,id} of compiled){const instance=new WebAssembly.Instance(wasm,{env,probe:{collect},symbols:{...symbols,...Object.fromEntries(row.symbols.map(([wire,id])=>[wire,ownerWords.get(id)]))},keywords,codes});register(id,instance);entries.set(row.name,{fn:instance.exports.entry,self:functions.get(row.name)});}
 let invocations=0;
 return {keywords,ownerWords,wordOwners,extraRoots,
  reset(mat){
   new Uint8Array(memory.buffer,get(tcr+56),mat.image.length/2).set(Buffer.from(mat.image,'hex'));
   put(tcr+48,get(tcr+56)+mat.image.length/2);
   mods.forEach((row,i)=>put(functions.get(row.name)+18,mat.roots[i]));
   put(tcr+104,610000);put(tcr+108,256);
   for(let i=0;i<256;i++)put(610000+4*i,243);
   owners.forEach((row,i)=>{let value=NIL;
    if(row.package==='COMMON-LISP'&&row.name==='*READ-BASE*')value=40;
    if(row.package==='COMMON-LISP'&&row.name==='*PRINT-LEVEL*')value=28;
    if(row.package==='COMMON-LISP'&&row.name==='*PRINT-LENGTH*')value=36;
    if(row.package==='KEYWORD')value=ownerWords.get(row.id);
    put(600000+32*i+8,value);
   });
  },
  invoke(name,args){const entry=entries.get(name),incoming=132096,output=132352,owner=132512;
   put(tcr+64,incoming);put(tcr+116,0);put(tcr+120,output);put(tcr+124,owner);args.forEach((v,i)=>put(incoming+4*i,v));
   const bindings=Array.from({length:256},(_,i)=>get(610000+4*i));
   const before=Array.from({length:64},(_,i)=>get(tcr+4*i));let pair;
   try{pair=entry.fn(entry.self,args.length);}catch(e){throw Error(name+': '+(e.is?.(call_error)?'checked '+e.getArg(call_error,0):e));}
   for(let i=0;i<64;i++)if(![48,52,56,116].includes(i*4))assert.equal(get(tcr+4*i),before[i],name+' restored TCR '+i*4);
   assert.deepEqual(Array.from({length:256},(_,i)=>get(610000+4*i)),bindings,name+' restored bindings');
   assert.equal(pair[1]>>>0,get(tcr+116),name+' result count');assert.equal(pair[0]>>>0,pair[1]?get(output):NIL,name+' primary');invocations++;
   const values=Array.from({length:pair[1]>>>0},(_,i)=>get(output+i*4));put(tcr+116,0);return values;
  },summary(){return {invocations,modules:mods.length,delivery:[]};}
 };
}
