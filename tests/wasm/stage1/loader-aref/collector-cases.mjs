// Both layout families are ordinary tagged-cell containers. Only a header
// roots the backing vector, and only that vector roots the cons payload.
function node(tag,values){const p=t(48),size=Math.ceil((4+4*values.length)/8)*8;
 assert(p+size<=t(52));put(p,(values.length<<8)|tag);
 values.forEach((v,i)=>put(p+4+4*i,v));set(48,p+size);return p+6;}
memory=new WebAssembly.Memory({initial:48,maximum:32769,shared:true});
for(const tag of [234,242]){
 setup();const payload=cons(471*4),data=node(250,[payload,N,N,N]);
 const values=tag===234?[8,16,data,0,0,8,8]:[8,16,data,0,0];
 const header=node(tag,values);put(EXTERNAL,header);
 const from=t(56),end=t(52),r=collect();poison(from,end);
 const moved=get(EXTERNAL),backing=get(moved+6),cell=get(backing-2);
 assert.notEqual(moved,header);assert.notEqual(backing,data);assert.notEqual(cell,payload);
 assert.equal(get(cell+3),471*4);assert.equal(r.objects,3);
 collect();assert.equal(get(get(get(get(EXTERNAL)+6)-2)+3),471*4);
 pass('array-header-movement-'+tag,r);
}
for(const [name,tag,values] of [
 ['array-minimum-width',234,[0xfffffffc,0,N,0]],
 ['array-rank-width',234,[8,0,N,0,0,0]],
 ['vector-header-width',242,[0,0,N,0,0,0]]
]){
 setup();put(EXTERNAL,node(tag,values));refused(name,collect,'collection refused 2');
}
setup();const truncated=node(234,[0,0,N,0,0]);put(truncated-6,(6<<8)|234);
refused('array-truncated-extent',collect,'collection refused 2');
