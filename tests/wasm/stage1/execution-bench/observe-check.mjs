import assert from 'node:assert/strict';
import {benchmarkObserver} from './observe.mjs';
const memory=new WebAssembly.Memory({initial:1}),view=new DataView(memory.buffer);
const set=(offset,value)=>view.setUint32(offset,value,true);
set(48,1000);set(56,512);
const owner={collectionCount:0,atSafepoint(fn){return fn(this);},
  rootCells(values){return {values:()=>values,release(){}};},
  collect(){this.collectionCount++;set(56,2048);set(48,2200);}};
const observer=benchmarkObserver(memory,0,owner);
observer.request(()=>{observer.output(1,'EB-');observer.output(1,'GC\n');return 0;});
observer.output(1,'EB-BEGIN EB-CALL 0 4\n');set(48,2300);
observer.beforeCollection();set(48,900);owner.collectionCount++;observer.afterCollection();
set(48,950);observer.output(1,'EB-END EB-CALL 0 4 1 1000 12\n');
assert.equal(observer.result().samples[0].allocatedBytes,150);
assert.equal(observer.result().samples[0].collections,1);
const broken=benchmarkObserver(memory,0,{...owner,collect(){}});
assert.throws(()=>broken.request(()=>{broken.output(1,'EB-GC\n');return 0;}),/Assertion/);
assert.throws(()=>observer.output(1,'EB-END EB-CALL 0 4 1 1000 12\n'),/end without begin/);
console.log(JSON.stringify({status:'PASS',checks:['split-output','allocation-excludes-copy','collection-count','missing-collection-refused','orphan-end-refused']}));
