// Derive all mutable regions from the admitted image and code inventories.
const PAGE=65536,MiB=1048576;
const need=(v,s)=>{if(!v)throw Error('layout: '+s);};
export const DEFAULT_CONFIG=Object.freeze({spaceBytes:32*MiB,freeTarget:16*MiB,valueStack:MiB,
 tempStack:MiB/2,controlStack:MiB,bindings:16384,generations:2,postImageCodes:8192,postImageRoots:65536,slotOffset:8,maximumPages:32769});
export function deriveLayout(config,{bootFunctions,bootRootCells=0,runtimeFunctions,runtimeRootCells,image,tcr=1024}){
 const c={...DEFAULT_CONFIG,...config},align=(n,a)=>Math.ceil(n/a)*a;
 for(const [key,value] of Object.entries(c))need(Number.isSafeInteger(value)&&value>=0,'config '+key);
 need(c.spaceBytes>=PAGE&&c.spaceBytes%PAGE===0&&c.valueStack>=16384&&c.valueStack%8===0&&
  c.tempStack>=16&&c.tempStack%8===0&&c.controlStack>=16&&c.controlStack%8===0&&c.bindings>=8&&c.bindings%8===0&&
  c.generations>0&&c.maximumPages<=32769&&c.maximumPages>0,'config extents');
 for(const n of [bootFunctions,bootRootCells,runtimeFunctions,runtimeRootCells])need(Number.isSafeInteger(n)&&n>=0,'inventory');
 const rows=16+bootFunctions+c.generations*runtimeFunctions+c.postImageCodes;
 need(rows<536870912,'code capacity');
 const rootCells=4+bootRootCells+c.generations*runtimeRootCells+c.postImageRoots;
 // Image root listing has at most one pointer per word, plus the TCR root.
 const logCapacity=rootCells+image.reduce((n,r)=>n+(r.end-r.start)/4,0)+1;
 const regions=[],claim=(name,role,start,bytes,extra={})=>{
  need(Number.isSafeInteger(start)&&start>=0&&start%8===0&&Number.isSafeInteger(bytes)&&bytes>0&&bytes%8===0,'extent '+name);
  const r={...extra,name,role,start,end:start+bytes};
  need(regions.every(o=>r.start>=o.end||o.start>=r.end),'overlap '+name);regions.push(r);return r;};
 claim('tcr','tcr',tcr,256);claim('c-stack','c-stack',1048576,65536);
 for(const [i,r] of image.entries())claim('image-'+i,'image',r.start,r.end-r.start,r);
 let p=Math.max(...regions.map(r=>r.end));
 const next=(name,role,bytes,a=PAGE)=>{p=align(p,a);const r=claim(name,role,p,align(bytes,8));p=r.end;return r;};
 const bindings=next('bindings','bindings',c.bindings);
 // The sentinel is eight bytes before the 16-byte aligned argument area.
 p=align(p+8,PAGE)-8;const vstack=claim('vstack','vstack',p,c.valueStack+8);p=vstack.end;
 const temp=next('temp','temp',c.tempStack),control=next('control','control',c.controlStack);
 const registry=next('registry','code-registry',8+16*rows);
 const rootList=next('root-list','root-list',align(4*logCapacity,PAGE)),external=next('external','external',align(4*rootCells,PAGE));
 const globals=next('runtime-globals','runtime-globals',16,16);
 next('scratch','scratch',align(Math.max(8*MiB,96+c.spaceBytes/8*20+logCapacity*12),PAGE));
 const spaces=[next('heap-0','space',c.spaceBytes),next('heap-1','space',c.spaceBytes)];
 const initialPages=Math.ceil(p/PAGE);need(initialPages<=c.maximumPages,'memory maximum');
 return {version:1,collector:'copying',workers:1,egc:false,tcr,maximumPages:c.maximumPages,logCapacity,
  regions:regions.filter(r=>r.role!=='space'),spaces:spaces.map(({name,start,end})=>({name,start,end})),
  groups:['module-constants','callbacks','registry','host'].map((kind,i)=>({kind,slots:[external.start+i*4]})),
  rows,slotOffset:c.slotOffset,tableCapacity:rows+c.slotOffset,registry:registry.start,external:external.start,
  root:vstack.start,bindings:bindings.start,runtimeGlobals:globals.start,freeTarget:c.freeTarget,
  tcrWords:{48:spaces[0].start,52:spaces[0].end,56:spaces[0].start,64:vstack.start+8,68:vstack.start+8,72:vstack.end,
   76:temp.start,80:temp.start,84:temp.end,88:control.start,92:control.start,96:control.end,104:bindings.start,
   120:vstack.start+8200,124:vstack.start+8264,128:vstack.start,200:7},
  stackDefaults:[c.valueStack,c.controlStack,c.tempStack],initialPages,configuration:c};
}
