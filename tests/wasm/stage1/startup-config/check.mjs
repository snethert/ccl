import assert from './assert.mjs';
import {BootstrapSchedule} from './bootstrap-schedule.mjs';
import {scheduleInstaller} from './bootstrap-install.mjs';
import {processConfiguration} from './config.mjs';
import {PROFILE,sha} from './loader.mjs';
import {inspect} from './binary.mjs';
const NIL=77825,T=77838,TCR=16384,REG=4096,STACK=32768;
const names=['preflight','config_5564','config_6151','config_6150','config_6127','config_5566','workload'];
export function execute(assets,base){
 const dir='';const fs={readFileSync:n=>assets[n.replace(/^\//,'')]};const read=(d,n)=>JSON.parse(new TextDecoder().decode(fs.readFileSync(d+'/'+n)));
 const cases=read(dir,'cases.json'),expected=read(dir,'expected.json'),native=read(dir,'compiled/native.json');
 const all=read(dir,'compiled/modules.json').map((m,i)=>{
  const bytes=fs.readFileSync(dir+'/compiled/'+m.name+'.wasm'),x=inspect(bytes);
  return {name:m.name,bytes,record:{name:m.name,slot:i+1,code:i+1,version:4,signature:17,role:23,profile:PROFILE,sha256:sha(bytes),imports:x.imports,entries:Object.fromEntries(x.exports.map(e=>[e.name,{role:e.name,index:e.index}]))}};
 });
 assert.equal(all.length,7);const mat=read(dir,'compiled/materialized.json');assert.equal(mat.image,'');
 const memory=new WebAssembly.Memory({initial:32769,maximum:32769,shared:true}),v=new DataView(memory.buffer);
 const get=p=>v.getUint32(p,true),put=(p,x)=>v.setUint32(p,x,true),S=base+8192,READY=S+256;
 const table=new WebAssembly.Table({element:'anyfunc',initial:32}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:32});
 const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const imports={env:{memory,tcr:TCR,table,tail_table,code_registry:REG,call_error,type_error,nonlocal_exit},symbols:{}};
 const fields=Object.fromEntries(read(dir,'tcr.json').fields.map(r=>[r.name,r.offset]));
 const set=(n,x)=>{assert(n in fields);put(TCR+fields[n],x);};
 const keys=[...new Set(all.flatMap(m=>m.record.imports.filter(x=>x.module==='symbols').map(x=>x.name)))];
 keys.forEach((k,i)=>imports.symbols[k]=base+4096+32*i+6);
 const symbol=i=>base+1024+32*i+6,encode=x=>x==='nil'?NIL:x==='t'?T:x*4;
 const decode=x=>x===symbol(7)?'CCL::*SPIN-LOCK-TIMEOUTS*':x===NIL?'nil':x===T?'t':((assert.equal(x&3,0),x|0)/4);
 const globals=()=>Array.from({length:8},(_,i)=>decode(get(symbol(i)+2)));
 const destinations=[[],[0],[1],[2],[3,4,5],[6,7],[]];
 let cfg,answers,preflight,workload,invocations=0,foreignChecks=0;
 function reset(raw,sentinel){
  cfg=processConfiguration(raw);
  new Uint8Array(memory.buffer,TCR,256).fill(0);new Uint8Array(memory.buffer,STACK,32768).fill(0);
  new Uint8Array(memory.buffer,base,8600).fill(0);
  for(let i=0;i<32;i++){table.set(i,null);tail_table.set(i,null);}
  put(77824,NIL);put(77828,NIL);put(77832,1850);for(let i=3;i<16;i++)put(77824+4*i,NIL);
  put(REG,32);put(REG+4,1);
  all.forEach((m,i)=>{
   [i+1,4,17,23].forEach((x,j)=>put(REG+8+16*(i+1)+4*j,x));
   [1578,4*(i+1),NIL,4,NIL,NIL,mat.roots[i],0].forEach((x,j)=>put(base+32*i+4*j,x));
  });
  keys.forEach((k,i)=>[1850,NIL,NIL,NIL,NIL,0,NIL,0].forEach((x,j)=>put(base+4096+32*i+4*j,x)));
  const initial=[sentinel,sentinel,sentinel,...cfg.defaults,sentinel,sentinel];
  initial.forEach((value,i)=>[1850,NIL,encode(value),NIL,NIL,0,NIL,0].forEach((x,j)=>put(symbol(i)-6+4*j,x)));
  for(const [n,x]of Object.entries({tcr_address:TCR,alloc_base:131072,alloc_pointer:131072,alloc_limit:135168,vsp_base:STACK+16,vsp:STACK+512,vsp_limit:STACK+32768,tsp_base:8192,tsp:8192,tsp_limit:12288,csp_base:12288,csp:12288,csp_limit:16384,tlb_pointer:139264,tlb_limit:64,mv_base:STACK+1024,mv_owner_top:STACK+1088,root_head:STACK+8,next_method_context:NIL,fp_control:7}))set(n,x);
  new Uint8Array(memory.buffer,8192,8192).fill(0x96);new Uint8Array(memory.buffer,131072,4096).fill(0xa5);
  for(let i=0;i<64;i++)put(139264+4*i,243);
  for(let i=0;i<7;i++){put(S+8*i,NIL);put(S+8*i+4,0);}
  answers=[];workload=null;preflight=null;return initial;
 }
 function plan(initial){
  const state=initial.slice(),steps=[];
  const updates=[[],[[0,cfg.pageSize]],[[1,cfg.ticks]],[[2,cfg.period]],cfg.active?[[3,cfg.stackSize],[4,cfg.stackSize],[5,cfg.half]]:[],[[6,cfg.cpuCount===1?1:1024],[7,0]],[]];
  names.forEach((name,i)=>{
   const before=state.map((value,j)=>({address:symbol(j)+2,value:encode(value)}));
   for(const [j,value]of updates[i])state[j]=value;
   steps.push({id:name,module:name,sha256:all.find(m=>m.name===name).record.sha256,phase:i===0?0:i===6?2:1,
    prerequisites:i?[names[i-1]]:[],completion:{address:S+8*i+4,value:4*(100+i)},before,
    after:state.map((value,j)=>({address:symbol(j)+2,value:encode(value)}))});
  });
  return {version:1,state:{start:base+1024,size:S+64-(base+1024)},ready:READY,initializers:steps};
 }
 function invoke(entry,row){
  const i=names.indexOf(row.id),index=all.findIndex(m=>m.name===row.module),done=S+8*i+1;
  const args=i===0||i===6?[...Array.from({length:8},(_,j)=>symbol(j)),done]:
   i===4?[symbol(3),symbol(4),symbol(5),cfg.active?T:NIL,encode(cfg.stackSize),encode(cfg.half),done]:
   i===5?[symbol(6),symbol(7),encode(cfg.cpuCount),done]:[symbol(i-1),encode([cfg.pageSize,cfg.ticks,cfg.period][i-1]),done];
  set('vsp',STACK+512);set('mv_base',STACK+1024);set('mv_owner_top',STACK+1088);set('mv_count',0);
  args.forEach((x,j)=>put(STACK+512+4*j,x));const saved=[64,128,140,92,112,48].map(o=>get(TCR+o));
  const image=Uint8Array.from(new Uint8Array(memory.buffer,base,8600));
  const foreign=[[8192,8192],[131072,4096],[139264,256]].map(([p,n])=>Uint8Array.from(new Uint8Array(memory.buffer,p,n)));
  invocations++;let pair;
  try{pair=entry(base+32*index+6,args.length);}catch(e){if(e.is?.(call_error))throw Error('CHECKED_'+e.getArg(call_error,0));throw e;}
  finally{assert.deepEqual([64,128,140,92,112,48].map(o=>get(TCR+o)),saved,'caller and allocation restored');}
  [[8192,8192],[131072,4096],[139264,256]].forEach(([p,n],j)=>assert.deepEqual(new Uint8Array(memory.buffer,p,n),foreign[j],'foreign owner region'));foreignChecks+=3;
  assert.equal(pair[1],i===0||i===6?8:1);
  const values=Array.from({length:pair[1]},(_,j)=>decode(get(STACK+1024+4*j)));
  const old=new DataView(image.buffer);old.setUint32(row.completion.address-base,get(row.completion.address),true);
  for(const j of destinations[i])old.setUint32(symbol(j)+2-base,get(symbol(j)+2),true);
  assert.deepEqual(new Uint8Array(memory.buffer,base,8600),image,'no foreign image writes');
  if(i===0)preflight=values;else if(i===6)workload=values;else answers.push({values,globals:globals()});
 }
 function adapter(){
  for(let i=0;i<8;i++){const p=symbol(i);assert.equal(get(p-6),1850,'CONFIG_SYMBOL_HEADER');assert.equal(get(p+22),0,'CONFIG_GLOBAL_INDEX');assert.equal(get(p+14)&8,0,'CONFIG_WRITABLE');}
  return scheduleInstaller({modules:all,imports,invoke,loaderOptions:{memory,table,tail_table,call_error,nonlocal_exit,stub:new WebAssembly.Module(fs.readFileSync(dir+'/stub.wasm'))}});
 }
 const rows=[];
 for(const [ci,c]of cases.entries())for(const [ri,sentinel]of [37,91].entries()){
  const raw=structuredClone(c.input),initial=reset(raw,sentinel),p=plan(initial),a=adapter();
  raw.defaults.fill(1);raw.cpuCount=99; // admitted configuration is a private snapshot
  assert(Object.isFrozen(cfg)&&Object.isFrozen(cfg.defaults));
  const owner=new BootstrapSchedule({memory,plan:p,digest:sha(JSON.stringify(p)),modules:all});
  const events=owner.run(a.install);
  assert.deepEqual(answers,native[ci][ri],'native source effects');assert.deepEqual(answers,expected[ci][ri]);
  assert.deepEqual(preflight,initial);assert.deepEqual(workload,native[ci][ri][4].globals,'readback');
  assert.equal(get(READY),1);assert.equal(get(READY+4),7);assert.equal(owner.state,'READY');
  rows.push({name:c.name,sentinel,answers:structuredClone(answers),preflight,workload,events,installed:a.installed()});
 }
 const refusals=[];
 function refuse(name,edit,why){
  const initial=reset(cases[0].input,37),p=plan(initial),before=sha(new Uint8Array(memory.buffer,base,8600));
  assert.throws(()=>edit(p),new RegExp(why),name);assert.equal(get(READY),0);refusals.push({name,reason:why});return before;
 }
 for(const name of names)refuse('missing '+name,p=>new BootstrapSchedule({memory,plan:p,digest:sha(JSON.stringify(p)),modules:all.filter(m=>m.name!==name)}),'MODULE_SET');
 for(const [field,value,why]of [['pageSize',0,'PAGE_SIZE'],['pageSize',3,'PAGE_SIZE'],['pageSize',536870912,'PAGE_SIZE'],['pageSize',1.5,'PAGE_SIZE'],['clockTicks',-2,'CLOCK_TICKS'],['clockTicks',536870912,'CLOCK_TICKS'],['clockTicks',NaN,'CLOCK_TICKS'],['cpuCount',0,'CPU_COUNT'],['cpuCount',536870912,'CPU_COUNT'],['stackSize',-536870913,'STACK_SIZE'],['stackSize',536870912,'STACK_SIZE'],['defaults',[0,1,1],'STACK_DEFAULTS'],['defaults',[1,1],'STACK_DEFAULTS'],['defaults',[1,1,1,1],'STACK_DEFAULTS'],['defaults',[1,1,1.5],'STACK_DEFAULTS']]){
  const raw=structuredClone(cases[0].input);raw[field]=value;
  refuse('invalid '+field+' '+String(value),()=>processConfiguration(raw),why);
 }
 refuse('extra configuration field',()=>processConfiguration({...cases[0].input,fdSetSize:128}),'CONFIG_FIELDS');
 refuse('missing capability',()=>processConfiguration(null),'CONFIG_OBJECT');
 for(const [offset,value,why]of [[22,4,'CONFIG_GLOBAL_INDEX'],[14,8,'CONFIG_WRITABLE'],[-6,0,'CONFIG_SYMBOL_HEADER']])refuse(why,()=>{put(symbol(0)+offset,value);adapter();},why);
 for(const [name,hook,why]of [
  ['no load',()=>()=>{},'COMPLETION_MISSING'],
  ['wrong tick dependency',(a,m,r)=>{const f=a.install(m,r);return()=>{f();if(r.id==='config_6151')put(symbol(1)+2,4);};},'POSTCONDITION'],
  ['missing completion',(a,m,r)=>{const f=a.install(m,r);return()=>{f();put(r.completion.address,0);};},'COMPLETION_MISSING']]){
  refuse(name,p=>{const a=adapter(),o=new BootstrapSchedule({memory,plan:p,digest:sha(JSON.stringify(p)),modules:all});assert.throws(()=>o.run((m,r)=>hook(a,m,r)),new RegExp(why));assert.equal(o.state,'FAILED');assert(!o.events.some(e=>e.id==='workload'&&e.event==='completed'));throw Error(why);},why);
 }
 return {base,rows,refusals,invocations,foreignChecks};
}
