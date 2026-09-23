import assert from 'node:assert/strict';

// The second load starts with published class roots. No graph projection,
// CORE-CONDITION-PREPARE, native class catalog, or class-table builder runs.
export function checkBootClasses({gen,owners,get,put,root,collect,initialize=false}) {
 const symbol=(pkg,name)=>{
  const row=owners.find(x=>x.package===pkg&&x.name===name);assert(row,pkg+'::'+name);
  return gen.ownerWords.get(row.id);
 };
 const entry=(pkg,name)=>{
  const owner=owners.find(x=>x.package===pkg&&x.name===name);assert(owner,name);
  const module=gen.mods.find(x=>x.cplMode&&x.function===owner.id)||
    (name==='CORE-CONDITION-PREPARE'&&gen.mods.find(x=>x.function===owner.id));assert(module,name);
  return module.name;
 };
 const invoke=(pkg,name,args)=>gen.invoke(entry(pkg,name),args);
 if(initialize)invoke('WASM32-COMPILER','CORE-CONDITION-PREPARE',[get(root+8)]);
 const tableSymbol=symbol('CCL','%FIND-CLASSES%');
 assert.equal(get(tableSymbol+2),get(get(root+8)+10),'global class table is the image table');
 // Every captured class has a live cell, and every cell resolves through
 // the generated FIND-CLASS path. Keep iteration cursors in the root frame.
 put(root+4,3);put(root+12,get(get(root+8)+42));put(root+16,77825);
 let count=0;
 while(get(root+12)!==77825){
  const pair=get(get(root+12)+3),name=get(pair+3),expected=get(pair-1);
  assert.equal(invoke('COMMON-LISP','FIND-CLASS',[name])[0],expected);
  put(root+12,get(get(root+12)-1));count++;
  if(count%64===0)collect();
 }
 assert.equal(count,612);
 const condition=invoke('COMMON-LISP','MAKE-CONDITION',[symbol('WASM32-COMPILER','CPL-DERIVED')])[0];
 put(root+16,condition);collect();
 const payload=invoke('COMMON-LISP','SLOT-VALUE',[get(root+16),symbol('WASM32-COMPILER','PAYLOAD')])[0];
 const other=invoke('COMMON-LISP','SLOT-VALUE',[get(root+16),symbol('WASM32-COMPILER','OTHER')])[0];
 assert.equal(payload,43*4);assert.equal(other,41*4);
 collect();
 assert.equal(get(tableSymbol+2),get(get(root+8)+10),'class root survives collection');
 put(root+4,1);put(root+12,77825);put(root+16,77825);
 return [true,count,payload/4,other/4];
}
