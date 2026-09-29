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

  // Owned ranges are an optional extension of the scalar declaration. An
  // allocation identity never exposes its offset or the foreign Memory.
  const buffers=d.buffers,managedNames=new Set(),ranges=new Map();
  const uint=n=>Number.isSafeInteger(n)&&n>=0&&n<=0x7fffffff;
  if(buffers!==undefined){
    need(buffers&&uint(buffers.maximumBytes)&&buffers.maximumBytes>0,'BUFFER_LIMIT');
    need(declared.has(buffers.allocate)&&signature(declared.get(buffers.allocate))==='[["i32"],["i32"]]'&&
         declared.has(buffers.release)&&signature(declared.get(buffers.release))==='[["i32"],[]]','BUFFER_ABI');
    for(const name of [buffers.allocate,buffers.release]){
      const index=m.exports.find(e=>e.kind===0&&e.name===name).index;
      for(const e of m.exports)if(e.kind===0&&e.index===index)managedNames.add(e.name);
    }
  }
  for(const e of d.exports){
    const rows=e.ranges??[],used=new Set();need(Array.isArray(rows),'RANGES');
    for(const r of rows){
      need(buffers&&!managedNames.has(e.name),'RANGE_EXPORT');
      need(r&&uint(r.pointer)&&uint(r.length)&&r.pointer!==r.length&&
           e.params[r.pointer]==='i32'&&e.params[r.length]==='i32'&&
           !used.has(r.pointer)&&!used.has(r.length),'RANGE_SIGNATURE');
      need(['read','write','readwrite'].includes(r.access)&&['bytes','utf-8'].includes(r.encoding),'RANGE_FORMAT');
      used.add(r.pointer);used.add(r.length);
    }
    ranges.set(e.name,rows);
  }
  // An alias must not erase the range contract of the same Wasm function.
  for(const a of m.exports.filter(e=>e.kind===0))for(const b of m.exports.filter(e=>e.kind===0&&e.index===a.index))
    need(JSON.stringify(ranges.get(a.name))===JSON.stringify(ranges.get(b.name)),'RANGE_ALIAS');

  let state='initializing',busy=false,instance;
  const handles=new WeakMap(),slices=new WeakMap(),live=new Set();
  function retire(){state='retired';instance=null;for(const h of live){h.active=false;h.finalizer?.cancel();}live.clear();}
  const idle=()=>{need(!busy,'REENTRY');need(state==='ready','RETIRED');};
  const memory=()=>instance.exports[d.memory.export];
  const owned=handle=>{const h=handles.get(handle);need(h?.active,'HANDLE');return h;};
  const extent=(h,offset,length)=>{
    need(uint(offset)&&uint(length)&&length<=h.size-offset,'BUFFER_RANGE');
    need(h.pointer+offset+length<=memory().buffer.byteLength,'MEMORY_RANGE');
    return h.pointer+offset;
  };
  const view=(h,offset,length)=>new Uint8Array(memory().buffer,extent(h,offset,length),length);
  const textRange=(h,offset,length,encoding)=>{
    if(encoding==='utf-8'){
      try{new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(view(h,offset,length));}
      catch{need(false,'UTF8');}
    }
  };
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
    }catch(error){busy=false;if(state==='retired')retire();throw error;}
    try{result=run();}catch(error){
      failed=true;cause=error;
      if(error instanceof WebAssembly.RuntimeError||state==='initializing')state='retired';
    }
    // Admission errors belong to the owner. Returning a catchable Lisp error
    // after failed admission would grant heap access before it was authorized.
    try{const admitted=leave(token);need(!admitted||typeof admitted.then!=='function','ASYNC_BOUNDARY');}catch(error){
      state='retired';throw new AggregateError(failed?[cause,error]:[error],
        'foreign-module: ADMISSION_FAILED',{cause:failed?cause:error});
    }finally{busy=false;if(state==='retired')retire();}
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
  const api=Object.freeze({
    declaration:d,
    get state(){return state;},
    call(name,args=[]){
      idle();
      const entry=declared.get(name);need(entry,'UNDECLARED_EXPORT');
      need(!initializerNames.has(name),'INITIALIZER_ONCE');
      need(!managedNames.has(name),'MANAGED_EXPORT');
      need(Array.isArray(args)&&args.length===entry.params.length,'ARITY');
      const values=[...args],checked=[];
      for(const r of ranges.get(name)){
        const slice=slices.get(values[r.pointer]);need(slice,'RANGE_HANDLE');
        const h=owned(slice.handle),length=values[r.length];
        values[r.pointer]=extent(h,slice.offset,length)|0;
        if(r.access!=='write')textRange(h,slice.offset,length,r.encoding);
        checked.push({r,h,offset:slice.offset,length});
      }
      argumentsFor(values,entry.params);
      const result=invoke('call:'+name,()=>instance.exports[name](...values));
      for(const {r,h,offset,length} of checked)if(r.access!=='read')textRange(h,offset,length,r.encoding);
      return result;
    },
    allocate(size){
      idle();need(buffers,'BUFFERS');need(uint(size)&&size>0&&size<=buffers.maximumBytes,'ALLOCATION_SIZE');
      const pointer=invoke('allocate:'+buffers.allocate,()=>instance.exports[buffers.allocate](size))>>>0;
      // A broken allocator cannot leave an admitted live offset, including an
      // overlap with another allocation. Retirement never calls that allocator.
      if(pointer===0||pointer+size>memory().buffer.byteLength||
         [...live].some(h=>pointer<h.pointer+h.size&&h.pointer<pointer+size)){
        retire();need(false,'ALLOCATION_RESULT');
      }
      const handle=Object.freeze({}),h={pointer,size,active:true};handles.set(handle,h);live.add(h);return handle;
    },
    range(handle,offset=0){
      idle();const h=owned(handle);extent(h,offset,0);
      const slice=Object.freeze({});slices.set(slice,{handle,offset});return slice;
    },
    write(handle,offset,bytes){
      idle();const h=owned(handle),copy=snapshotBytes(bytes);
      view(h,offset,copy.length).set(copy);
    },
    read(handle,offset,length){idle();return view(owned(handle),offset,length).slice();},
    finalize(handle,owner,anchor){
      idle();const h=owned(handle);need(!h.finalizer,'FINALIZER_ONCE');
      h.finalizer=owner.atSafepoint(o=>o.registerFinalizer(anchor,()=>api.release(handle)));
    },
    release(handle){
      need(!busy,'REENTRY');const h=handles.get(handle);need(h,'HANDLE');
      if(!h.active)return false;
      // Invalidate before a destructor can fail. Even a recoverable failure
      // leaves its allocation retired; an uncertain free is never retried.
      h.active=false;live.delete(h);h.finalizer?.cancel();
      if(state==='ready')invoke('release:'+buffers.release,()=>instance.exports[buffers.release](h.pointer|0));
      return true;
    },
    close(){need(!busy,'REENTRY');retire();}
  });
  return api;
}
