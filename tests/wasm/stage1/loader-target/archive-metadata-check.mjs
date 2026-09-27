// Qualify metadata-only changes while reusing the full rewrite/byte witness.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const [kind,source,before,after]=process.argv.slice(2),read=p=>JSON.parse(fs.readFileSync(p));
const old=read(before+'.json'),current=read(after+'.json'),units=new Map(current.units.map(u=>[u.name,u]));
const hash=async path=>{const h=createHash('sha256');for await(const b of fs.createReadStream(path))h.update(b);return h.digest('hex');};
const hashes={};for(const suffix of ['.wat','.wasm','.template.wasm']){hashes[suffix]=await hash(after+suffix);assert.equal(hashes[suffix],await hash(before+suffix));}
const sources=new Map();
if(kind==='boot')for(const row of read(source+'/boot/code-set.json').modules)sources.set(row.name,row);
let file;
const directory=kind==='runtime'?read(source+'/bundles.json').files:[];
for(const f of current.functions){
 const unit=units.get(f.unit);
 if(kind==='runtime'&&unit.file!==file){
  file=unit.file;sources.clear();let id=0;
  const records=read(source+'/'+directory.find(r=>r.path===file).stem+'.records.json');
  const walk=r=>{sources.set('code_'+(++id),{arity:r[2],captures:r[3]});for(const child of r[8]??[])walk(child);};
  for(const unit of records.units)walk(unit.record);
 }
 const row=sources.get(f.source_name);assert.deepEqual(f.arity,row.arity);assert.equal(f.captures,row.captures);
 f.helpers=current.helper_sets[f.helper_set];delete f.helper_set;delete f.arity;delete f.captures;
}
delete current.helper_sets;delete current.helper_bodies;assert.deepEqual(current,old);
console.log(JSON.stringify({status:'PASS',functions:current.function_count,hashes,
 beforeBytes:fs.statSync(before+'.json').size,afterBytes:fs.statSync(after+'.json').size,
 checks:['WAT unchanged','template unchanged','binary unchanged','all original manifest fields unchanged after helper-set expansion','arity/captures equal compiler records']}));
