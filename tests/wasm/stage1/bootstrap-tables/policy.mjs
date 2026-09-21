// Stage 1 owner policy, explicitly chosen by the user. No weak bits are set.
export const STRONG_POLICY='stage1-bootstrap-strong-v1';
export function strongPlan(site,policy){
 if(policy!==STRONG_POLICY)throw Error('strong substitution requires explicit policy');
 if(!site||!['eq','eql','equal'].includes(site.test)||!['key','value'].includes(site.weak))throw Error('table constructor policy');
 if(!Number.isInteger(site.size)||site.size<0||site.size>16384||
    !Number.isFinite(site.rehashSize)||site.rehashSize<1||
    !Number.isFinite(site.rehashThreshold)||site.rehashThreshold<=0||site.rehashThreshold>1)throw Error('table constructor options');
 return Object.freeze({policy,site:site.id,test:site.test,requestedWeak:site.weak,
  weak:null,size:site.size,rehashSize:site.rehashSize,rehashThreshold:site.rehashThreshold,
  retention:'keys-and-values',stage2:'weak-semantics'});
}
export function createStrongEQ({site,policy,memory,service,base,end,capacity}){
 const plan=strongPlan(site,policy);
 // Never substitute identity comparison for EQL or EQUAL.
 if(plan.test!=='eq')throw Error('equality service not installed: '+plan.test);
 if(!(memory instanceof WebAssembly.Memory)||!Number.isInteger(capacity)||capacity<4||capacity>16384||
    (capacity&(capacity-1))||capacity<plan.size)throw Error('table capacity');
 const bytes=64+8*capacity;
 if(!Number.isSafeInteger(base)||base<0||base%8||!Number.isSafeInteger(end)||
    end!==base+bytes||end>memory.buffer.byteLength)throw Error('table extent');
 if(service.ht_size(capacity)!==bytes)throw Error('table service size');
 if(service.ht_init(base,end,capacity)!==0)throw Error('table construction');
 return Object.freeze({plan,table:base+6,end,capacity});
}
