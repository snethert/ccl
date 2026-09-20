import assert from 'node:assert/strict';
import fs from 'node:fs';
import {regionModule} from './scalar-service.mjs';
const rows=[{start:0,end:8},{start:8,end:16},{start:65528,end:65536},{start:2147483648,end:2147483664},{start:4294967280,end:4294967288}];
const a=regionModule(rows),fn=new WebAssembly.Instance(a.module).exports.contains;
assert(a.disjoint);assert.deepEqual(WebAssembly.Module.imports(a.module),[]);
let count=0;
const points=[0,1,7,8,9,15,16,65527,65528,65532,65535,65536,2147483647,2147483648,2147483656,2147483663,2147483664,4294967279,4294967280,4294967284,4294967287,4294967288,4294967295];
for(const p of points)for(const n of [1,4,8,16,256,4294967295]){
 assert.equal(fn(p,n),Number(rows.some(r=>p>=r.start&&p<r.end&&p+n<=r.end)),p+'/'+n);count++;
}
let state=123456789;const random=()=>{state=(Math.imul(state,1664525)+1013904223)>>>0;return state;};
for(let i=0;i<10000;i++){const p=random(),n=random();assert.equal(fn(p,n),Number(rows.some(r=>p>=r.start&&p<r.end&&p+n<=r.end)));count++;}
const overlap=regionModule([{start:0,end:16},{start:8,end:24}]);assert.equal(overlap.disjoint,false);assert.equal(new WebAssembly.Instance(overlap.module).exports.contains(8,4),0);
assert.equal(new WebAssembly.Instance(regionModule([]).module).exports.contains(0,4),0);
fs.writeFileSync(process.argv[2],JSON.stringify({status:'PASS',comparisons:count,overlap_falls_back:true,empty_false:true},null,2)+'\n');
