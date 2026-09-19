// U1 restart: six node slots (istruct cell, name, action, report, interactive,
// test), then one alignment word outside the header's count.
for(const from of [262144,2147483648]){
 for(let field=0;field<6;field++){
  setup(from);const child=alloc([NIL,4*(401+field)]),words=[1666,NIL,NIL,NIL,NIL,NIL,NIL,from+9];words[1+field]=child;
  const restart=alloc(words,6);roots([restart]);run('restart-field-'+field+'-'+from);
  const relocated=load(ROOT+8);assert.notEqual(relocated,restart,'restart actually moved');
  const value=load(relocated-2+4*field);assert.notEqual(value,child,'restart field '+field+' moved');assert.equal(load(value+3),4*(401+field));
  assert.equal(load(relocated+22),from+9,'restart padding is not a root');
 }
 setup(from);const r=alloc([1666,NIL,NIL,NIL,NIL,NIL,NIL,0],6);store(r+6,r);roots([r,r]);run('restart-cycle-'+from);assert.equal(load(ROOT+8),load(ROOT+12));assert.equal(load(load(ROOT+8)+6),load(ROOT+8));
 setup(from);roots([77838,NIL]);run('canonical-t-root-'+from);assert.equal(load(ROOT+8),77838);assert.equal(load(ROOT+12),NIL);
 for(const count of [5,7]){
  setup(from);const p=alloc([count*256+130,...Array(count).fill(NIL)],6);roots([p]);
  const bytes=new Uint8Array(memory.buffer,from,load(TCR+48)-from).slice(),head=new Uint8Array(memory.buffer,ROOT,32).slice(),tcr=new Uint8Array(memory.buffer,TCR,256).slice();
  assert.equal(wasm.instance.exports.collect(config),2,'unadmitted istruct count '+count);
  assert.deepEqual(new Uint8Array(memory.buffer,from,bytes.length),bytes);assert.deepEqual(new Uint8Array(memory.buffer,ROOT,32),head);assert.deepEqual(new Uint8Array(memory.buffer,TCR,256),tcr);
  tests.push({name:'unadmitted-istruct-'+count+'-'+from,status:'REFUSED',code:2});
 }
}
