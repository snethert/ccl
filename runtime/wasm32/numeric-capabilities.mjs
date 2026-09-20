import {CollectorOwner} from './collector-owner.mjs';
import {allocationService} from './allocation-service.mjs';
import {integerService} from './integer-service.mjs';
// Identity authentication inside one trusted Worker, not code signing. The
// private association prevents accidental mixing of two owners or memories.
const owners=new WeakMap();
export function numericCapabilities(options){
 const {owner,memory,tcr,callError}=options;
 if(!(owner instanceof CollectorOwner)||owner.tcr!==tcr||owner.view.buffer!==memory?.buffer)
  throw Error('NUMERIC_OWNER');
 const calculate=integerService(options),ensure=allocationService(owner,callError);
 const bundle=Object.freeze({ensure,calculate});
 owners.set(bundle,{memory,tcr,callError,owner});
 return bundle;
}
export function admitNumericCapabilities(bundle,{memory,tcr,call_error}){
 const o=owners.get(bundle);
 if(!o||o.memory!==memory||o.tcr!==tcr||o.callError!==call_error||o.owner.view.buffer!==memory.buffer)
  throw Error('NUMERIC_CAPABILITY');
 return bundle;
}
