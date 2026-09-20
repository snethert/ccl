setup(false,32768);
const sample={name:'service-loop',op:'add',a:{kind:'64',bits:'3ff8000000000000'},b:{kind:'64',bits:'4000000000000000'},mask:7,safe:1};
const loop=new WebAssembly.Instance(new WebAssembly.Module(fs.readFileSync(dir+'/service-loop.wasm')),{env:{memory},floating:{calculate}}).exports.run;
owner.ensure=()=>{throw Error('SERVICE_LOOP_MUST_NOT_ASSURE');};
// Match the generated timing harness's per-batch TCR/operand reset. The raw
// correctness reset clones owner.spaces and clears a 16 KiB image; neither is
// part of the service under measurement.
const heapBase=t(56);
function resetBatch(){
 for(const [o,v] of [[48,heapBase],[64,ROOT+24],[128,ROOT],[120,BASE+8200],[124,BASE+8264],[140,0],[148,0],[192,0],[76,196608]])set(o,v);
 put(ROOT,BASE);put(ROOT+4,4);put(ROOT+16,N);put(ROOT+20,N);set(200,sample.mask);
 let cursor=heapBase;
 for(const [slot,x] of [[ROOT+8,sample.a],[ROOT+12,sample.b]]){const value=store(x,cursor);cursor+=value.size;put(slot,value.v);}
 set(48,cursor);
}
function measure(ms){
 let count=0,now=performance.now(),start=now;
 do{for(let j=0;j<128;j++){resetBatch();loop(ROOT,0,1,64);count++;}now=performance.now();}while(now-start<ms);
 assert.equal(decode(get(ROOT+16)),'400c000000000000');
 return {milliseconds:now-start,calls:count,operations:count*64,nsPerOperation:(now-start)*1e6/(count*64)};
}
measure(500);const trials=Array.from({length:20},()=>measure(125));
fs.writeFileSync(outputFile,JSON.stringify({status:'MEASURED',trials,scope:'One persistent four-slot root frame per batch; direct Wasm loop, same scalar capability and boxed results. Difference from generated-loop timing includes language loop, frame setup/retirement and result delivery; not an isolated stack-cost measurement.'},null,2)+'\n');
