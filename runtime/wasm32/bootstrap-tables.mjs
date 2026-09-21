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
export function plannedCapacity(site,liveCount){
 if(!Number.isSafeInteger(liveCount)||liveCount<0)throw Error('measured population required');
 const need=Math.max(4,site.size,liveCount+Math.max(16,Math.ceil(liveCount/4)));
 if(need>16384)throw Error('bootstrap table capacity exceeds 16384');
 return 2**Math.ceil(Math.log2(need));
}
export function createStrongEQ({site,policy,memory,service,base,end,capacity,liveCount}){
 const plan=strongPlan(site,policy);
 // Never substitute identity comparison for EQL or EQUAL.
 if(plan.test!=='eq')throw Error('equality service not installed: '+plan.test);
 const required=plannedCapacity(site,liveCount);
 if(!(memory instanceof WebAssembly.Memory)||capacity!==required)throw Error('table capacity');
 const bytes=64+8*capacity;
 if(!Number.isSafeInteger(base)||base<0||base%8||!Number.isSafeInteger(end)||
    end!==base+bytes||end>memory.buffer.byteLength)throw Error('table extent');
 if(service.ht_size(capacity)!==bytes)throw Error('table service size');
 if(service.ht_init(base,end,capacity)!==0)throw Error('table construction');
 return Object.freeze({plan,table:base+6,end,capacity});
}
