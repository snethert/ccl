import assert from './assert.mjs';
import {startupInputs,materializeInputs,inputBytes,precompose} from './inputs.mjs';
export function ownerChecks(witness){
 let comparisons=0,refusals=0;
 for(const row of witness){assert.deepEqual([...precompose(String.fromCodePoint(...row.slice(0,2)))].map(c=>c.codePointAt(0)),row.slice(2),'native composition pair');comparisons++;}
 const input={imageName:'cafe\u0301',arguments:['','same','same','😀']},saved=startupInputs(input);
 input.imageName='changed';input.arguments[1]='changed';input.arguments.push('new');
 assert.deepEqual(saved,{imageName:'café',arguments:['','same','same','😀']},'private input snapshot');
 assert(Object.isFrozen(saved)&&Object.isFrozen(saved.arguments),'frozen inputs');comparisons++;
 const memory=new WebAssembly.Memory({initial:8}),bytes=new Uint8Array(memory.buffer);bytes.fill(0xa6);
 const good={imageName:'image',arguments:['','a','😀']};
 const bad=[null,{},[],{imageName:'i'}, {...good,extra:0},{...good,imageName:7},{...good,imageName:'a\0b'},
 {...good,imageName:'\ud800'},{...good,imageName:'\udfff'},{...good,imageName:'a'.repeat(4097)},
 {...good,arguments:'args'},{...good,arguments:[null]},{...good,arguments:['a\0b']},{...good,arguments:['\ud800']},
 {...good,arguments:['\udfff']},{...good,arguments:Array(257).fill('')},{...good,arguments:Array(16).fill('a'.repeat(4096))},
 {...good,arguments:Array(1)}];
 for(const input of bad){assert.throws(()=>materializeInputs({memory,base:65536,end:65568,input}),/startup inputs:/);assert(bytes.every(b=>b===0xa6),'refusal preservation');refusals++;}
 const size=inputBytes(good);
 for(const [base,end]of [[-8,size-8],[1,size+1],[NaN,size],[65536,65536+size-8],[65536,65536+size+8],[bytes.length-size+8,bytes.length+8]]){
  assert.throws(()=>materializeInputs({memory,base,end,input:good}),/startup inputs: extent/);assert(bytes.every(b=>b===0xa6),'extent refusal preservation');refusals++;
 }
 for(const input of [good,{imageName:'a'.repeat(4096),arguments:[]},{imageName:'',arguments:Array(256).fill('')},{imageName:'',arguments:Array(16).fill('a'.repeat(4096))}]){
  const size=inputBytes(input),base=bytes.length-size;bytes.fill(0xa6);
  const result=materializeInputs({memory,base,end:bytes.length,input});
  assert.equal(result.end,bytes.length,'exact fit');assert(bytes.subarray(0,base).every(b=>b===0xa6),'leading guard');
  const d=new DataView(memory.buffer),word=p=>d.getUint32(p,true),string=p=>{
   assert.equal(p&7,6);const h=word(p-6);assert.equal(h&255,191);const n=h>>>8;
   return String.fromCodePoint(...Array.from({length:n},(_,i)=>word(p-2+4*i)));
  };
  assert.equal(string(result.image),precompose(input.imageName),'materialized image');
  const args=[];for(let p=result.arguments;p!==77825;p=word(p-1)){assert.equal(p&7,1);assert(args.length<256);args.push(string(word(p+3)));}
  assert.deepEqual(args,input.arguments,'materialized argv order');comparisons++;
 }
 return {comparisons,refusals};
}
