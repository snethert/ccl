import fs from 'node:fs';
import assert from 'node:assert/strict';
const [binary, output] = process.argv.slice(2);
const {exports:e} = new WebAssembly.Instance(new WebAssembly.Module(fs.readFileSync(binary)));
new Int32Array(e.memory.buffer).set([1,2,3,2]);
const cases=[['i32',3,3],['call',3,3],['svref',0,2],['f64',.5,.5],['f32',.5,.5]];
const n=4194304, trials=[];
for(const [name,x,slope] of cases){
  for(const count of [0,4,16,100,n])assert.equal(e[name](count,x),count*slope);
  const begin=performance.now();
  do{assert.equal(e[name](n,x),n*slope);}while(performance.now()-begin<250);
}
for(let trial=0;trial<9;trial++){
  for(const [name,x,slope] of cases){
    let calls=0,value;const begin=performance.now();
    do{value=e[name](n,x);calls++;}while(performance.now()-begin<50);
    const elapsedMs=performance.now()-begin;
    assert.equal(value,n*slope);
    trials.push({name,trial,n,calls,elapsedMs,value,nsPerIteration:elapsedMs*1e6/(calls*n)});
  }
  cases.push(cases.shift());
}
fs.writeFileSync(output,JSON.stringify({kind:'HAND-BUILT WASM EXECUTION',
  node:process.version,v8:process.versions.v8,execArgv:process.execArgv,trials,
  scope:'Engine reference only. No Lisp ABI, roots, allocation, overflow or FP exception policy. Optimizer may inline calls or hoist loads. JS batch dispatch and timing included.'},null,2)+'\n');
