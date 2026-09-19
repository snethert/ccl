import fs from 'node:fs';
import assert from 'node:assert/strict';
const memory=new WebAssembly.Memory({initial:17,maximum:32769,shared:true}),d=new DataView(memory.buffer),TCR=256;
const get=p=>d.getUint32(p,true),put=(p,v)=>d.setUint32(p,v,true),tag=new WebAssembly.Tag({parameters:['i32']});
const instance=await WebAssembly.instantiate(await WebAssembly.compile(fs.readFileSync(process.argv[2])),{env:{memory,tcr:TCR,call_error:tag}});
const rows=[];
for(const [name,base,cap] of [['existing',610000,32],['relocated',630000,32],['missing',610000,1]]){
 new Uint8Array(memory.buffer).fill(0);put(TCR+68,65536);put(TCR+72,98304);put(TCR+56,262144);put(TCR+48,262144);put(TCR+52,294912);put(TCR+104,base);put(TCR+108,cap);put(TCR+112,66000);
 put(600000,1850);put(600028,31*4);put(66000,0);put(66004,31*4);put(66016,600006);put(66020,28);put(66024,1112425521);put(base+31*4,44);
 const saved=new Uint8Array(memory.buffer,262144,32768).slice();let status=0;
 try{instance.exports.unbind(0);}catch(e){assert(e.is(tag));status=e.getArg(tag,0);}
 assert.equal(status,cap===1?11:0,name+': non-growing unbind status');
 assert.equal(get(TCR+48),262144,name+': no allocation');assert.equal(get(TCR+104),base);assert.equal(get(TCR+108),cap);
 assert.deepEqual(new Uint8Array(memory.buffer,262144,32768),saved,'heap unchanged');
 assert.equal(get(TCR+112),cap===1?66000:0);assert.equal(get(base+31*4),cap===1?44:28);rows.push({name,status});
}
fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',rows},null,2)+'\n');
