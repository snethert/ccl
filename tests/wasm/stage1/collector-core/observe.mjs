if(currentControlCase&&m.name==='irq_gc'){
 const before={from:get(56),used:get(48),limit:get(52),tlb:get(104),cap:get(108)},destination=before.from===3145728?collectionOrigin:3145728;
 // Root SLOT inventory from the owner, independent of Lisp allocation. Symbols
 // are pinned in this first service; values/function cells may refer to heap.
 const extra=[];
 for(const p of new Set(Object.values(symbols))){if(p%8===6&&load(p-6)===1850)extra.push(p+2,p+6);}
 for(let i=0;i<currentControlCase.nodes.length;i++){const p=16385+8*i;extra.push(p-1,p+3);}
 const config=1200000;
 new Uint8Array(memory.buffer,config,96).fill(0);
 setCollector=(o,v)=>store(config+o,v);
 setCollector(0,tcr);setCollector(16,destination);setCollector(20,destination+32768);setCollector(68,32768);setCollector(72,1180000);setCollector(76,extra.length);setCollector(80,1800000);
 extra.forEach((slot,i)=>store(1180000+4*i,slot));
 const result=collector.exports.collect(config);assert.equal(result,0,currentControlCase.id+': collector accepted live state');
 const bytes=get(48)-get(56),reclaimed=before.used-before.from-bytes;
 assert.equal(load(config+92),reclaimed,'independent reclaimed byte count');
 assert(reclaimed>=8,'discarded generated cons reclaimed');
 // Poison every retired word so stale pointers cannot accidentally read copies.
 new Uint8Array(memory.buffer,before.from,before.limit-before.from).fill(0xdd);
 movedVectors.push({function:currentControlCase.function,live_objects:load(config+84),root_slots:load(config+88),bytes,reclaimed,source:before.from,destination});relocations++;
 inspect('after collection '+currentControlCase.id);
}
