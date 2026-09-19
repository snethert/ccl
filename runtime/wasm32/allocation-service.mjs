import {CollectorOwner} from './collector-owner.mjs';
// A trusted single-Worker capability, never a Lisp callback. Failure may have
// moved roots, so generated callers must unwind from their published roots.
export function allocationService(owner,callError){
 if(!(owner instanceof CollectorOwner)||!(callError instanceof WebAssembly.Tag))throw new TypeError('allocation service capabilities');
 return bytes=>{
  try{owner.atSafepoint(o=>o.ensure(bytes>>>0));}
  catch{throw new WebAssembly.Exception(callError,[6]);}
 };
}
