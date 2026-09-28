// HOSTFM scalar lower layer. The embedding supplies the FOREIGN publication and
// admission hooks; this module never receives Lisp memory or Lisp addresses.
import {snapshotBytes} from './bytes.mjs';
import {sha256} from './sha256.mjs';
import {inspectForeign} from './foreign-binary.mjs';

const failures=new WeakMap();
const codes=Object.freeze({trap:1,exception:2,host:3});
// A resource-only module checks the port tag's exact (i32) signature using
// engine linking; the JS Tag object alone does not expose that signature.
const tagType=new WebAssembly.Module(new Uint8Array([
  0,97,115,109,1,0,0,0,1,5,1,96,1,127,0,2,8,1,1,101,1,116,4,0,0
]));
const need=(ok,reason)=>{if(!ok)throw Error('foreign-module: '+reason);};
const signature=s=>JSON.stringify([s?.params,s?.results]);
const key=s=>JSON.stringify([s.module,s.name]);
const freeze=value=>{if(value&&typeof value==='object'){
  Object.values(value).forEach(freeze);Object.freeze(value);
}return value;};
const scalar=(value,type)=>{
  if(type==='i32')need(Number.isInteger(value)&&value>=-2147483648&&value<=2147483647,'I32');
  else if(type==='i64')need(typeof value==='bigint'&&BigInt.asIntN(64,value)===value,'I64');
  else need(typeof value==='number','FLOAT');
};
const argumentsFor=(args,types)=>{
  need(Array.isArray(args)&&args.length===types.length,'ARITY');
  const values=[...args];need(values.length===types.length,'ARITY');
  for(let i=0;i<values.length;i++)scalar(values[i],types[i]);
  return values;
};

// Metadata retains the original foreign exception/trap without exposing it
// across the live Wasm caller. Weak keys do not keep old failures alive.
export const foreignFailure=exception=>failures.get(exception);

export function openForeignModule({bytes,declaration,imports={},boundary,errorTag}) {
  const source=snapshotBytes(bytes),d=structuredClone(declaration);
  need(d?.version===1&&typeof d.name==='string'&&d.name.length>0,'DECLARATION');
  need(d.policy==='per-worker','POLICY');
  need(typeof d.sha256==='string'&&sha256(source)===d.sha256,'DIGEST');
  need(Array.isArray(d.imports)&&Array.isArray(d.exports)&&Array.isArray(d.tables),'SURFACE');
  need(boundary&&typeof boundary.enter==='function'&&typeof boundary.leave==='function','BOUNDARY');
  need(errorTag instanceof WebAssembly.Tag,'ERROR_TAG');
  try{new WebAssembly.Instance(tagType,{e:{t:errorTag}});}catch{need(false,'ERROR_TAG_SIGNATURE');}
  // Capture the hooks now: later caller mutation cannot replace admission.
  const enter=boundary.enter.bind(boundary),leave=boundary.leave.bind(boundary);
  const m=inspectForeign(source);
  need(m.memories.length===1&&d.memory&&m.memories[0].minimum===d.memory.minimum&&
       m.memories[0].maximum===d.memory.maximum,'MEMORY_LIMITS');
  need(m.tables.length===d.tables.length&&m.tables.every((table,i)=>
    table.minimum===d.tables[i]?.minimum&&table.maximum===d.tables[i]?.maximum),'TABLE_LIMITS');
  const memoryExports=m.exports.filter(e=>e.kind===2);
  need(memoryExports.length===1&&memoryExports[0].index===0&&memoryExports[0].name===d.memory.export,'MEMORY_EXPORT');
  need(m.exports.every(e=>e.kind===0||e.kind===2),'EXPORT_KIND');
  const declared=new Map();
  for(const e of d.exports){
    need(typeof e.name==='string'&&!declared.has(e.name),'EXPORT_DECLARATION');
    const actual=m.exports.find(x=>x.kind===0&&x.name===e.name);
    need(actual&&signature(actual.signature)===signature(e),'EXPORT_SIGNATURE');declared.set(e.name,e);
  }
  need(declared.size===m.exports.filter(e=>e.kind===0).length,'EXPORT_SET');
  const init=d.initialization;
  need(init&&['none','start','export'].includes(init.kind),'INITIALIZATION');
  need((m.start!==null)===(init.kind==='start'),'START_CONVENTION');
  if(init.kind==='export')need(declared.has(init.name)&&signature(declared.get(init.name))==='[[],[]]','INITIALIZER_SIGNATURE');
  if(init.kind==='start')need(signature(m.types[m.functions[m.start]])==='[[],[]]','START_SIGNATURE');
  const initializerIndex=init.kind==='start'?m.start:init.kind==='export'?m.exports.find(e=>e.name===init.name).index:null;
  const initializerNames=new Set(m.exports.filter(e=>e.kind===0&&e.index===initializerIndex).map(e=>e.name));

  let state='initializing',busy=false,instance;
  const importObject=Object.create(null),importNames=new Set();
  need(m.imports.length===d.imports.length,'IMPORT_SET');
  for(const actual of m.imports){
    const name=key(actual),matches=d.imports.filter(row=>key(row)===name);
    need(!importNames.has(name)&&matches.length===1,'IMPORT_DECLARATION');importNames.add(name);
    need(signature(matches[0])===signature(actual),'IMPORT_SIGNATURE');
    const fn=imports[actual.module]?.[actual.name];need(typeof fn==='function','IMPORT_MISSING');
    const target=importObject[actual.module]??=Object.create(null);
    target[actual.name]=(...args)=>{
      need(busy,'IMPORT_OUTSIDE_FOREIGN');
      const result=fn(...args);
      need(!result||typeof result.then!=='function','ASYNC_IMPORT');
      if(actual.results.length===1)scalar(result,actual.results[0]);
      else if(actual.results.length>1)return argumentsFor(result,actual.results);
      return result;
    };
  }
  freeze(d);
  function invoke(operation,run){
    need(!busy,'REENTRY');need(state!=='retired','RETIRED');
    busy=true;let token,result,cause,failed=false;
    try{token=enter(operation);
      if(token&&typeof token.then==='function'){state='retired';need(false,'ASYNC_BOUNDARY');}
    }catch(error){busy=false;if(state==='retired')instance=null;throw error;}
    try{result=run();}catch(error){
      failed=true;cause=error;
      if(error instanceof WebAssembly.RuntimeError||state==='initializing')state='retired';
    }
    // Admission errors belong to the owner. Returning a catchable Lisp error
    // after failed admission would grant heap access before it was authorized.
    try{const admitted=leave(token);need(!admitted||typeof admitted.then!=='function','ASYNC_BOUNDARY');}catch(error){
      state='retired';throw new AggregateError(failed?[cause,error]:[error],
        'foreign-module: ADMISSION_FAILED',{cause:failed?cause:error});
    }finally{busy=false;if(state==='retired')instance=null;}
    if(failed){
      const kind=cause instanceof WebAssembly.RuntimeError?'trap':cause instanceof WebAssembly.Exception?'exception':'host';
      const error=new WebAssembly.Exception(errorTag,[codes[kind]]);
      failures.set(error,Object.freeze({library:d.name,operation,kind,cause,retired:state==='retired'}));
      throw error;
    }
    return result;
  }
  const module=new WebAssembly.Module(source);
  // Instantiation itself is an entry: the start section may execute imports.
  instance=invoke('instantiate',()=>new WebAssembly.Instance(module,importObject));
  if(init.kind==='export')invoke('initialize:'+init.name,()=>instance.exports[init.name]());
  state='ready';
  return Object.freeze({
    declaration:d,
    get state(){return state;},
    call(name,args=[]){
      need(state==='ready','RETIRED');
      const entry=declared.get(name);need(entry,'UNDECLARED_EXPORT');
      need(!initializerNames.has(name),'INITIALIZER_ONCE');
      const values=argumentsFor(args,entry.params);
      return invoke('call:'+name,()=>instance.exports[name](...values));
    },
    close(){need(!busy,'REENTRY');state='retired';instance=null;}
  });
}
