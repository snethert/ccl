import fs from 'node:fs';
import assert from 'node:assert/strict';
const dir=process.argv[2],rows=[];
for(const base of [262144,2147483648]){
 const memory=new WebAssembly.Memory({initial:Math.max(80,Math.ceil((base+4096)/65536)),maximum:32769,shared:true});
 const view=new DataView(memory.buffer),put=(p,n)=>view.setUint32(p,n,true);
 const error=new WebAssembly.Tag({parameters:['i32']});
 const {instance}=await WebAssembly.instantiate(fs.readFileSync(dir+'/validator.wasm'),{env:{memory,error}});
 const frame=base+64,head=base+160,top=base+256;
 function reset(){
  new Uint8Array(memory.buffer,base,4096).fill(0);
  put(1024+68,base);put(1024+128,head);
  put(head,frame);put(head+4,2);put(head+8,77825);put(head+12,77825);
  put(frame,0);put(frame+4,4);put(frame+8,12);
  put(frame+12,12);put(frame+16,8);put(frame+20,4);
 }
 function run(name,setup,answer=null){
  reset();const pointer=setup?.()??frame+8;
  const before=Buffer.from(memory.buffer,base,4096).toString('hex');
  if(answer===null){
   let caught=false;
   try{instance.exports.validate(pointer,top);}
   catch(e){assert(e instanceof WebAssembly.Exception,`${name}: trap or host error`);assert(e.is(error));assert.equal(e.getArg(error,0),5);caught=true;}
   assert(caught,name+': not refused');
  }else assert.equal(instance.exports.validate(pointer,top),answer,name);
  assert.equal(Buffer.from(memory.buffer,base,4096).toString('hex'),before,name+': state changed');
  rows.push({base,name,result:answer===null?'checked refusal':answer});
 }
 run('three arguments',null,3);
 run('empty',()=>{put(frame+4,1);put(frame+8,0);},0);
 run('seven arguments',()=>{put(frame+4,8);put(frame+8,28);},7);
 run('unknown pointer',()=>frame+12);
 run('null chain',()=>{put(1024+128,0);});
 run('unaligned frame',()=>{put(1024+128,head+1);put(head+1,0);put(head+5,1);put(head+9,0);return head+9;});
 run('below stack',()=>{put(1024+68,head+4);});
 run('header beyond top',()=>{put(1024+128,top-8);});
 run('payload beyond next frame',()=>{put(frame+4,25);});
 run('cyclic chain',()=>{put(head,head);});
 run('negative count',()=>{put(frame+8,0xfffffffc);});
 run('nonfixnum count',()=>{put(frame+8,13);});
 run('count mismatch',()=>{put(frame+8,8);});
 run('max unsigned extent',()=>{put(frame+4,0xffffffff);});
 run('unbacked pointer',()=>0xfffffff8);
}
fs.writeFileSync(dir+'/checks.json',JSON.stringify({status:'PASS',rows},null,2)+'\n');
console.log('PASS:',rows.length,'lexpr frame checks');
