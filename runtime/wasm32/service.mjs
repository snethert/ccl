import {floatService} from './float-service.mjs';
// U1 library compatibility around the accepted mathematical primitive. Ordinary
// arithmetic stays in Wasm. This adapter only selects native library errors and
// the source-pinned bignum/infinity comparison convention.
export function lispFloatService(options){
 const raw=floatService(options),{memory}=options;
 const limits={32:1n<<128n,64:1n<<1024n};
 let cachedView=new DataView(memory.buffer);
 const view=()=>{const b=memory.buffer;if(cachedView.buffer!==b)cachedView=new DataView(b);return cachedView;};
 const get=p=>view().getUint32(p,true),set=(p,v)=>view().setUint32(p,v,true);
 const number=v=>{
  if(v%4===0)return {integer:BigInt((v>=2**31?v-2**32:v)/4)};
  const p=v-6,h=get(p),n=Math.floor(h/256);
  if(h%256===7){let x=0n;for(let i=n-1;i>=0;i--)x=(x<<32n)|BigInt(get(p+4+4*i));return {integer:BigInt.asIntN(32*n,x)};}
  return {width:h===271?32:64,value:h===271?view().getFloat32(p+4,true):view().getFloat64(p+8,true)};
 };
 return (op,root,safe)=>{
  op>>>=0;root>>>=0;safe>>>=0;
  if(op>=10&&op<=11&&safe<=1&&root+24<=memory.buffer.byteLength){
   const v=get(root+8),p=v-6;
   if(v%8===6&&p>=0&&p+(op===10?8:16)<=memory.buffer.byteLength&&get(p)===(op===10?271:791)){
    // Same-format FLOAT returns its input in U1. Validate the frame and both
    // numeric objects with a nonallocating comparison, without NaN signaling.
    raw(6,root,0);set(root+16,get(root+8));return 1<<10;
   }
  }
  const status=raw(op,root,safe);
  const a=number(get(root+8)),b=op>=10?{}:number(get(root+12));
  if(op>=4&&op<=9){
   // U1 widens a single first, then treats infinity's exponent/significand as
   // the magnitude 2^1024. Keep that source behavior, including its equality.
   const special=(a.integer!==undefined&&!Number.isFinite(b.value)&&!Number.isNaN(b.value))||(b.integer!==undefined&&!Number.isFinite(a.value)&&!Number.isNaN(a.value));
   if(special){const cv=x=>x.integer!==undefined?x.integer:(x.value<0?-(1n<<1024n):1n<<1024n),x=cv(a),y=cv(b);const yes=[x<y,x<=y,x===y,x!==y,x>=y,x>y][op-4];set(root+16,yes?77838:77825);}
   return status;
  }
  const width=op===10?32:op===11?64:a.width===64||b.width===64?64:32;
  const limit=limits[width];
  for(const [i,x] of [a,b].entries())if(x.integer!==undefined&&(x.integer>=limit||x.integer<=-limit)){
   set(root+16,77825);return 4|(20<<5)|((i+1)<<10)|(i===0?20<<12:20<<17);
  }
  return status;
 };
}
