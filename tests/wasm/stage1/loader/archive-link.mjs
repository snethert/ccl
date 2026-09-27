// Build-side archive linker. Input: per-function WAT as the compiler
// emits it (bundle records.json units or a boot code-set.json). Output: one WAT
// module per tier plus a manifest. Symbol reads become one load from $roots;
// code imports become $code_base plus an immediate; helpers are shared by text.
import fs from 'node:fs';
import {createHash} from 'node:crypto';
const h=s=>createHash('sha256').update(s).digest('hex');
const need=(v,s)=>{if(!v)throw Error('archive-link: '+s);};
function forms(text){ // top-level forms of "(module ...)", strings respected
  let i=text.indexOf('(module');need(i>=0,'MODULE');i+=7;let depth=0,start=-1;const out=[];
  for(;i<text.length;i++){const c=text[i];
    if(c==='"'){i++;while(text[i]!=='"'){if(text[i]==='\\')i++;i++;}continue;}
    if(c==='('){if(depth===0)start=i;depth++;}
    else if(c===')'){if(depth===0)break;depth--;if(depth===0)out.push(text.slice(start,i+1));}}
  return out;}
const identity=v=>v==null?null:JSON.stringify(v);
const subst=(text,map)=>text.replace(/\$([A-Za-z0-9_.]+)/g,(m,n)=>map.has(n)?'$'+map.get(n):m);
// Runtime (version 5) symbol sites read through a cell; boot (version 4) sites
// are the tagged reference. Both become exactly one load from the root block.
function rewriteSymbols(text,cell){
  text=text.replace(/\(i32\.load \(global\.get \$symbol_([A-Za-z0-9_]+)\)\)/g,(m,w)=>{need(cell.has(w),'SYMBOL '+w);return `(i32.load offset=${4*cell.get(w)} (global.get $roots))`;});
  text=text.replace(/\(global\.get \$symbol_([A-Za-z0-9_]+)\)/g,(m,w)=>{need(cell.has(w),'SYMBOL '+w);return `(i32.load offset=${4*cell.get(w)} (global.get $roots))`;});
  need(!/\$symbol_/.test(text),'SYMBOL_RESIDUE');return text;}
function rewriteCodes(text,offset){ // $code_registry is the env import, not a code import
  text=text.replace(/\(global\.get \$code_([A-Za-z0-9_]+)\)/g,(m,n)=>n==='registry'?m:(need(offset.has(n),'CODE '+n),`(i32.add (global.get $code_base) (i32.const ${4*offset.get(n)}))`));
  need(!/\$code_(?!(registry|base)\b)/.test(text),'CODE_RESIDUE');return text;}
export function link({units,outWat}){
  // units: [{name, symbol_count, functions:[{name, wat, symbols:[[wire,index]], codes:[name], root:boolean}]}]
  const types=new Map(),fixed=new Map(),helpers=new Map(),helperCache=new Map(),helperSets=new Map(),exportsList=[],manifest={version:1,packaging:'code-archive-v2',units:[],functions:[],helpers:[],helper_sets:[]};
  const bodiesPath=outWat+'.bodies',bodyFd=fs.openSync(bodiesPath,'w');
  const emitBody=t=>fs.writeSync(bodyFd,t+'\n');
  const offsetOf=new Map();let k=0;
  for(const u of units)for(const f of u.functions){need(!offsetOf.has(f.name),'DUPLICATE '+f.name);offsetOf.set(f.name,k++);}
  // Symbols read inside helper functions get archive-wide shared cells, so the
  // helper text is identical in every unit and deduplicates; body-only symbols
  // get per-unit cells. Shared cells are filled at first publication and
  // checked for identity afterwards.
  // Sharing is by symbol identity (u.identities[index]: "PKG::NAME" for a
  // symbol, null for any other object), never by wire name: the compiler's
  // bootstrap_N wires are positional. A wire read inside a helper whose entry
  // has no identity keeps a per-unit cell, so that helper stays unit-specific.
  const shared=new Map();
  for(const u of units)for(const f of u.functions){const byWire=new Map(f.symbols);
    for(const form of forms(f.wat)){
    const m=form.match(/^\((\w+)\s+(?:\$([^\s()]+))?/);if(m[1]!=='func'||m[2]==='body'||form.includes('(export "entry")'))continue;
    for(const [,w] of form.matchAll(/\$symbol_([A-Za-z0-9_]+)/g)){const id=identity(u.identities?.[byWire.get(w)]);if(id!=null&&!shared.has(id))shared.set(id,shared.size);}}}
  let rootBase=shared.size;k=0;
  manifest.shared_symbols=[...shared.keys()];
  for(const u of units){
    const unitRow={name:u.name,wire:u.wire??u.name,file:u.file,record_version:u.record_version,record_sha256:u.record_sha256,...(u.references?{references:u.references}:{}),symbol_count:u.symbol_count,root_base:rootBase,functions:[],shared:[]};
    for(let i=0;i<u.symbol_count;i++){const id=identity(u.identities?.[i]);if(id!=null&&shared.has(id))unitRow.shared.push([id,i,shared.get(id)]);}
    for(const f of u.functions){
      const cell=new Map(f.symbols.map(([w,i])=>{need(i<u.symbol_count,'SYMBOL_INDEX');const id=identity(u.identities?.[i]);return [w,id!=null&&shared.has(id)?shared.get(id):rootBase+i];}));
      const fs_=forms(f.wat),tag='f'+k,local=new Map();let body=null,entry=null;
      for(const form of fs_){
        const m=form.match(/^\((\w+)\s+(?:\$([^\s()]+))?/),head=m[1],name=m[2];
        if(head==='type'){if(!types.has(name))types.set(name,form);else need(types.get(name)===form,'TYPE_SHAPE '+name);continue;}
        if(head==='import'){const [,mod,field]=form.match(/^\(import "([^"]+)" "([^"]+)"/);
          need(mod!=='keywords','KEYWORD_IMPORT');if(mod==='symbols'||mod==='codes')continue; // replaced by $roots / $code_base
          if(!fixed.has(mod+'.'+field))fixed.set(mod+'.'+field,form);else need(fixed.get(mod+'.'+field)===form,'IMPORT_SHAPE '+field);continue;}
        if(head==='func'){if(name==='body'){body=form;continue;}if(form.includes('(export "entry")')){entry=form;continue;}local.set(name,form);continue;}
        need(false,'FORM '+head);}
      need(body&&entry,'ENTRIES');
      // A code import names the callee by its compiler wire; the callee's own function name may differ (boot code-set rows).
      const codeOffset=new Map(f.codes.map(c=>{const target=typeof c==='string'?c:c.target;need(offsetOf.has(target),'CODE '+target);return [typeof c==='string'?c:c.name,offsetOf.get(target)];}));
      const rewrite=t=>rewriteCodes(rewriteSymbols(t,cell),codeOffset);
      const rewritten=new Map([...local].map(([n,t])=>[n,rewrite(t)])),key=h([...rewritten.values()].join("\n"));
      let map=helperCache.get(key)??new Map([...local.keys()].map(n=>[n,n]));
      if(!helperCache.has(key))for(let iter=0;iter<32;iter++){const next=new Map();
        for(const [n,t] of rewritten)next.set(n,n+'__'+h(subst(t.replace(/^\(func \$[^\s()]+/,'(func'),map)).slice(0,12));
        let same=true;for(const [n,v] of next)if(map.get(n)!==v)same=false;map=next;if(same)break;}
      helperCache.set(key,map);
      const full=new Map([...map,['body','body__'+tag]]);
      for(const [n,t] of local){const v=map.get(n);const body=subst(rewrite(t).replace(/^\(func \$[^\s()]+/,'(func $'+v),full);if(!helpers.has(v))helpers.set(v,body);else need(helpers.get(v)===body,'HELPER_COLLISION');}
      emitBody(subst(rewrite(body).replace('(export "tail_entry")',''),full).replace(/^\(func \$body__\w+/,'(func $body__'+tag));
      emitBody(subst(rewrite(entry).replace('(export "entry")','$entry__'+tag),full));
      exportsList.push(`(export "${tag}.entry" (func $entry__${tag}))`,`(export "${tag}.tail_entry" (func $body__${tag}))`);
      const helperNames=[...map.values()],helperKey=JSON.stringify(helperNames);
      if(!helperSets.has(helperKey)){helperSets.set(helperKey,helperSets.size);manifest.helper_sets.push(helperNames);}
      manifest.functions.push({name:f.name,source_name:f.source_name??f.name,code_offset:k,unit:u.name,export:tag,arity:f.arity,captures:f.captures,
        symbols:f.symbols,codes:[...codeOffset].map(([name,code_offset])=>({name,code_offset})),helper_set:helperSets.get(helperKey)});
      unitRow.functions.push(k);k++;
    }
    manifest.units.push(unitRow);rootBase+=u.symbol_count;
  }
  manifest.root_cells=rootBase;manifest.function_count=k;manifest.helpers=[...helpers.keys()];
  fixed.set('env.roots','(import "env" "roots" (global $roots i32))');fixed.set('env.code_base','(import "env" "code_base" (global $code_base i32))');
  const fd=fs.openSync(outWat,'w');const emit=t=>fs.writeSync(fd,t+'\n');
  emit('(module');for(const t of types.values())emit(t);for(const t of fixed.values())emit(t);for(const t of helpers.values())emit(t);fs.closeSync(bodyFd);const input=fs.openSync(bodiesPath,'r'),buffer=Buffer.alloc(1048576);let n;while((n=fs.readSync(input,buffer,0,buffer.length,null)))fs.writeSync(fd,buffer,0,n);fs.closeSync(input);fs.unlinkSync(bodiesPath);for(const t of exportsList)emit(t);emit(')');fs.closeSync(fd);
  return manifest;}
export function unitsFromRecords(records,identities={},file='fixture'){
  let ordinal=0;
  return records.units.map(u=>{
    const key=name=>JSON.stringify([file,u.name,name]),functions=[];
    const walk=rec=>{
      need([4,5].includes(rec[0])&&rec[7]===null,'RECORD');
      functions.push({name:key(rec[1]),source_name:'code_'+(++ordinal),arity:rec[2],captures:rec[3],wat:rec[4],symbols:rec[5]??[],
        codes:(rec[6]??[]).map(name=>({name,target:key(name)}))});
      for(const c of rec[8]??[])walk(c);
    };
    walk(u.record);
    return {name:JSON.stringify([file,u.name]),wire:u.name,file,symbol_count:u.symbol_count,functions,
      identities:u.symbol_identities??identities[u.name]??null,
      record_version:(u.install_record??u.record)[0],record_sha256:h(JSON.stringify(u.install_record??u.record))};
  });
}
export function unitsFromCodeSet(codeSet){ // boot code-set.json: each module its own unit; symbols carry addresses
  const byId=new Map(codeSet.modules.map(m=>[m.id,m.name]));
  return codeSet.modules.map(m=>({name:m.name,wire:m.name,record_version:4,record_sha256:h(JSON.stringify([4,m.name])),symbol_count:(m.symbols??[]).length,functions:[{name:m.name,arity:m.arity,captures:m.captures,wat:m.wat,symbols:(m.symbols??[]).map(([w],i)=>[w,i]),codes:(m.codes??[]).map(([n,id])=>({name:n,target:byId.get(id)}))}],
    identities:(m.symbols??[]).map(([,a])=>String(a)),references:(m.symbols??[]).map(([,a])=>a)})); // boot: identity is the image address
}
if(process.argv[1]===new URL(import.meta.url).pathname){
  const [kind,input,outWat,outManifest]=process.argv.slice(2);
  const identityFile=process.argv[6]; // prototype only: fixture-functions.json supplies what records.json will carry
  const identities=identityFile?Object.fromEntries(Object.entries(JSON.parse(fs.readFileSync(identityFile))).map(([u,v])=>[u,v.symbols.map(s=>s&&typeof s==='object'&&!Array.isArray(s)&&s.symbol?s.package+'::'+s.symbol:null)])):{};
  const units=kind==='bundle'?unitsFromRecords(JSON.parse(fs.readFileSync(input)),identities):unitsFromCodeSet(JSON.parse(fs.readFileSync(input)));
  const manifest=link({units,outWat});fs.writeFileSync(outManifest,JSON.stringify(manifest));
  console.log(JSON.stringify({units:manifest.units.length,functions:manifest.function_count,helpers:manifest.helpers.length,root_cells:manifest.root_cells,watBytes:fs.statSync(outWat).size}));
}
