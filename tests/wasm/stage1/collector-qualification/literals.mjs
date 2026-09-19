import fs from 'node:fs';import assert from 'node:assert/strict';
import {CollectorOwner} from './collector-owner.mjs';import {LazyLoader,PROFILE,sha} from './loader.mjs';import {inspect} from './binary.mjs';
const [dir,collectorPath,output]=process.argv.slice(2),read=n=>JSON.parse(fs.readFileSync(dir+'/'+n));
const bytes=fs.readFileSync(collectorPath),mods=read('modules.json'),expected=read('expected.json'),rows=[];
const NIL=77825,T=77838,tcr=1024,ROOT=131064,OUT=139264;
for(const label of ['low','high','pinned'].filter(x=>!process.env.LITERAL_LAYOUT||x===process.env.LITERAL_LAYOUT)){
 const pool=read('materialized-'+label+'.json'),A=label==='pinned'?2097152:pool.base,B=A+32768;
 const memory=new WebAssembly.Memory({initial:label==='high'?32769:48,maximum:32769,shared:true});let dv=new DataView(memory.buffer);
 const load=p=>{dv=new DataView(memory.buffer);return dv.getUint32(p,true);},store=(p,v)=>{dv=new DataView(memory.buffer);dv.setUint32(p,v,true);},set=(o,v)=>store(tcr+o,v),get=o=>load(tcr+o);
 const images=[];const image=(start,bytes)=>images.push({name:'image'+start,role:'image',start,end:start+bytes});
 image(77824,40);store(NIL-1,NIL);store(NIL+3,NIL);store(T-6,1850);for(let i=1;i<8;i++)store(T-6+4*i,NIL);
 const symbols={condition_handlers:600006};for(const x of [600006,...Object.values(pool.symbols)]){image(x-6,32);store(x-6,1850);for(let i=1;i<8;i++)store(x-6+4*i,NIL);store(x+22,0);}
 const table=new WebAssembly.Table({element:'anyfunc',initial:mods.length+1}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:mods.length+1}),call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const codes=Object.fromEntries(mods.map((m,i)=>[m.name,4*(i+1)])),handles={},binaries=new Map(mods.map(m=>[m.name,fs.readFileSync(dir+'/'+m.name+'.wasm')]));
 let symbolTop=600032;
 for(const b of binaries.values())for(const i of inspect(b).imports)if(i.module==='symbols'&&symbols[i.name]===undefined){const p=symbolTop;symbolTop+=32;assert(symbolTop<620000);image(p,32);store(p,1850);for(let j=1;j<8;j++)store(p+4*j,NIL);store(p+28,0);symbols[i.name]=p+6;}
 store(4096,mods.length+1);store(4100,1);
 for(const [i,m] of mods.entries()){
  [i+1,4,17,23].forEach((v,j)=>store(4104+16*(i+1)+4*j,v));
  if(m.top){const p=786432+32*i;image(p,32);store(p,1578);[codes[m.name],NIL,4,NIL,NIL,pool.roots[i],0].forEach((v,j)=>store(p+4+4*j,v));handles[m.name]=p+6;}
 }
 new Uint8Array(memory.buffer,pool.base,pool.image.length/2).set(Buffer.from(pool.image,'hex'));if(label==='pinned')image(pool.base,pool.image.length/2);set(48,label==='pinned'?A:A+pool.image.length/2);set(52,A+32768);set(56,A);
 set(68,ROOT+8);set(72,163840);set(64,ROOT+8);set(128,ROOT);store(ROOT,0);store(ROOT+4,0);set(120,OUT);set(124,OUT+64);
 set(80,196608);set(76,196608);set(84,229376);set(92,229376);set(88,229376);set(96,245760);set(104,266240);set(108,0);set(188,NIL);
 const external=262144;store(external,NIL);
 const regions=[['tcr',1024,1280],['external',external,external+4096],['vstack',ROOT,163840],['temp',196608,229376],['control',229376,245760],['bindings',266240,270336],['c-stack',1048576,1114112],['root-list',1180000,1200000],['scratch',1200000,1800000]].map(([role,start,end],i)=>({name:role+i,role,start,end}));
 const owner=CollectorOwner.create(memory,bytes,sha(bytes),{version:1,collector:'copying',workers:1,egc:false,tcr,maximumPages:32769,logCapacity:32768,regions:[...regions,...images],spaces:[{name:'a',start:A,end:A+32768},{name:'b',start:B,end:B+32768}],groups:['module-constants','callbacks','registry','host'].map(kind=>({kind,slots:kind==='host'?[external]:[]}))});
 const catalog=mods.map((m,i)=>{const b=binaries.get(m.name),info=inspect(b);return {name:m.name,slot:i+1,code:i+1,version:4,signature:17,role:23,sha256:sha(b),profile:PROFILE,imports:info.imports,entries:Object.fromEntries(info.exports.map(e=>[e.name,{index:e.index,role:e.name}]))};});
 const loader=new LazyLoader({memory,table,tail_table,call_error,nonlocal_exit,catalog,readBytes:n=>binaries.get(n),stub:new WebAssembly.Module(fs.readFileSync(new URL('./stub.wasm',import.meta.url)))}),entries={};
 for(const m of mods)entries[m.name]=loader.defer(m.name,{env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},codes,symbols,keywords:{}}).host_entry;
 const collect=()=>{const from=get(56),end=get(52);const r=owner.atSafepoint(o=>o.collect());new Uint8Array(memory.buffer,from,end-from).fill(0xdd);return r;};
 const cold=mods.findIndex(m=>m.name==='cold');assert.equal(loader.snapshot()[cold].state,'COLD');const before=load(handles.cold+18);const first=collect();if(label==='pinned')assert.equal(load(handles.cold+18),before);else assert.notEqual(load(handles.cold+18),before,'cold pool moves before installation');assert.equal(loader.snapshot()[cold].state,'COLD');
 function invoke(name,args=[],self=handles[name]){store(ROOT+4,args.length);args.forEach((v,i)=>store(ROOT+8+4*i,v));set(116,0);set(120,OUT);set(124,OUT+64);set(128,ROOT);set(64,ROOT+8);
  let r;try{r=entries[name](self,args.length);}catch(e){if(e.is?.(call_error))throw Error(name+': checked '+e.getArg(call_error,0)+' '+JSON.stringify(loader.events.at(-1)));throw e;}
  assert.equal(get(128),ROOT);assert.equal(get(112),0);assert.equal(get(140),0);return Array.from({length:r[1]},(_,i)=>load(OUT+4*i));}
 function describe(values,name){const seen=new Map(),objects=[];
  function value(x){for(const [key,address] of Object.entries(pool.symbols))if(x===address)return {symbol:key};if(x===77825)return {kind:'singleton',value:'nil'};if(x===77838)return {kind:'singleton',value:'t'};if(x%4===0)return {kind:'integer',value:String((x|0)/4)};if(x%256===75)return {kind:'character',value:Math.floor(x/256)};if(!seen.has(x)){seen.set(x,objects.length);objects.push(x);}return {ref:seen.get(x)};}
  const roots=values.map(value),result=[];
  for(let i=0;i<objects.length;i++){let x=objects[i],p=x-x%8;
   if(x%8===1){result.push({kind:'cons',car:value(load(p+4)),cdr:value(load(p))});continue;}
   assert.equal(x%8,6,'value-tag '+name);const header=load(p),tag=header%256,n=Math.floor(header/256);
   if(tag===250)result.push({kind:'general-vector',elements:Array.from({length:n},(_,j)=>value(load(p+4+4*j)))});
   else if(tag===191)result.push({kind:'string',value:Array.from({length:n},(_,j)=>load(p+4+4*j))});
   else if(tag===7){let v=0n;for(let j=n-1;j>=0;j--)v=v*4294967296n+BigInt(load(p+4+4*j));if(load(p+4*n)>=0x80000000)v-=1n<<BigInt(n*32);result.push({kind:'integer',value:String(v)});}
   else if(tag===15)result.push({kind:'single-float',value:load(p+4).toString(16).padStart(8,'0')});
   else if(tag===23)result.push({kind:'double-float',value:dv.getBigUint64(p+8,true).toString(16).padStart(16,'0')});
   else {
    const ints={199:['u8',1,false],207:['s8',1,true],215:['u16',2,false],223:['s16',2,true],167:['u32',4,false],175:['s32',4,true],183:['fixnum',4,true]};
    if(tag in ints){const [type,width,signed]=ints[tag];result.push({kind:'vector',type,elements:Array.from({length:n},(_,j)=>String(dv['get'+(signed?'Int':'Uint')+(width*8)](p+4+width*j,true)))});}
    else if(tag===255)result.push({kind:'vector',type:'bit',elements:Array.from({length:n},(_,j)=>(dv.getUint8(p+4+Math.floor(j/8))>>>(j%8))&1)});
    else if([159,231,239,247].includes(tag)){
     const width=[231,247].includes(tag)?8:4,parts=[239,247].includes(tag)?2:1,offset=tag===159?4:8,type={159:'single-float',231:'double-float',239:'complex-single-float',247:'complex-double-float'}[tag];
     const bits=where=>(width===8?dv.getBigUint64(where,true):dv.getUint32(where,true)).toString(16).padStart(width*2,'0');
     result.push({kind:'vector',type,elements:Array.from({length:n},(_,j)=>parts===1?bits(p+offset+j*width):[bits(p+offset+j*width*2),bits(p+offset+j*width*2+width)])});
    }else throw new Error('oracle unsupported tag '+tag);
   }
  }return {roots,objects:result};
 }
 let comparisons=0,collections=1;
 for(const m of mods.filter(m=>m.top&&!['tail_pool','mutate_pool','closure','captured','grandchild','captured_apply','flet_constant'].includes(m.name))){
  const result=invoke(m.name);assert.deepEqual(describe(result,m.name),expected[m.name],m.name+': native literals');
  collect();collections++;const moved=Array.from({length:get(116)},(_,i)=>load(OUT+4*i));assert.deepEqual(describe(moved,m.name),expected[m.name],m.name+': moved active values');comparisons+=2;
 }
 for(const name of ['closure','captured','grandchild']){
  let result=invoke(name,name==='captured'?[68]:[]);let depth=name==='grandchild'?2:1;
  while(depth--){store(external,result[0]);store(ROOT+4,0);set(116,0);collect();collections++;const self=load(external),child=mods[load(self-2)/4-1].name;result=invoke(child,[],self);}
  assert.deepEqual(describe(result,name),expected[name],name+': moved closure pool');comparisons++;
 }
 // Put the pool's objects in a pinned image as well: the owner must admit all
 // pointer-free widths there, not only in the C copying scanner.
 rows.push({label,status:'PASS',comparisons,collections,coldBeforeInstall:true,literalObjects:pool.objects.length,first});
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',rows},null,2)+'\n');
