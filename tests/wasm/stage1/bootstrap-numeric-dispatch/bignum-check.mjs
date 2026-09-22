import assert from 'node:assert/strict';
export function checkBignums({gen,memory,tcr,root,collect,encode,get,put}) {
 const NIL=77825, records=[], at=i=>root+8+4*i, read=i=>get(at(i)), save=(i,v)=>put(at(i),v), call=(name,args)=>gen.invoke('core_bignum_'+name,args);
 put(root,0);put(root+4,4);for(let i=0;i<4;i++)save(i,NIL);
 save(0,call('new',[12])[0]);save(1,call('new',[12])[0]);
 for(let i=0;i<3;i++) {
  call('store',[read(0),i*4,((0x1234+i)*4),((0xabcd+i)*4)]);
  assert.deepEqual(call('read',[read(0),i*4]),[(0x1234+i)*4,(0xabcd+i)*4]);
 }
 call('store',[read(1),0,0xfffffffc,0xfffffff8]);
 assert.deepEqual(call('read',[read(1),0]),[65535*4,65534*4]);
 records.push('native compose-digit truncates signed half words');
 call('copy',[read(0),0,read(1),0,48]);
 for(let i=0;i<3;i++)assert.deepEqual(call('read',[read(0),i*4]),call('read',[read(1),i*4]));
 call('copy',[read(1),0,read(1),16,32]);
 assert.deepEqual(call('read',[read(1),8]),call('read',[read(0),4]));
 records.push('digit and overlapping byte copies');
 const refuse=(label,name,args,code=4)=>{
  const used=get(tcr+48), before=new Uint8Array(memory.buffer,read(0)-6,16).slice();
  assert.throws(()=>call(name,args),new RegExp('checked '+code+'$'),label);
  assert.equal(get(tcr+48),used,label);
  assert.deepEqual(new Uint8Array(memory.buffer,read(0)-6,16),before,label);
  records.push(label);
 };
 for(const bad of [NIL,0,75])refuse('object tag '+bad,'read',[bad,0]);
 for(const bad of [75,0xfffffffc,12])refuse('digit index '+bad,'store',[read(0),bad,0,0]);
 refuse('high half type','store',[read(0),0,75,0],5);
 refuse('low half type','store',[read(0),0,0,75],5);
 for(const bad of [0,16,75,0xfffffffc])refuse('resize count '+bad,'resize',[read(0),bad]);
 for(const bad of [0,75,0xfffffffc,67108864])refuse('allocation count '+bad,'new',[bad],6);
 refuse('source byte extent','copy',[read(0),4,read(1),0,48]);
 refuse('destination byte extent','copy',[read(1),0,read(0),4,48]);
 refuse('negative byte offset','copy',[read(0),0xfffffffc,read(1),0,4]);
 refuse('byte count type','copy',[read(0),0,read(1),0,75]);
 refuse('destination object','copy',[read(0),0,NIL,0,4]);
 const raw=read(0)-6, header=get(raw);
 for(const bad of [250,7]){put(raw,bad);refuse('header '+bad,'read',[read(0),0]);put(raw,header);}
 const end=memory.buffer.byteLength;
 refuse('unbacked header','read',[(end+6)>>>0,0]);
 const old=get(end-8);put(end-8,3*256+7);refuse('unbacked digits','read',[end-2,0]);put(end-8,old);
 call('resize',[read(0),4]);assert.equal(get(raw),263);assert.equal(get(raw+8),250);assert.equal(get(raw+12),0);
 collect();assert.deepEqual(call('read',[read(0),0]),[0x1234*4,0xabcd*4]);
 records.push('shrunk allocation remains walkable under collection');
 save(2,call('new',[16])[0]);call('resize',[read(2),8]);assert.equal(get(read(2)+6),0);
 collect();assert.deepEqual(call('read',[read(2),4]),[0,0]);
 records.push('even digit count has zero padding');
 return records;
}
