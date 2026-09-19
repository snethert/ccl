if(['index-limit','empty','partial-capacity'].includes(fault)){
 const name=fault==='partial-capacity'?'sd_sequential':'sd_bind';
 assert.deepEqual(invoke(name,[44]),fault==='partial-capacity'?[44,44]:[44,412],fault+': formerly refused metadata now grows');
 assert.equal(get(108),16,'initial growth capacity');assert(get(104)!==610000,'vector was replaced');
 assert(Array.from({length:get(108)},(_,i)=>load(get(104)+4*i)).every(x=>x===243),'new vector restored after binding');
}else
