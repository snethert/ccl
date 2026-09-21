// Trusted image-owner handoff. Addresses must come from the actual selected
// image's termination roots; this module does not discover or authenticate them.
export const POLICY='stage1-no-finalization-v1';
export function admitTerminationExclusion({memory,policy,region,slots}){
 const need=(ok,why)=>{if(!ok)throw Error('termination exclusion: '+why);};
 const word=n=>Number.isSafeInteger(n)&&n>=0&&n<=0xffffffff;
 need(policy===POLICY,'policy');
 need(memory instanceof WebAssembly.Memory,'memory');
 const view=new DataView(memory.buffer),names=['populationData','pendingCallbacks','functionCount','automaticEnabled'];
 need(region&&word(region.start)&&word(region.end)&&region.start%4===0&&region.end%4===0&&region.start<region.end&&region.end<=view.byteLength,'region');
 need(slots&&Object.keys(slots).length===4&&names.every(n=>Object.hasOwn(slots,n)),'slot inventory');
 const addresses=names.map(n=>slots[n]);
 need(addresses.every(p=>word(p)&&p%4===0&&p>=region.start&&p+4<=region.end)&&new Set(addresses).size===4,'slot extent/alias');
 const values=addresses.map(p=>view.getUint32(p,true));
 need(values[0]===77825,'registered objects');
 need(values[1]===77825,'pending callbacks');
 need(values[2]===0,'function registrations');
 need(values[3]===77825,'automatic scheduling');
 return Object.freeze({policy,slots:Object.freeze({...slots}),values:Object.freeze(values)});
}
