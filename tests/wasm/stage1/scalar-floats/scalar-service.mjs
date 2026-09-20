import {createHash} from 'node:crypto';
import {lispFloatService} from './service.mjs';
const need=(x,s)=>{if(!x)throw Error('SCALAR_'+s);};
const u=n=>{const a=[];do{let b=n%128;n=Math.floor(n/128);a.push(b|(n?128:0));}while(n);return a;};
const si=n=>{n=BigInt(n);const a=[];for(;;){let b=Number(n&127n);n>>=7n;const done=(n===0n&&!(b&64))||(n===-1n&&(b&64));a.push(b|(done?0:128));if(done)return a;}};
const name=s=>[...u(s.length),...Buffer.from(s)];
const section=(id,body)=>[id,...u(body.length),...body];
// Pure Wasm binary search over immutable, disjoint pinned spans. No linear-memory
// metadata, JS callback, start function or imported authority in this module.
export function regionModule(regions){
 const rows=regions.map(r=>({...r})).sort((a,b)=>a.start-b.start);
 const disjoint=rows.every((r,i)=>!i||rows[i-1].end<=r.start);
 const constant=n=>[0x42,...si(n)],p=[0x20,0,0xad];
 function tree(lo,hi){
  if(lo===hi)return [0x41,0];const mid=(lo+hi)>>1,r=rows[mid];
  return [...p,...constant(r.start),0x54,0x04,0x7f,...tree(lo,mid),0x05,
   ...p,...constant(r.end),0x54,0x04,0x7f,...p,0x20,1,0xad,0x7c,...constant(r.end),0x58,
   0x05,...tree(mid+1,hi),0x0b,0x0b];
 }
 const body=[0,...(disjoint?tree(0,rows.length):[0x41,0]),0x0b];
 const bytes=Uint8Array.from([0,97,115,109,1,0,0,0,
  ...section(1,[1,0x60,2,0x7f,0x7f,1,0x7f]),...section(3,[1,0]),
  ...section(7,[1,...name('contains'),0,0]),...section(10,[1,...u(body.length),...body])]);
 return {module:new WebAssembly.Module(bytes),disjoint,rows,bytes};
}
export function scalarFloatService(options){
 // Construction of the original service performs all existing capability,
 // digest and pinned-region checks, even when its hot branch is never called.
 const slow=lispFloatService(options),{memory,tcr,owner,scalarBytes,scalarDigest,pinned=[]}=options;
 need(createHash('sha256').update(scalarBytes).digest('hex')===scalarDigest,'DIGEST');
 const module=new WebAssembly.Module(scalarBytes);
 const globals=['tcr','boundary','eligible','a0','a1','b0','b1','v0','v1','t0','t1','c0','c1','l0','l1','maximum'];
 const imports=['env/memory/memory',...globals.map(n=>'env/'+n+'/global'),'regions/contains/function','fallback/calculate/function'].sort();
 need(JSON.stringify(WebAssembly.Module.imports(module).map(i=>[i.module,i.name,i.kind].join('/')).sort())===JSON.stringify(imports),'IMPORTS');
 need(JSON.stringify(WebAssembly.Module.exports(module))===JSON.stringify([{name:'calculate',kind:'function'}]),'EXPORTS');
 const admission=owner.scalarAdmission,region=regionModule(pinned);
 const env={memory,tcr,boundary:admission.boundary,...admission.bounds};
 for(const n of ['a0','a1','b0','b1','eligible'])env[n]=new WebAssembly.Global({value:'i32',mutable:true},0);
 function refresh(){
  const pair=owner.spaces;
  [env.a0.value,env.a1.value,env.b0.value,env.b1.value]=[pair[0].start,pair[0].end,pair[1].start,pair[1].end];
  // Preserve the original first-span semantics for any overlapping declarations.
  // Such inputs use the old service, including its original refusals.
  env.eligible.value=Number(region.disjoint&&!region.rows.some(r=>pair.some(s=>r.start<s.end&&s.start<r.end)));
 }
 refresh();
 const fallback=(op,root,safe)=>{try{return slow(op,root,safe);}finally{refresh();}};
 return new WebAssembly.Instance(module,{env,regions:new WebAssembly.Instance(region.module).exports,fallback:{calculate:fallback}}).exports.calculate;
}
