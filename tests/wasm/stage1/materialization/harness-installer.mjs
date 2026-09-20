// Fixture owner, not a new production lazy-loader profile. Publication uses
// the D2-validated module; every function is explicitly installed before use.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {install} from './materializer.mjs';
export {sha256 as sha} from './sha256.mjs';
export const PROFILE='d2-fixture-owner';
export class LazyLoader {
 constructor(o){this.o=o;this.rows=new Map(o.catalog.map(r=>[r.slot,{record:r,state:'COLD'}]));this.events=[];}
 defer(name,imports){const r=[...this.rows.values()].find(r=>r.record.name===name);assert(r&&!r.imports);r.imports=imports;return {host_entry:(...args)=>r.instance.exports.entry(...args)};}
 install(slot){const r=this.rows.get(slot),o=this.o;assert(r.state==='COLD');
  const data=JSON.parse(fs.readFileSync(o.directory+'/materialization.json'));
  const x=data.modules[r.record.name],profile=o.profile;
  const bytes=o.readBytes(r.record.name),template=fs.readFileSync(o.directory+'/templates/'+r.record.name+'.wasm');
  const module=install(bytes,x.outputs[profile],template,x.template,x.abi,x.classification,data.policy,profile);
  assert.equal(o.table.get(slot),null);assert.equal(o.tail_table.get(slot),null);
  const instance=new WebAssembly.Instance(module,r.imports);
  o.table.set(slot,instance.exports.entry);o.tail_table.set(slot,instance.exports.tail_entry);
  r.instance=instance;r.state='READY';this.events.push({slot,event:'INSTALLED',sha256:x.outputs[profile].binary_sha256});
 }
 snapshot(){return [...this.rows.values()].map(r=>({name:r.record.name,slot:r.record.slot,state:r.state}));}
}
