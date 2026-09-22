import assert from 'node:assert/strict';
// Target layout checks are separate from native getter comparisons.
export function checkFuncallables({gen,memory,tcr,root,config,collector,collect,encode,decode,get,put}){
 const NIL=77825,T=77838,records=[];
 const rootAt=i=>root+8+4*i,save=(i,x)=>put(rootAt(i),x),read=i=>get(rootAt(i));
 put(root,0);put(root+4,4);for(let i=0;i<4;i++)save(i,NIL);
 const template=gen.functions.get('core_gf_identity');
 const slots=Array.from({length:7},(_,i)=>[i+10,null]);
 save(0,encode({vector:slots}));
 // Constructor clones the vector: caller mutation must not alias its fields.
 const originalVector=read(0);put(tcr+52,get(tcr+48));
 save(1,gen.invoke('core_gf_make',[template,read(0)])[0]);assert.notEqual(read(0),originalVector,'constructor retried after collection');
 assert.equal(get(read(1)-6),1834);assert.notEqual(get(read(1)+22),read(0));
 put(read(0)-2,999*4);
 for(let i=0;i<7;i++)assert.deepEqual(decode(gen.invoke('core_gf_ref',[read(1),4*i])[0]),slots[i]);
 save(0,NIL);collect();
 for(let i=0;i<7;i++)assert.deepEqual(decode(gen.invoke('core_gf_ref',[read(1),4*i])[0]),slots[i]);
 records.push('all seven immediate fields survive with only the function rooted');
 assert.deepEqual(gen.invoke('core_gf_call',[read(1),124]),[124]);
 records.push('metadata checked callable dispatch after movement');
 save(2,encode([73,null]));
 const before=get(tcr+56);
 assert.deepEqual(decode(gen.invoke('core_gf_set_moving',[read(1),8,read(2)])[0]),[73,null]);
 assert.notEqual(get(tcr+56),before);
 assert.equal(gen.invoke('core_gf_ref',[read(1),8])[0],read(2));
 save(2,NIL);collect();assert.deepEqual(decode(gen.invoke('core_gf_ref',[read(1),8])[0]),[73,null]);
 records.push('setter reloads function and value after collection');
 save(2,gen.invoke('core_gf_closure',[encode([81,null])])[0]);
 save(0,encode({vector:[null,null,null,null,null,null,null]}));
 save(3,gen.invoke('core_gf_make',[read(2),read(0)])[0]);save(0,NIL);save(2,NIL);collect();
 assert.deepEqual(decode(gen.invoke('core_gf_call',[read(3),8])[0]),[[81,null],2]);
 records.push('captured closure prefix survives cloning and movement');
 const refused=(label,name,args)=>{const from=get(tcr+56),used=get(tcr+48),image=Buffer.from(new Uint8Array(memory.buffer,from,used-from));assert.throws(()=>gen.invoke(name,args),/checked 4$/);assert.equal(get(tcr+48),used);assert.deepEqual(Buffer.from(new Uint8Array(memory.buffer,from,used-from)),image);records.push(label);};
 for(const index of [28,0xfffffffc,75])refused('index '+index,'core_gf_ref',[read(1),index]);
 refused('ordinary function has no Lisp immediates','core_gf_ref',[template,0]);
 refused('non-function','core_gf_ref',[NIL,0]);
 refused('constructor requires function','core_gf_make',[NIL,encode({vector:[null,null,null,null,null,null,null]})]);
 refused('constructor exact vector width','core_gf_make',[template,encode({vector:[null]})]);
 const raw=read(1)-6,field=get(raw+28);
 for(const [label,value] of [['tag',NIL],['extent',memory.buffer.byteLength-2],['header',template]]){
  put(raw+28,value);refused('immediates '+label,'core_gf_ref',[raw+6,0]);refused('callable '+label,'core_gf_call',[raw+6,0]);put(raw+28,field);
 }
 const source=get(tcr+56),used=get(tcr+48),dest=source===262144||source===2147483648?3145728:(memory.buffer.byteLength>2147483648?2147483648:262144);
 for(const [label,p,value]of [['function width',raw,2090],['immediates tag',raw+28,NIL],['immediates interior',raw+28,field+8],['immediates header',field-6,1786]]){
  const old=get(p);put(p,value);const image=Buffer.from(new Uint8Array(memory.buffer,source,used-source)),roots=Buffer.from(new Uint8Array(memory.buffer,root,24));put(config+16,dest);put(config+20,dest+65536);
  assert.equal(collector.collect(config),2,label);assert.equal(get(tcr+48),used);assert.deepEqual(Buffer.from(new Uint8Array(memory.buffer,source,used-source)),image);assert.deepEqual(Buffer.from(new Uint8Array(memory.buffer,root,24)),roots);put(p,old);records.push('collector refuses '+label);
 }
 return records;
}
