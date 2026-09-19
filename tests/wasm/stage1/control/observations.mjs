// This oracle derives the cleanup depths and reservations from o_nested's
// source and the public B/context layout, not from saved checkpoint words.
if(m.name==='o_mark'&&currentControlCase?.function==='o_nested'){
 const marker=load(get(64)+4)/4,expected=marker===11?[2,2,1]:marker===13?[2,1]:null;
 assert(expected,'only the two source cleanup entries execute');
 const records=[];for(let r=get(140);r;r=load(r))records.push(r);
 assert.deepEqual(records.map(r=>load(r+4)),expected,'source-derived cleanup control extents');
 assert.equal(get(88),get(92)+16*expected.length,'source-derived cleanup CSP');
 assert.equal(get(76),get(80),'cleanup has no retained arena allocation');
 const capacity=currentControlCase.capacity,retention=16*Math.ceil((48+4*capacity)/16);
 assert.equal(u32(context),records[0]+retention+4*capacity,'source-derived cleanup VSP checkpoint');
 assert.equal(load(u32(context)+32),records[0]+32,'source-derived cleanup root checkpoint');
 assert.equal(load(get(104)+4),28,'cleanup sees inner special value');
 assert(get(112)!==0&&load(get(112))===0,'cleanup has exactly one dynamic binding');
 assert.equal(get(148),1,'cleanup retains pending nonlocal exit');
 cleanupWitnesses.push(marker);
}
