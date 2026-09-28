// Test-only Lisp service transport. The declaration, copy/handle API and owner
// are product inputs; no foreign instance receives the Lisp Memory.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {openForeignModule,foreignFailure} from '../../../../runtime/wasm32/foreign-module.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
import {declaration} from './declaration.mjs';
export function create({memory,tcr,owner,config}) {
 const bytes=fs.readFileSync(config.library),tag=new WebAssembly.Tag({parameters:['i32']});
 const get=p=>new DataView(memory.buffer).getUint32(p,true),word=o=>get(tcr+o);
 const raw=owner.foreignBoundary,entries=[],collections=[],cases=[];let args,active;
 const boundary={enter(operation){
  assert(!active);const before=Array.from({length:64},(_,i)=>word(i*4)),token=raw.enter(operation);
  active={operation,before,token,count:owner.collectionCount};return token;
 },leave(token){
  assert.equal(token,active.token);raw.leave(token);const moved=owner.collectionCount!==active.count;
  for(let i=0;i<64;i++)if(!moved||![48,52,56,104,188,204].includes(i*4))assert.equal(word(i*4),active.before[i],'return TCR '+i*4);
  assert.equal(word(32),2);assert.equal(word(144),0);entries.push({operation:active.operation,moved});active=null;
 }};
 const source=()=>{
  assert(!active);assert.equal(word(32),2);const pointer=get(args+8);
  assert.equal(pointer%8,6);const header=get(pointer-6);
  assert.equal(header>>>8,8);assert.equal(header&255,199);
  return new Uint8Array(memory.buffer,pointer-2,8);
 };
 return {
  processRequest(pointer,fallback){
   if(get(pointer)!==404)return fallback(pointer);
   args=pointer;const mode=get(args+4)>>2,events=[],start=collections.length;
   assert(mode>=0&&mode<=4);const imports={host:{collect(){
    assert.equal(word(32),3);const before=get(args+8),result=owner.collectForeign();
    assert.notEqual(get(args+8),before,'source root moved');assert.equal(word(32),3);
    new Uint8Array(memory.buffer,result.source,result.usedBytes).fill(0xa5);
    collections.push({...result,poisonedBytes:result.usedBytes,state:word(32)});
   },observe(kind,offset){assert.equal(word(32),3);events.push({kind,offset});}}};
   const l=openForeignModule({bytes,declaration:declaration(sha256(bytes),'utf-8'),imports,boundary,errorTag:tag});
   let a,b,value,primary;const secondary=[];
   try{
    a=l.allocate(16);b=l.allocate(16);
    // Every allocating foreign entry can move this root. Recompute its byte
    // address only now, and perform the copy without a collecting call.
    l.write(a,0,source());l.call('mode',[mode>=3?6:0]);
    value=l.call('run',[l.range(a),8,mode===2?2:mode===1||mode===4?1:mode===0?5:0]);
    const copied=l.read(a,0,8);source().set(copied);
   }catch(error){if(!foreignFailure(error))throw error;primary=error;}
   finally{
    for(const handle of [a,b])if(handle)try{l.release(handle);}catch(error){
     assert(foreignFailure(error));if(primary)secondary.push(foreignFailure(error).kind);else primary=error;
    }
   }
   const failure=primary?foreignFailure(primary):null;
   assert.equal(events.filter(e=>e.kind===1).length,mode===2?0:mode>=3?1:2,'release ordering');
   assert.deepEqual(secondary,mode===4?['trap']:[],'primary exception survives destructor trap');
   cases.push({mode,kind:failure?.kind??null,retired:l.state==='retired',releases:events.filter(e=>e.kind===1).length,
    secondary,collections:collections.length-start,source:[...source()]});
   l.close();return primary?-4:value*4;
  },
  result(){assert(!active);return {status:'PASS',entries,collections,cases,librarySha256:sha256(bytes)};}
 };
}
