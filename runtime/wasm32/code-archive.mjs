// Trusted-owner archive admission. Compilation is per tier; publication is per
// FASL unit. A generation owns one immutable code window and one root block.
import {sha256} from './sha256.mjs';
import {snapshotBytes} from './bytes.mjs';
import {inspect} from './binary.mjs';
import {entryRanges} from './ranges.mjs';
import {installArchive} from './archive-materializer.mjs';
import {signatures} from './bundle.mjs';
export const ARCHIVE_PACKAGING='code-archive-v2';
const need=(v,s)=>{if(!v)throw Error('code archive: '+s);};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const uint=n=>Number.isSafeInteger(n)&&n>=0&&n<=0xffffffff;
const digest=s=>typeof s==='string'&&/^[0-9a-f]{64}$/.test(s);
export function admitCodeArchive({bytes,manifest,digest:expectedDigest,env,capabilities={},versions,policy,
  allocateCode,reserveRoots,registerRoots,slotOffset=8,maxGenerations=Infinity,measure=(_p,run)=>run()}) {
 env={...env};capabilities=Object.fromEntries(Object.entries(capabilities).map(([k,v])=>[k,{...v}]));
 need(manifest&&typeof manifest==='object','MANIFEST');
 manifest=structuredClone(manifest);
 const count=manifest.function_count;
 need(manifest.version===1&&manifest.packaging===ARCHIVE_PACKAGING,'PACKAGING');
 need(same(manifest.abi,versions.abi)&&same(manifest.layout,versions.layout),'VERSIONS');
 need(uint(count)&&count>0&&count<=536870911&&uint(manifest.root_cells),'COUNTS');
 need(Array.isArray(manifest.functions)&&manifest.functions.length===count&&Array.isArray(manifest.units)&&
   Array.isArray(manifest.shared_symbols)&&new Set(manifest.shared_symbols).size===manifest.shared_symbols.length,'INVENTORY');
 need(digest(expectedDigest)&&expectedDigest===manifest.binary_sha256&&digest(manifest.template_sha256),'DIGEST');
 need(env.memory instanceof WebAssembly.Memory&&env.table instanceof WebAssembly.Table&&env.tail_table instanceof WebAssembly.Table&&env.table!==env.tail_table&&uint(slotOffset),'CAPABILITIES');
 need(maxGenerations===Infinity||(Number.isSafeInteger(maxGenerations)&&maxGenerations>0),'GENERATION_LIMIT');
 need([allocateCode,reserveRoots,registerRoots].every(f=>typeof f==='function'),'ROOT_AUTHORITY');
 const units=new Map(),names=new Set(),exports=new Set(),owned=new Set();let nextRoot=manifest.shared_symbols.length;
 for(const [i,f] of manifest.functions.entries()){
  need(f&&f.code_offset===i&&typeof f.name==='string'&&!names.has(f.name)&&typeof f.export==='string'&&!exports.has(f.export),'FUNCTION');
  names.add(f.name);exports.add(f.export);
 }
 for(const u of manifest.units){
  need(u&&typeof u.name==='string'&&!units.has(u.name)&&typeof u.wire==='string'&&uint(u.symbol_count)&&u.root_base===nextRoot,'UNIT');
  nextRoot+=u.symbol_count;
  need(Array.isArray(u.functions)&&u.functions.length>0,'UNIT_FUNCTIONS');
  for(const i of u.functions){need(uint(i)&&i<count&&!owned.has(i)&&manifest.functions[i].unit===u.name,'UNIT_FUNCTIONS');owned.add(i);}
  need([4,5,6].includes(u.record_version)&&digest(u.record_sha256),'CODE_RECORD');
  need(Array.isArray(u.shared)&&u.shared.every(s=>Array.isArray(s)&&s.length===3),'SHARED_SYMBOLS');const indices=new Set();
  for(const [identity,index,cell] of u.shared){
   need(typeof identity==='string'&&uint(index)&&index<u.symbol_count&&!indices.has(index)&&uint(cell)&&
     manifest.shared_symbols[cell]===identity,'SHARED_SYMBOL');indices.add(index);
  }
  for(const i of u.functions){const f=manifest.functions[i],wires=new Set();
   need(Array.isArray(f.symbols)&&f.symbols.every(s=>Array.isArray(s)&&s.length===2)&&Array.isArray(f.codes),'IMPORTS');
   for(const [wire,index] of f.symbols){need(typeof wire==='string'&&!wires.has(wire)&&uint(index)&&index<u.symbol_count,'SYMBOL_WIRE');wires.add(wire);}
   const codeNames=new Set();for(const c of f.codes){need(c&&typeof c.name==='string'&&!codeNames.has(c.name)&&ownedCode(c.code_offset),'CODE_IMPORT');codeNames.add(c.name);}
   function ownedCode(id){return uint(id)&&id<count&&(manifest.boot===true||u.functions.includes(id));}
  }
  units.set(u.name,u);
 }
 need(nextRoot===manifest.root_cells&&owned.size===count,'COMPLETE_UNITS');
 need(manifest.d2?.outputs?.full&&manifest.d2.template&&manifest.d2.classification&&manifest.d2.abi,'D2');
 bytes=snapshotBytes(bytes);
 const x=inspect(bytes,{ownerRetry:true});
 const fixed=[
  {module:'env',name:'memory',kind:'memory',flags:3,minimum:1,maximum:32769},
  {module:'env',name:'tcr',kind:'global',type:'i32',mutable:0},
  {module:'env',name:'table',kind:'table',element:'funcref',flags:0,minimum:0,maximum:null},
  {module:'env',name:'tail_table',kind:'table',element:'funcref',flags:0,minimum:0,maximum:null},
  {module:'env',name:'code_registry',kind:'global',type:'i32',mutable:0},
  ...[['call_error',['i32']],['type_error',['i32','i32']],['nonlocal_exit',['i32']]].map(([name,params])=>({module:'env',name,kind:'tag',signature:{params,results:[]}})),
  ...['roots','code_base'].map(name=>({module:'env',name,kind:'global',type:'i32',mutable:0})),
  ...[['owner','ensure',['i32'],[]],['integer','calculate',['i32','i32'],['i32']],['floating','calculate',['i32','i32','i32'],['i32']]].map(([module,name,params,results])=>({module,name,kind:'function',signature:{params,results}}))];
 const sorted=a=>[...a].sort((a,b)=>(a.module+'.'+a.name).localeCompare(b.module+'.'+b.name));
 need(same(sorted(x.imports),sorted(fixed)),'IMPORT_SET');
 need(same(x.imports,manifest.d2.outputs.full.imports),'IMPORT_MANIFEST');
 need(x.exports.length===2*count&&Array.isArray(manifest.entries)&&manifest.entries.length===count,'EXPORT_SET');
 const ranges=new Map(entryRanges(bytes,{ownerRetry:true,inspected:x,validated:true}).map(r=>[r.role,r])),exportMap=new Map(x.exports.map(e=>[e.name,e]));
 for(const [i,f] of manifest.functions.entries()){
  const row=manifest.entries[i];need(row&&row.code_offset===i,'ENTRY_OFFSET');
  const bodies=[];
  for(const role of ['entry','tail_entry']){
   const name=f.export+'.'+role,e=exportMap.get(name),r=ranges.get(name);
   need(e&&e.kind===0&&same(x.types[x.functions[e.index]],signatures[role]),'SIGNATURE');
   need(same(row[role],r),'RANGE');bodies.push(bytes.subarray(r.start,r.end));
  }
  const body=new Uint8Array(bodies[0].length+bodies[1].length);body.set(bodies[0]);body.set(bodies[1],bodies[0].length);
  need(sha256(body)===row.body_sha256,'BODY_DIGEST');
 }
 const module=measure('archive.compile',()=>installArchive(bytes,manifest,policy,x));bytes=null;
 // Runtime closures retain only identity/dispatch rows, never validation inputs.
 const functions=manifest.functions.map(f=>({name:f.source_name,unit:f.unit,export:f.export}));
 const rootCount=manifest.root_cells;
 manifest=null;
 const view=()=>new DataView(env.memory.buffer),get=p=>view().getUint32(p,true),put=(p,v)=>view().setUint32(p,v,true);
 const registry=env.code_registry;
 need(uint(registry)&&registry%8===0&&registry+8<=env.memory.buffer.byteLength,'REGISTRY');
 const capacity=get(registry);need(get(registry+4)===1&&registry+8+16*capacity<=env.memory.buffer.byteLength,'REGISTRY');
 const generations=[],sessions=new Map();let transaction=null;
 function createGeneration(){
  need(generations.length<maxGenerations,'GENERATION_CAPACITY');
  const journal=[];
  try{
   const codeBase=allocateCode(count,journal);
   need(uint(codeBase)&&codeBase>0&&codeBase+count<=Math.min(capacity,536870912)&&
     codeBase+count+slotOffset<=Math.min(env.table.length,env.tail_table.length),'CAPACITY');
   const roots=measure('archive.roots',()=>reserveRoots(rootCount,journal));
   const imports={env:{...env,roots:roots.base,code_base:codeBase*4},...capabilities};
   const instance=new WebAssembly.Instance(module,imports);
   const g={index:generations.length,codeBase,roots,instance,units:new Map(),sharedFilled:new Set()};
   generations.push(g);
   if(transaction){transaction.undo.push(...journal,()=>generations.pop());transaction.commit.push(()=>roots.commit?.());}
   else roots.commit?.();return g;
  }catch(e){for(let i=journal.length-1;i>=0;i--)journal[i]();throw e;}
 }
 function entries(g,u){return u.functions.map(i=>{const f=functions[i],codeId=g.codeBase+i;
  return {record:{name:f.name,code_id:codeId,slot:codeId+slotOffset},codeId,
   instance:{exports:{entry:g.instance.exports[f.export+'.entry'],tail_entry:g.instance.exports[f.export+'.tail_entry']}}};});}
 function install(session,name,record,symbolValues){
  const s=sessions.get(session),unit=s?.byWire.get(name);
  need(unit&&sha256(JSON.stringify(record))===unit.record_sha256,'CODE_RECORD');
  need(Array.isArray(symbolValues)&&symbolValues.length===unit.symbol_count&&symbolValues.every(uint),'SYMBOL_COUNT');
  const g=s.g,u=g.units.get(unit.name);need(u?.session===session,'UNRESERVED_UNIT');
  const cells=Array.from({length:unit.symbol_count},(_,i)=>g.roots.base+4*(unit.root_base+i));
  if(u.state==='published'){
   need(same(cells.map(get),symbolValues),'IMPORT_IDENTITY');
   for(const e of entries(g,unit)){const p=registry+8+16*e.codeId;
    need(same([0,4,8,12].map(o=>get(p+o)),[e.record.slot,4,17,23]),'REGISTRY_CHANGED');
    need(env.table.get(e.record.slot)===e.instance.exports.entry&&env.tail_table.get(e.record.slot)===e.instance.exports.tail_entry,'TABLE_CHANGED');}
   return g.codeBase+unit.functions[0];
  }
  const sharedWrites=new Map();
  for(const [,index,cell] of unit.shared){const p=g.roots.base+4*cell,value=symbolValues[index];
   if(g.sharedFilled.has(cell))need(get(p)===value,'SHARED_IDENTITY');
   else if(sharedWrites.has(cell))need(sharedWrites.get(cell)[1]===value,'SHARED_IDENTITY');
   else sharedWrites.set(cell,[p,value]);
  }
  for(const e of entries(g,unit)){const p=registry+8+16*e.codeId;
   need([0,4,8,12].every(o=>get(p+o)===0)&&env.table.get(e.record.slot)===null&&env.tail_table.get(e.record.slot)===null,'SLOT_OCCUPIED');}
  const journal=[],write=(p,v)=>{const old=get(p);journal.push(()=>put(p,old));put(p,v);};
  try{
   cells.forEach((p,i)=>write(p,symbolValues[i]));
   for(const [cell,[p,value]] of sharedWrites){write(p,value);g.sharedFilled.add(cell);journal.push(()=>g.sharedFilled.delete(cell));}
   measure('bundle.roots',()=>registerRoots(g.roots,[...cells,...[...sharedWrites.values()].map(([p])=>p)],journal));
   measure('bundle.publish',()=>{for(const e of entries(g,unit)){
    const p=registry+8+16*e.codeId,slot=e.record.slot;
    [slot,4,17,23].forEach((v,i)=>write(p+4*i,v));
    journal.push(()=>{env.table.set(slot,null);env.tail_table.set(slot,null);});
    env.table.set(slot,e.instance.exports.entry);env.tail_table.set(slot,e.instance.exports.tail_entry);
   }});
   u.state='published';if(transaction)transaction.undo.push(...journal,()=>{u.state='reserved';});return g.codeBase+unit.functions[0];
  }catch(e){for(let i=journal.length-1;i>=0;i--)journal[i]();throw e;}
 }
 const api=Object.freeze({
  prepare:()=>{if(!generations.length)createGeneration();},
  reserve(session,unitNames){
   need(!sessions.has(session)&&Array.isArray(unitNames)&&new Set(unitNames).size===unitNames.length,'SESSION');
   const byWire=new Map();for(const name of unitNames){const u=units.get(name);need(u&&!byWire.has(u.wire),'UNIT');byWire.set(u.wire,u);}
   const g=generations.find(g=>unitNames.every(n=>!g.units.has(n)))??createGeneration();
   for(const name of unitNames)g.units.set(name,{state:'reserved',session});
   sessions.set(session,{g,byWire});return g.index;
  },
  release(session){const s=sessions.get(session);if(!s)return;
   for(const u of s.byWire.values()){const state=s.g.units.get(u.name);if(state.state==='reserved')s.g.units.delete(u.name);else delete state.session;}
   sessions.delete(session);
  },
  install,
  installAll(rows,after){
   need(!transaction&&generations.length===0,'BOOT_STATE');
   const token=Symbol('boot'),tx={undo:[],commit:[]};transaction=tx;
   try{
    api.reserve(token,rows.map(r=>r.name));
    for(const r of rows)install(token,units.get(r.name).wire,r.record,r.values);
    const result=api.entries(token);after();for(const commit of tx.commit)commit();api.release(token);return result;
   }catch(e){for(let i=tx.undo.length-1;i>=0;i--)tx.undo[i]();sessions.delete(token);throw e;}
   finally{transaction=null;}
  },
  entries(session){const s=sessions.get(session);return s?[...s.byWire.values()].filter(u=>s.g.units.get(u.name).state==='published').flatMap(u=>entries(s.g,u)):[];},
  storage:()=>({modules:1,generations:generations.length,reservedRootCells:generations.length*rootCount,
   publishedUnits:generations.reduce((n,g)=>n+[...g.units.values()].filter(u=>u.state==='published').length,0),openSessions:sessions.size})
 });
 return api;
}
