// Fixture embedding supplies a resident namespace and declared capabilities.
// Dispatch, numeric marshalling, handles and error transport are product code.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createNamespace} from '../../../../runtime/wasm32/namespace.mjs';
import {foreignLibraries} from '../../../../runtime/wasm32/foreign-libraries.mjs';
import {foreignService} from '../../../../runtime/wasm32/foreign-service.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
import {declaration} from './declaration.mjs';
export function create({memory,tcr,owner,config}) {
 const bytes=new Uint8Array(fs.readFileSync(config.library)),digest=sha256(bytes),entries=[],collections=[],events=[];
 const get=p=>new DataView(memory.buffer).getUint32(p,true),raw=owner.foreignBoundary;let active;
 const boundary={enter(operation){assert(!active);const words=Array.from({length:64},(_,i)=>get(tcr+4*i)),token=raw.enter(operation);
  active={operation,words,count:owner.collectionCount};return token;},leave(token){raw.leave(token);
  for(let i=0;i<64;i++)if(owner.collectionCount===active.count||![48,52,56,104,188,204].includes(4*i))assert.equal(get(tcr+4*i),active.words[i]);
  entries.push(active.operation);active=null;}};
 const imports={host:{collect(){assert(active);assert.equal(get(tcr+32),3);const r=owner.collectForeign();
  new Uint8Array(memory.buffer,r.source,r.usedBytes).fill(0xa5);collections.push({...r,state:get(tcr+32)});},observe(kind){assert(active);events.push(kind);}}};
 const names=['example','trap','destructor','primary','close','final-close','final-trap'];
 const namespace=createNamespace({version:1,cwd:'/lib',cclRoot:'/',entries:[{path:'/',kind:'directory'},
  {path:'/lib',kind:'directory'},...names.map(name=>({path:'/lib/'+name+'.wasm',kind:'file',bytes,sha256:digest}))]});
 const libraries=foreignLibraries({namespace,libraries:names.map(name=>({path:name+'.wasm',declaration:{...declaration(digest),name},imports})),boundary,errorTag:new WebAssembly.Tag({parameters:['i32']})});
 return {foreignRequest:foreignService({memory,tcr,owner,libraries}),result(){assert(!active);return {entries,collections,events,digest};}};
}
