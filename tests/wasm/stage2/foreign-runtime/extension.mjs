// Fixture transport through the shared boot driver's declared host extension.
// Opcode 100 is test-only. The library and CollectorOwner boundary are product.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {openForeignModule,foreignFailure} from '../../../../runtime/wasm32/foreign-module.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';

export function create({memory,tcr,owner,config}) {
 const bytes=fs.readFileSync(config.library),tag=new WebAssembly.Tag({parameters:['i32']});
 const declaration={version:1,name:'runtime-fixture',sha256:sha256(bytes),policy:'per-worker',
  memory:{export:'memory',minimum:1,maximum:2},tables:[],initialization:{kind:'export',name:'initialize'},
  imports:[{module:'host',name:'collect',params:[],results:[]},{module:'host',name:'fail',params:[],results:[]}],
  exports:[{name:'initialize',params:[],results:[]},{name:'run',params:['i32','i32'],results:['i32']}]};
 const get=p=>new DataView(memory.buffer).getUint32(p,true),word=o=>get(tcr+o);
 const snapshot=()=>Array.from({length:64},(_,i)=>word(i*4));
 const raw=owner.foreignBoundary,entries=[],collections=[],failures=[];
 let library,args,active;
 const boundary={enter(operation){
  const before=snapshot(),token=raw.enter(operation);
  assert.equal(word(32),3);assert.equal(word(144),word(128));
  snapshot().forEach((v,i)=>{if(![32,144].includes(i*4))assert.equal(v,before[i],'entry TCR '+i*4);});
  active={operation,before,token,collections:owner.collectionCount,payload:get(args+8)};
  return token;
 },leave(token){
  assert.equal(token,active.token);raw.leave(token);
  const after=snapshot(),moved=owner.collectionCount!==active.collections;
  const collectorFields=[48,52,56,104,188,204];
  after.forEach((v,i)=>{if(!moved||!collectorFields.includes(i*4))assert.equal(v,active.before[i],'return TCR '+i*4);});
  assert.equal(word(32),2);assert.equal(word(144),0);
  if(moved)assert.notEqual(get(args+8),active.payload,'generated argument root moved');
  entries.push({operation:active.operation,moved,restoredWords:64-(moved?collectorFields.length:0),
   rootHead:word(128),state:word(32),descriptor:word(144)});active=null;
 }};
 const imports={host:{collect(){
  assert.equal(word(32),3);assert.equal(word(144),word(128));
  const before=owner.collectionCount,result=owner.collectForeign();
  assert.equal(owner.collectionCount,before+1,'real collection');
  assert.notEqual(result.source,result.destination);assert.equal(word(32),3,'foreign execution still active');
  // Retire the entire old live extent, including forwarding words. Any stale
  // Lisp local will now fail the generated semantic witnesses.
  new Uint8Array(memory.buffer,result.source,result.usedBytes).fill(0xa5);
  collections.push({before,after:owner.collectionCount,...result,poisonedBytes:result.usedBytes,state:word(32)});
 },fail(){throw Error('foreign host failure');}}};
 return {
  processRequest(pointer,fallback){
   if(get(pointer)!==400)return fallback(pointer);
   args=pointer;const mode=get(args+4)>>2;
   if(mode===10){library?.close();library=null;return 0;}
   if(mode===11)return library?.state==='retired'?4:0;
   assert(mode>=0&&mode<=5);assert.equal(word(32),2);
   const payload=get(args+8);assert.equal(payload%8,1);const value=get(payload+3)>>2;
   if(library?.state==='retired')return -16;
   library??=openForeignModule({bytes,declaration,imports,boundary,errorTag:tag});
   try{return library.call('run',[mode,value])*4;}
   catch(error){
    const failure=foreignFailure(error);if(!failure)throw error;
    assert.equal(word(32),2,'admission before Lisp condition');assert.equal(word(144),0);
    failures.push({mode,kind:failure.kind,retired:failure.retired});
    return -error.getArg(tag,0)*4;
   }
  },
  result(){assert(!active);return {status:'PASS',entries,collections,failures,
   librarySha256:sha256(bytes),scope:'One Lisp Worker; generated roots and Lisp cleanup through a fixture scalar transport. No multi-Worker D5 or Lisp callback.'};}
 };
}
