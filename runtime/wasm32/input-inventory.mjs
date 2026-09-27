// Application-owned input buffers only. These counters describe ownership, not
// engine retention or GC timing. Categories are disjoint backing-buffer sets.
export function inputInventory(){
 const rows=new Map(),manifests=new Map();let peakBytes=0,peakCount=0,peakManifests=0;
 const need=(v,s)=>{if(!v)throw Error('input inventory: '+s);};
 function snapshot(extra={}){
  const buffers=new Map(),categories={};
  for(const {category,values} of rows.values())for(const buffer of values){
   need(!buffers.has(buffer)||buffers.get(buffer)===category,'category alias');buffers.set(buffer,category);
  }
  for(const [buffer,category] of buffers){if(!buffer.byteLength)continue;const r=categories[category]??={bytes:0,count:0};r.bytes+=buffer.byteLength;r.count++;}
  for(const [category,row] of Object.entries(extra)){need(!categories[category],'category overlap');categories[category]={...row};}
  const bytes=Object.values(categories).reduce((n,r)=>n+r.bytes,0),count=Object.values(categories).reduce((n,r)=>n+r.count,0);
  peakBytes=Math.max(peakBytes,bytes);peakCount=Math.max(peakCount,count);
  peakManifests=Math.max(peakManifests,manifests.size);
  return {bytes,count,peakBytes,peakCount,validationManifests:manifests.size,peakValidationManifests:peakManifests,categories};
 }
 return Object.freeze({
  hold(label,category,values){need(!rows.has(label),'duplicate owner');
   const buffers=values.map(v=>ArrayBuffer.isView(v)?v.buffer:v);need(buffers.every(b=>b instanceof ArrayBuffer),'buffer');
   rows.set(label,{category,values:buffers});snapshot();},
  release:label=>rows.delete(label),
  holdManifest:(label,value)=>{need(!manifests.has(label),'duplicate manifest');manifests.set(label,value);snapshot();},
  releaseManifest:label=>manifests.delete(label),snapshot
 });
}
