import fs from 'node:fs';import assert from 'node:assert/strict';import {CollectorOwner} from './owner.mjs';import {sha256} from './sha256.mjs';
const [dir,output,only='all']=process.argv.slice(2),binary=fs.readFileSync(dir+'/collector.wasm'),digest=sha256(binary),NIL=77825,T=77838,rows=[];
for(const image of [524288,2147483648]){
 const memory=new WebAssembly.Memory({initial:Math.max(64,Math.ceil((image+65536)/65536)),maximum:32769,shared:true}),d=new DataView(memory.buffer),put=(p,v)=>d.setUint32(p,v,true),get=p=>d.getUint32(p,true),bytes=(p,n)=>new Uint8Array(memory.buffer,p,n),tcr=1024,root=131064,A=2097152,B=2162688;
 function setup(type=0){
  const regions=[['tcr',tcr,tcr+256],['image',77824,77864],['image',image,image+16],['vstack',root,root+32776],['temp',196608,212992],['control',212992,229376],['external',262144,266240],['bindings',266240,270336],['c-stack',1048576,1114112],['root-list',1180000,1184096],['scratch',1200000,1800000]].map(([role,start,end],i)=>({name:role+'-'+i,role,start,end}));
  const layout={version:1,collector:'copying',workers:1,egc:false,tcr,maximumPages:32769,logCapacity:32768,regions,spaces:[A,B].map((start,i)=>({name:'heap-'+i,start,end:start+256})),groups:['module-constants','callbacks','registry','host'].map((kind,i)=>({kind,slots:[262144+4*i]}))};
  for(const r of [...regions,...layout.spaces])bytes(r.start,r.end-r.start).fill(0);
  put(NIL-1,NIL);put(NIL+3,NIL);put(T-6,1850);for(let i=1;i<8;i++)put(T-6+4*i,NIL);for(let i=0;i<4;i++)put(262144+4*i,NIL);
  [[48,A+24],[52,A+256],[56,A],[68,root+8],[72,root+32776],[64,root+8],[128,root],[80,196608],[76,196608],[84,212992],[92,212992],[88,212992],[96,229376],[104,266240],[108,0],[120,root+8200],[124,root+8264],[188,NIL]].forEach(([o,v])=>put(tcr+o,v));
  put(root,0);put(root+4,0);put(A,92);put(A+4,68);put(A+8,NIL);put(A+12,A+1);put(A+16,148);put(A+20,124);
  [602,type,A+9,0].forEach((v,i)=>put(image+4*i,v));return layout;
 }
 if(only==='all'||only==='moving')for(const type of [0,4]){
  const layout=setup(type),owner=CollectorOwner.create(memory,binary,digest,layout);
  for(let turn=0;turn<2;turn++){const before=get(image+8),old=get(tcr+56),r=owner.atSafepoint(o=>o.collect());bytes(old,256).fill(0xda);
   assert.notEqual(get(image+8),before,'image contents root moves');assert.equal(get(image),602);const head=get(image+8),member=get(head+3);assert.equal(get(head-1),NIL);assert.deepEqual([get(member+3),get(member-1)],[68,92]);assert.equal(r.objects,2);assert.equal(r.reclaimed,turn===0?8:0);rows.push({image,type,turn,moving:true,reclaimed:r.reclaimed});}
 }
 for(const [name,change,why] of [
  ['native-three',l=>put(image,858),'strong population shape'],
  ['native-termination',l=>{put(image,1114);l.regions.find(r=>r.start===image).end=image+24;},'strong population shape'],
  ['truncated',l=>{const p=memory.buffer.byteLength-8;const r=l.regions.find(r=>r.start===image);r.start=p;r.end=p+8;put(p,602);put(p+4,0);},'strong population shape'],
  ['type-lowbits',l=>put(image+4,1),'strong population fields'],
  ['type-flags',l=>put(image+4,8),'strong population fields'],
  ['padding',l=>put(image+12,1),'strong population fields'],
 ]){if(only!=='all'&&only!==name)continue;const layout=setup();change(layout);const before=[bytes(tcr,256).slice(),bytes(A,256).slice(),bytes(image,32).slice(),bytes(root,16).slice()];
  assert.throws(()=>CollectorOwner.create(memory,binary,digest,layout),e=>e instanceof Error&&e.message.includes('collector-owner: '+why),name);
  [bytes(tcr,256),bytes(A,256),bytes(image,32),bytes(root,16)].forEach((v,i)=>assert.deepEqual(v,before[i],name+' preservation'));rows.push({image,refused:name});
 }
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',rows},null,2)+'\n');
