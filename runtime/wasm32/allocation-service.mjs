import {CollectorOwner} from './collector-owner.mjs';
// A trusted single-Worker capability, never a Lisp callback. Failure may have
// moved roots, so generated callers must unwind from their published roots.
export function allocationService(owner,callError){
 if(!(owner instanceof CollectorOwner)||!(callError instanceof WebAssembly.Tag))throw new TypeError('allocation service capabilities');
 return bytes=>{
  try{owner.atSafepoint(o=>o.ensure(bytes>>>0));}
  catch(error){throw new WebAssembly.Exception(callError,[/inhibition state/.test(String(error))?11:6]);}
 };
}

export function heapSnapshotService(owner,callError){
 if(!(owner instanceof CollectorOwner)||!(callError instanceof WebAssembly.Tag))throw new TypeError('heap snapshot capabilities');
 return mask=>{
  try{return owner.atSafepoint(o=>o.heapSnapshot(mask));}
  catch(error){throw new WebAssembly.Exception(callError,[/growth maximum|growth refusal/.test(String(error))?6:11]);}
 };
}

export function objectValidityService(owner,callError){
 if(!(owner instanceof CollectorOwner)||!(callError instanceof WebAssembly.Tag))throw new TypeError('object validity capabilities');
 return word=>{
  try{return owner.atSafepoint(o=>o.validObject(word));}
  catch(error){throw new WebAssembly.Exception(callError,[11]);}
 };
}

// GC-lock operations can relocate before taking the first lock or collect
// after the final release. Their Lisp callers publish ordinary rooted frames.
export function collectionInhibitionService(owner,callError){
 if(!(owner instanceof CollectorOwner)||!(callError instanceof WebAssembly.Tag))throw new TypeError('collection inhibition capabilities');
 return delta=>{
  try{return owner.atSafepoint(o=>o.inhibitCollection(delta));}
  catch(error){throw new WebAssembly.Exception(callError,[/growth maximum|growth refusal/.test(String(error))?6:11]);}
 };
}
