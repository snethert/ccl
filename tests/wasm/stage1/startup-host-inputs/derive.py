import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def replace(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def check(source,order):
 s=source.replace("import {inspect} from './binary.mjs';", "import {inspect} from './binary.mjs';\nimport {startupInputs,materializeInputs,inputBytes} from './inputs.mjs';\nimport {ownerChecks} from './owner-check.mjs';")
 s=replace(s,' const cases=read'," const admission=ownerChecks(read(dir,'composition-witness.json'));\n const cases=read")
 s=replace(s,'return {base,rows,refusals,invocations,foreignChecks};','return {base,rows,refusals,invocations,foreignChecks,admission};')
 s=replace(s,'assert.equal(all.length,20)','assert.equal(all.length,23)')
 s=replace(s,"const sequence=['preflight',...resets.map(r=>r.module),...names.slice(1)];",'const sequence='+json.dumps(order)+';')
 s=replace(s,"const symbol=i=>base+1024+32*i+6,encode=x=>", "const symbol=i=>base+1024+32*i+6,encode=x=>x&&typeof x==='object'?x.pointer:")
 old="const decode=x=>x===symbol(7)?'CCL::*SPIN-LOCK-TIMEOUTS*':x===NIL?'nil':x===T?'t':((assert.equal(x&3,0),x|0)/4);"
 new="""const decode=x=>{
  if(x===symbol(7))return 'CCL::*SPIN-LOCK-TIMEOUTS*';if(x===NIL)return 'nil';if(x===T)return 't';
  if((x&7)===6){assert.equal(get(x-6)&255,191,'input string');return Array.from({length:get(x-6)>>>8},(_,i)=>get(x-2+4*i));}
  if((x&7)===1){const out=[];for(let p=x;p!==NIL;p=get(p-1)){assert.equal(p&7,1,'input list');assert(out.length<256,'input list length');out.push(decode(get(p+3)));}return out;}
  assert.equal(x&3,0,'input value tag');return (x|0)/4;
 };
 const hostCases=read(dir,'host-cases.json'),hostNative=read(dir,'host-native.json');let hostIndex=0,hostInput,hostReader,hostAnswer;
 const collector=new WebAssembly.Instance(new WebAssembly.Module(fs.readFileSync(dir+'/collector.wasm')),{env:{memory}}).exports;
 const hostNames=['host_image','host_arguments','host_readback'];
 const expectedHost=()=>[hostNative[hostIndex].image,hostNative[hostIndex].arguments.length?hostNative[hostIndex].arguments:'nil'];"""
 s=replace(s,old,new)
 s=replace(s,'Array.from({length:21},(_,j)=>decode', 'Array.from({length:23},(_,j)=>decode')
 s=replace(s,'...Array(12).fill(sentinel)];','...Array(14).fill(sentinel)];')
 s=replace(s,'  answers=[];resetAnswers=[];workload=null;preflight=null;return initial;',"""  hostInput=materializeInputs({memory,base:base+16384,end:base+16384+inputBytes(hostCases[hostIndex].input),input:hostCases[hostIndex].input});
  assert(hostInput.end<=base+32768,'input region capacity');hostAnswer=null;hostReader=null;
  answers=[];resetAnswers=[];workload=null;preflight=null;return initial;""")
 s=replace(s,'i<20;i++','i<23;i++')
 s=replace(s,'const i=names.indexOf(name),j=resets.findIndex(r=>r.module===name);','const i=names.indexOf(name),j=resets.findIndex(r=>r.module===name),h=hostNames.indexOf(name);')
 s=replace(s,'   if(j>=0)state[resetIndex(j)]=resets[j].value;','   if(h===0||h===1)state[21+h]={pointer:h===0?hostInput.image:hostInput.arguments};\n   else if(j>=0)state[resetIndex(j)]=resets[j].value;')
 s=replace(s,"phase:name==='preflight'?0:name==='workload'?2:1,","phase:name==='preflight'?0:(name==='workload'||name==='host_readback')?2:1,")
 s=replace(s,'else for(const [k,value]of updates[i])','else for(const [k,value]of (i<0?[]:updates[i]))')
 s=replace(s,'value:4*(j>=0?201+j:100+i)','value:4*(h>=0?301+h:j>=0?201+j:100+i)')
 s=replace(s,'size:S+160-', 'size:S+184-')
 s=replace(s,'const args=j>=0?',"const h=hostNames.indexOf(row.id);\n  const args=h===2?[symbol(21),symbol(22),done]:h>=0?[symbol(21+h),h===0?hostInput.image:hostInput.arguments,done]:j>=0?")
 s=replace(s,'invocations++;let pair;',"const inputBefore=Uint8Array.from(new Uint8Array(memory.buffer,base+16384,hostInput.end-base-16384));\n  invocations++;let pair;")
 s=replace(s,'assert.equal(pair[1],i===0||i===6?9:1);','assert.equal(pair[1],h===2?2:i===0||i===6?9:1);\n  assert.deepEqual(new Uint8Array(memory.buffer,base+16384,inputBefore.length),inputBefore,\'inputs unchanged\');')
 s=replace(s,'for(const j of (i<0?', 'for(const j of (h>=0?(h===2?[]:[21+h]):i<0?')
 s=replace(s,'if(j>=0)resetAnswers.push',"if(h>=0){if(h===2){hostAnswer=values;hostReader=()=>invoke(entry,row);}else assert.deepEqual(values,[expectedHost()[h]],'native host callback');}\n  else if(j>=0)resetAnswers.push")
 s=replace(s,'i<21;i++','i<23;i++')
 s=replace(s,'  const initial=reset(c.input,sentinel)', '  hostIndex=ci%hostCases.length;\n  const initial=reset(c.input,sentinel)')
 s=replace(s,'stateAll().slice(9)', 'stateAll().slice(9,21)')
 s=replace(s,'get(READY+4),20','get(READY+4),23')
 s=replace(s,"  rows.push({name:c.name,sentinel,", """  assert.deepEqual(hostAnswer,expectedHost(),'native host readback');
  // Both published globals are real collector roots. No builder references are
  // supplied, and old input bytes are poisoned before generated readback.
  const gc=1200000,extra=1180000,to=base+49152;
  new Uint8Array(memory.buffer,gc,96).fill(0);
  set('alloc_base',base+16384);set('alloc_pointer',hostInput.end);set('alloc_limit',base+32768);set('mv_count',0);
  put(gc,TCR);put(gc+16,to);put(gc+20,base+65536);put(gc+68,32768);put(gc+72,extra);put(gc+76,2);put(gc+80,1800000);
  put(extra,symbol(21)+2);put(extra+4,symbol(22)+2);
  assert.equal(collector.collect(gc),0,'host input collection');
  assert(get(symbol(21)+2)!==hostInput.image,'image moves');
  new Uint8Array(memory.buffer,base+16384,hostInput.end-base-16384).fill(0xda);
  hostReader();assert.deepEqual(hostAnswer,expectedHost(),'generated moved input readback');
  rows.push({hostCase:hostCases[hostIndex].name,hostAnswer,hostCollection:true,name:c.name,sentinel,""")
 # Refusal tests have no extra execution and operate on a fresh input graph.
 s=replace(s,'const fresh=()=>{const initial=', 'const fresh=()=>{hostIndex=0;const initial=')
 return s
