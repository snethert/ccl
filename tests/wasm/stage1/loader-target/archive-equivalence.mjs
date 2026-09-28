// Independent S-expression comparison, then reconstruction of each v1 module
// from the linked bodies. WABT output must equal the retained v1 template.
import fs from 'node:fs';
import {readRecords} from './record-reader.mjs';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {decodeTargetBundle} from '../../../../runtime/wasm32/target-bundle.mjs';
const [kind,source,archiveStem,baseline,out]=process.argv.slice(2),read=p=>JSON.parse(fs.readFileSync(p));
fs.mkdirSync(out,{recursive:true});
const archive=read(archiveStem+'.json'),units=new Map(archive.units.map(u=>[u.name,u]));
const hash=s=>createHash('sha256').update(s).digest('hex');
function parse(s){
 const tokens=s.replace(/;;[^\n]*/g,'').match(/"(?:\\.|[^"\\])*"|[()]|[^\s()]+/g),stack=[],root=[];let current=root;
 for(const t of tokens){if(t==='('){const next=[];current.push(next);stack.push(current);current=next;}
  else if(t===')'){assert(stack.length);current=stack.pop();}else current.push(t);}
 assert.equal(stack.length,0);assert.equal(root.length,1);return root[0];
}
const print=x=>Array.isArray(x)?'('+x.map(print).join(' ')+')':x;
async function* forms(file){
 let depth=0,quoted=false,escaped=false,parts=[];
 for await(const buffer of fs.createReadStream(file,{encoding:'utf8',highWaterMark:1048576})){
  let start=depth>=2?0:-1;
  for(let i=0;i<buffer.length;i++){
   const c=buffer[i];if(quoted){if(escaped)escaped=false;else if(c==='\\')escaped=true;else if(c==='"')quoted=false;continue;}
   if(c==='"'){quoted=true;continue;}
   if(c==='('){if(depth===1)start=i;depth++;}
   if(c===')'){depth--;if(depth===1){parts.push(buffer.slice(start,i+1));yield parts.join('');parts=[];start=-1;}}
  }
  if(start>=0)parts.push(buffer.slice(start));
 }
 assert.equal(depth,0);
}
const sourceRows=new Map(),baselineFiles=kind==='runtime'&&baseline!=='-'?read(baseline+'/bundle-manifest.json').files:[];
let currentFile,templates,currentSources;
const boot=kind==='boot'?new Map(read(source+'/boot/code-set.json').modules.map(m=>[m.name,m])):null;
function input(f){
 const u=units.get(f.unit);
 if(kind==='boot'){
  const m=boot.get(f.source_name);return {wat:m.wat,version:4,template:baseline==='-'?null:fs.readFileSync(baseline+'/boot/artifacts/'+m.name+'.template.wasm')};
 }
 if(currentFile!==u.file){
  const file=read(source+'/bundles.json').files.find(r=>r.path===u.file),prior=baselineFiles.find(r=>r.path===u.file);
  currentFile=u.file;templates=baseline==='-'?null:decodeTargetBundle(fs.readFileSync(baseline+'/'+prior.bundle),prior.sha256).modules;
  currentSources=new Map();let id=0;
  for(const unit of readRecords(source+'/'+file.stem+'.records.json').units){
   const walk=r=>{currentSources.set('code_'+(++id),r);for(const c of r[8]??[])walk(c);};walk(unit.record);
  }
 }
 const r=currentSources.get(f.source_name);return {wat:r[4],version:r[0],template:templates?.get(f.source_name).template??null};
}
const sharedForms=new Map(),declarations=new Map(),cache=new Set();
let body,verified=0,symbolSites=0,codeSites=0,bytes=0;
for await(const text of forms(archiveStem+'.wat')){
 const actual=parse(text),name=actual[1];
 if(actual[0]!=='func'){if(actual[0]==='type'||actual[0]==='import')declarations.set(print(actual),true);continue;}
 if(!name.startsWith('$body__f')&&!name.startsWith('$entry__f')){sharedForms.set(name,actual);continue;}
 if(name.startsWith('$body__f')){body=actual;continue;}
 const index=Number(name.slice('$entry__f'.length)),f=archive.functions[index],u=units.get(f.unit),original=input(f),module=parse(original.wat);
 const helperNames=f.helpers??archive.helper_sets[f.helper_set];
 const helpers=module.filter(x=>Array.isArray(x)&&x[0]==='func'&&typeof x[1]==='string'&&x[1]!=='$body');
 assert.equal(helpers.length,helperNames.length);
 const renames=new Map(helpers.map((x,i)=>[x[1],'$'+helperNames[i]]));renames.set('$body','$body__f'+index);
 const cells=new Map(f.symbols.map(([wire,i])=>[wire,u.shared.find(s=>s[1]===i)?.[2]??u.root_base+i]));
 const codes=new Map(f.codes.map(c=>[c.name,c.code_offset]));
 const isSymbol=x=>Array.isArray(x)&&x.length===2&&x[0]==='global.get'&&x[1].startsWith('$symbol_');
 function inverse(old,now){
  if((original.version>=5&&Array.isArray(old)&&old.length===2&&old[0]==='i32.load'&&isSymbol(old[1]))||
     (original.version===4&&isSymbol(old))){
   const wire=(original.version>=5?old[1][1]:old[1]).slice(8);assert(cells.has(wire));
   assert.deepEqual(now,['i32.load','offset='+4*cells.get(wire),['global.get','$roots']]);symbolSites++;return old;
  }
  if(Array.isArray(old)&&old[0]==='global.get'&&codes.has(old[1]?.slice(6))){
   assert.deepEqual(now,['i32.add',['global.get','$code_base'],['i32.const',String(4*codes.get(old[1].slice(6)))]]);codeSites++;return old;
  }
  if(!Array.isArray(old)){assert.equal(now,renames.get(old)??old);return old;}
  assert(Array.isArray(now));assert.equal(now.length,old.length);
  return now.map((x,i)=>inverse(old[i],x));
 }
 const rebuilt=['module'];let helperIndex=0;
 for(const form of module.slice(1)){
  if(form[0]!=='func'){
   if(form[0]==='type'||(form[0]==='import'&&!['"symbols"','"codes"'].includes(form[1])))assert(declarations.has(print(form)));
   rebuilt.push(form);continue;
  }
  const originalForm=structuredClone(form);let linked;
  if(form[1]==='$body'){
   linked=body;const ix=originalForm.findIndex(x=>Array.isArray(x)&&x[0]==='export');originalForm.splice(ix,1);
   const inverted=inverse(originalForm,linked);inverted.splice(ix,0,form[ix]);rebuilt.push(inverted);
  }else if(Array.isArray(form[1])&&form[1][0]==='export'){
   linked=actual;originalForm[1]=name;
   const inverted=inverse(originalForm,linked);inverted[1]=form[1];rebuilt.push(inverted);
  }else{
   linked=sharedForms.get('$'+helperNames[helperIndex++]);assert(linked);
   // The same original helper and linked variant have the same root mapping;
   // include that map in the key so offset mutations cannot bypass the walk.
   const key=hash(print(form)+print(linked)+JSON.stringify([...cells]));
   if(cache.has(key))rebuilt.push(form);else{rebuilt.push(inverse(form,linked));cache.add(key);}
  }
 }
 const wat=print(rebuilt);fs.writeFileSync(out+'/reconstructed.wat',wat);
 execFileSync('/usr/local/bin/wat2wasm',['--enable-all',out+'/reconstructed.wat','-o',out+'/reconstructed.wasm']);
 const result=fs.readFileSync(out+'/reconstructed.wasm');
 // Changed compiler products have no retained v1 binary. Assemble the
 // original unlinked module independently, then compare exact bytes.
 if(!original.template){
  fs.writeFileSync(out+'/original.wat',original.wat);
  execFileSync('/usr/local/bin/wat2wasm',['--enable-all',out+'/original.wat','-o',out+'/original.wasm']);
  original.template=fs.readFileSync(out+'/original.wasm');
 }
 assert.deepEqual(result,Buffer.from(original.template),'v1 template '+f.name);
 verified++;bytes+=result.length;
 if(verified%500===0)fs.writeFileSync(out+'/progress.json',JSON.stringify({verified,symbolSites,codeSites}));
}
assert.equal(verified,archive.function_count);
const result={status:'PASS',baseline:baseline==='-'?'fresh unlinked compiler WAT':baseline,functions:verified,symbolSites,codeSites,templateBytes:bytes,archive:archive.binary_sha256};
fs.writeFileSync(out+'/result.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
