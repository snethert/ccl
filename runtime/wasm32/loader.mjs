import {createHash} from 'node:crypto';
import {inspect} from './binary.mjs';
export const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const need=(ok,reason)=>{if(!ok)throw Error(reason);};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const B={params:['i32','i32'],results:['i32','i32']},TAIL={params:['i32','i32','i32'],results:['i32','i32']};
export const PROFILE='wasm32-shared-B-exnref-control-v1';

export function validate(bytes,record) {
  need(sha(bytes)===record.sha256,'BINARY_DIGEST');
  need(record.profile===PROFILE,'PROFILE');
  need(WebAssembly.validate(bytes),'INVALID_WASM');
  const m=inspect(bytes);
  const expected=[
    {module:'env',name:'memory',kind:'memory',flags:3,minimum:1,maximum:32769},
    {module:'env',name:'tcr',kind:'global',type:'i32',mutable:0},
    {module:'env',name:'table',kind:'table',element:'funcref',flags:0,minimum:0,maximum:null},
    {module:'env',name:'tail_table',kind:'table',element:'funcref',flags:0,minimum:0,maximum:null},
    {module:'env',name:'code_registry',kind:'global',type:'i32',mutable:0},
    {module:'env',name:'call_error',kind:'tag',signature:{params:['i32'],results:[]}},
    {module:'env',name:'type_error',kind:'tag',signature:{params:['i32','i32'],results:[]}},
    {module:'env',name:'nonlocal_exit',kind:'tag',signature:{params:['i32'],results:[]}}
  ];
  const fixed=m.imports.filter(i=>i.module==='env');need(same(fixed,expected),'ENV_IMPORTS');
  const keys=new Set();
  for(const i of m.imports){const key=i.module+'.'+i.name;need(!keys.has(key),'DUPLICATE_IMPORT');keys.add(key);
    if(i.module!=='env')need(['symbols','keywords','codes'].includes(i.module)&&i.kind==='global'&&i.type==='i32'&&i.mutable===0,'IMPORT_AUTHORITY');}
  need(same(m.imports,record.imports),'IMPORT_MANIFEST');
  need(m.exports.length===2,'EXPORT_SET');
  for(const [role,signature] of [['entry',B],['tail_entry',TAIL]]){
    const e=m.exports.find(e=>e.name===role);need(e&&e.kind===0&&same(m.types[m.functions[e.index]],signature),'EXPORT_SIGNATURE');
    need(record.entries[role]?.index===e.index&&record.entries[role]?.role===role,'EXPORT_ROLE');
  }
  return m;
}

// The catalog and imported capabilities belong to the trusted Worker owner.
// This is integrity/role authentication against that catalog, not code signing.
// No await, imported code execution, GC or Lisp callback occurs in publication.
export class LazyLoader {
  #rows=new Map(); #names=new Set(); #busy=false; #o;
  constructor(options){
    this.#o=options;this.events=[];
    need(options.table!==options.tail_table,'DISTINCT_TABLES');
    need(options.nonlocal_exit instanceof WebAssembly.Tag&&options.nonlocal_exit!==options.call_error,'DISTINCT_EXIT_TAG');
    const seen=new Set();
    for(const source of options.catalog){const r=structuredClone(source);
      need(Number.isInteger(r.slot)&&r.slot>0&&r.slot<options.table.length&&r.slot<options.tail_table.length,'SLOT');
      need(r.code===r.slot&&r.version===4&&r.signature===17&&r.role===23,'CODE_ROLE');
      need(!seen.has(r.slot)&&!this.#names.has(r.name),'CATALOG_UNIQUE');seen.add(r.slot);this.#names.add(r.name);
      this.#rows.set(r.slot,{record:r,state:'DECLARED'});
    }
  }
  defer(name,imports,observe){
    const row=[...this.#rows.values()].find(r=>r.record.name===name);need(row?.state==='DECLARED','DECLARATION');
    const o=this.#o,r=row.record;
    // Copy only own data properties. No getters or mutable Global objects may
    // smuggle execution or change an imported identity after declaration.
    const clean=Object.create(null);
    for(const [namespace,nd] of Object.entries(Object.getOwnPropertyDescriptors(imports))){need('value'in nd,'IMPORT_GETTER');const fields=nd.value;clean[namespace]=Object.create(null);
      for(const [key,d] of Object.entries(Object.getOwnPropertyDescriptors(fields))){need('value'in d,'IMPORT_GETTER');clean[namespace][key]=d.value;}}
    need(clean.env.memory===o.memory&&clean.env.table===o.table&&clean.env.tail_table===o.tail_table&&clean.env.call_error===o.call_error&&clean.env.nonlocal_exit===o.nonlocal_exit,'CAPABILITIES');
    need(Number.isInteger(clean.env.tcr)&&Number.isInteger(clean.env.code_registry),'RAW_GLOBALS');
    for(const ns of ['symbols','keywords','codes'])for(const value of Object.values(clean[ns]??{}))need(Number.isInteger(value)&&value>=0&&value<=4294967295,'IDENTITY_GLOBAL');
    row.imports=clean;row.observe=observe;
    const stub=new WebAssembly.Instance(o.stub,{loader:{install:slot=>this.install(slot),slot:r.slot,table:o.table,tail_table:o.tail_table}});
    row.stubs={entry:stub.exports.entry,tail_entry:stub.exports.tail_entry};row.pair=row.stubs;row.state='COLD';
    need(o.table.get(r.slot)===null&&o.tail_table.get(r.slot)===null,'SLOT_OCCUPIED');
    o.table.set(r.slot,row.pair.entry);o.tail_table.set(r.slot,row.pair.tail_entry);
    return {...row.stubs,host_entry:(self,count)=>{this.install(r.slot);return row.raw.entry(self,count);}};
  }
  #check(row){const o=this.#o,r=row.record,view=new DataView(o.memory.buffer),base=row.imports.env.code_registry;
    need(base%8===0&&base>=0&&base+8+16*(r.code+1)<=view.byteLength,'REGISTRY_EXTENT');
    const get=p=>view.getUint32(p,true),p=base+8+16*r.code;
    need(get(base)>r.code&&get(base+4)===1&&same([get(p),get(p+4),get(p+8),get(p+12)],[r.slot,r.version,r.signature,r.role]),'REGISTRY_IDENTITY');
    need(o.table.get(r.slot)===row.pair.entry&&o.tail_table.get(r.slot)===row.pair.tail_entry,'TABLE_IDENTITY');
  }
  install(slot){
    const row=this.#rows.get(slot),o=this.#o;
    if(this.#busy){this.events.push({slot,event:'REFUSED',reason:'REENTRANT_INSTALL'});throw new WebAssembly.Exception(o.call_error,[7]);}
    try {
      need(row&&row.state!=='DECLARED','UNDECLARED_SLOT');this.#check(row);
      if(row.state==='READY'){this.events.push({slot,event:'READY_HIT'});return;}
      need(row.state==='COLD','INSTALL_STATE');this.#busy=true;row.state='LOADING';
      const bytes=Buffer.from(o.readBytes(row.record.name)); // snapshot once
      validate(bytes,row.record);
      // No start, segments, imported functions or getters: instantiation cannot
      // execute user code or write shared state. Both exports precede publication.
      const instance=new WebAssembly.Instance(new WebAssembly.Module(bytes),row.imports);
      const raw={entry:instance.exports.entry,tail_entry:instance.exports.tail_entry};
      const pair=row.observe?{
        entry:new WebAssembly.Instance(o.observer,{env:{entry:raw.entry,observe:row.observe.entry}}).exports.entry,
        tail_entry:new WebAssembly.Instance(o.tailObserver,{env:{entry:raw.tail_entry,observe:row.observe.tail_entry}}).exports.entry
      }:raw;
      need(typeof pair.entry==='function'&&typeof pair.tail_entry==='function','ENTRY_PAIR');
      this.#check(row);
      o.table.set(slot,pair.entry);o.tail_table.set(slot,pair.tail_entry);
      row.raw=raw;row.pair=pair;row.state='READY';this.events.push({slot,event:'INSTALLED',sha256:row.record.sha256});
    } catch(e){
      if(row?.state==='LOADING')row.state='COLD';
      this.events.push({slot,event:'REFUSED',reason:e.code==='ENOENT'?'MISSING_MODULE':e.message});
      throw new WebAssembly.Exception(o.call_error,[['REGISTRY_EXTENT','REGISTRY_IDENTITY','TABLE_IDENTITY'].includes(e.message)?4:7]);
    } finally {this.#busy=false;}
  }
  // Test/owner unload point, invoked only while no Lisp invocation is active.
  reset(){need(!this.#busy,'BUSY_RESET');const o=this.#o;
    for(const row of this.#rows.values()){need(row.state!=='DECLARED','RESET_DECLARATION');row.pair=row.stubs;row.state='COLD';o.table.set(row.record.slot,row.pair.entry);o.tail_table.set(row.record.slot,row.pair.tail_entry);}
  }
  snapshot(){return [...this.#rows.values()].map(r=>({name:r.record.name,slot:r.record.slot,state:r.state}));}
}
