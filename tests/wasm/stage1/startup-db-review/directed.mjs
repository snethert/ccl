 // Consistent malformed lists isolate checks that broken links cannot test.
 const directed=[];
 for(const [name,wanted,edit]of [
  ['foreign-directory',3,a=>{
   const p=base+8192;new Uint8Array(memory.buffer,p,56).set(new Uint8Array(memory.buffer,node(0)-6,56));
   put(base+12,p+6);put(node(1)-6+8,p+6);
  }],
  ['omitted-directory',3,a=>{put(node(0)-6+12,head);put(base+8,node(0));}],
  ['shared-descriptor',2,a=>{a[3]=DT;put(base+4,DT);}],
 ]){
  setup(2);new Uint8Array(memory.buffer,base+8192-8,80).fill(0xa5);
  const a=[head,base+24,5,HT,DT,base,end,RESULT];edit(a);poison();
  const before=snapshot(),outside=Uint8Array.from(new Uint8Array(memory.buffer,base+8192-8,80)),pub=Uint8Array.from(new Uint8Array(memory.buffer,RESULT,16));
  const tcr=Uint8Array.from(new Uint8Array(memory.buffer,TCR,256));
  const status=service.db_run(...a);
  assert.equal(status,wanted,'isolated admission '+name);
  assert.deepEqual(snapshot(),before,'isolated arena preservation '+name);
  assert.deepEqual(new Uint8Array(memory.buffer,base+8192-8,80),outside,'isolated outside preservation '+name);
  assert.deepEqual(new Uint8Array(memory.buffer,RESULT,16),pub,'isolated publication preservation '+name);
  assert.deepEqual(new Uint8Array(memory.buffer,TCR,256),tcr,'isolated TCR preservation '+name);
  directed.push({name,status,arena_preserved:true,outside_preserved:true,publication_preserved:true,tcr_preserved:true});
 }
 fs.writeFileSync(dir+'/directed-'+base+'.json',JSON.stringify(directed,null,2)+'\n');
