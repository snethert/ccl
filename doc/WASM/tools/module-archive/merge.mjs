// Prototype archive assembler: merge per-function WAT modules into one module.
// Helpers are deduplicated by content (fixed point over callee variants);
// symbol/code/keyword imports are renamed per function; env.* imports unify.
import fs from 'node:fs';
import {createHash} from 'node:crypto';
const [outWat,kind,...sources]=process.argv.slice(2);
const h=s=>createHash('sha256').update(s).digest('hex').slice(0,10);
function forms(text){ // split "(module ...)" into top-level forms, respecting strings
  let i=text.indexOf('(module')+7,depth=0,start=-1;const out=[];
  for(;i<text.length;i++){const c=text[i];
    if(c==='"'){i++;while(text[i]!=='"'){if(text[i]==='\\')i++;i++;}continue;}
    if(c==='('){if(depth===0)start=i;depth++;}
    else if(c===')'){if(depth===0)break;depth--;if(depth===0)out.push(text.slice(start,i+1));}}
  return out;}
const ident=/^\((\w+)\s+(?:\$([^\s()]+))?/;
const subst=(text,map)=>text.replace(/\$([A-Za-z0-9_.]+)/g,(m,n)=>map.has(n)?'$'+map.get(n):m);
const types=new Map(),fixedImports=new Map(),helpers=new Map(),functions=[],exportsList=[],importsList=[];
let helperRefs=0;
const modules=[];
for(const source of sources){if(kind==='bundle'){const r=JSON.parse(fs.readFileSync(source));const walk=(rec,unit)=>{modules.push({wat:rec[4],name:rec[1]});for(const c of rec[8]||[])walk(c,unit);};for(const u of r.units)walk(u.record,u.name);}
else{for(const m of JSON.parse(fs.readFileSync(source)).modules)modules.push({wat:m.wat,name:m.name});}}
modules.forEach((m,k)=>{const fs_=forms(m.wat),tag='f'+k;const own=new Map(),localHelpers=new Map();let body=null,entry=null;
  for(const f of fs_){const mm=f.match(ident);const head=mm[1],name=mm[2];
    if(head==='type'){if(!types.has(name))types.set(name,f);continue;}
    if(head==='import'){const [,mod,field]=f.match(/^\(import "([^"]+)" "([^"]+)"/);
      if(['symbols','codes','keywords'].includes(mod)){const g=f.match(/\(global \$([^\s()]+)/)[1];own.set(g,g+'__'+tag);
        importsList.push({mod,field:tag+'.'+field});fixedImports.set(mod+'.'+tag+'.'+field,f.replace(`"${field}"`,`"${tag}.${field}"`).replace('$'+g,'$'+g+'__'+tag));}
      else fixedImports.set(mod+'.'+field,f);continue;}
    if(head==='func'){if(name==='body'){body=f;continue;}if(f.includes('(export "entry")')){entry=f;continue;}localHelpers.set(name,f);continue;}
    throw Error('unexpected form '+head);}
  // fixed point over helper variants
  let map=new Map([...localHelpers.keys()].map(n=>[n,n]));
  for(let iter=0;iter<32;iter++){const next=new Map();for(const [n,t] of localHelpers){const t2=subst(t.replace(/^\(func \$[^\s()]+/,'(func'),map);next.set(n,n+'__'+h(t2));}
    let same=true;for(const [n,v] of next)if(map.get(n)!==v)same=false;map=next;if(same)break;}
  const full=new Map([...map,...own,['body','body__'+tag]]);
  for(const [n,t] of localHelpers){const v=map.get(n);if(!helpers.has(v)){helpers.set(v,subst(t.replace(/^\(func \$[^\s()]+/,'(func $'+v),full));}helperRefs++;}
  functions.push(subst(body.replace('(export "tail_entry")',''),full).replace(/^\(func \$body__\w+/,'(func $body__'+tag));
  functions.push(subst(entry.replace('(export "entry")','$entry__'+tag),full));
  exportsList.push(`(export "${tag}.entry" (func $entry__${tag}))`,`(export "${tag}.tail_entry" (func $body__${tag}))`);
});
// Stream the output: a whole-runtime WAT exceeds V8's maximum string length.
const fd=fs.openSync(outWat,'w');let watBytes=0;const emit=t=>{watBytes+=Buffer.byteLength(t)+1;fs.writeSync(fd,t+'\n');};
emit('(module');for(const t of types.values())emit(t);for(const t of fixedImports.values())emit(t);for(const t of helpers.values())emit(t);for(const t of functions)emit(t);for(const t of exportsList)emit(t);emit(')');fs.closeSync(fd);
fs.writeFileSync(outWat+'.imports.json',JSON.stringify(importsList));
console.log(JSON.stringify({functions:modules.length,helperInstancesBefore:helperRefs,distinctHelpers:helpers.size,watBytes,imports:fixedImports.size}));
