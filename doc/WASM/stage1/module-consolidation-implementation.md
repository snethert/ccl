# Module consolidation — implementation inventory and proposed code

```
DOC-ID   MCP-IMPL-1
AUTHOR   Claude (Fable 5.1), 27 September 2026, at wasm2 c9f259a4 (plan MCP-P7 adopted; review 0a7cd736)
READER   Codex, as Stage 1 author. Everything here is a proposal Codex may adopt, adapt or replace.
STATUS   Stage 1 core (linker + runtime admission) EXECUTED on the retained smoke fixture and linked
         for the misc and boot tiers; every other snippet is UNEXECUTED and marked so.
SCOPE    Only this document. Prose is kept to what a snippet needs.
```

Stages follow the accepted review: **stage 1** archive + generations + root slices
(plan A-1..A-12, A-15 host part), **stage 2** heap/stack sizing and growth (A-14,
timer split), **stage 3** input ownership and release (A-16). Each stage lists the
files that change, then the code.

## Executed evidence (27 September, this machine)

| run | result |
|---|---|
| smoke fixture (`loader-completion/focused-r9`, 16 units, 18 functions) linked into one module | 39 helpers, 219 root cells, 1,062,831 bytes WAT; validates |
| functional check through the archive: ADD-SEVEN, EXTREMA (6 native cases), VALUES (6), ASSQ (7 incl. 2 type errors), ORDINARY/METHOD-KEYS (native match), nested unit, identity re-install, **second generation** with the first generation's closure intact, partial-close release, refusals preserving registry/roots/counter | PASS |
| misc bundle (176 functions) linked | 13 fixed imports only, 352 exports, 1,101,736 bytes; validates |
| boot code set (1,042 functions) linked | 13 fixed imports only, 2,084 exports, 9,901,826 bytes; validates |
| misc linked **without** symbol identities | helpers do not deduplicate (1,293 instead of 39; 19.2 MB WAT): the producer must emit identities (§1.1) |

Not executed: any READY run, collector integration, browser engines, stages 2 and 3.

---

## Stage 1 — one archive per tier, generations, root slices

### Inventory

| # | file | change |
|---|---|---|
| 1.1 | `compiler/WASM32/wasm32-bundle.lisp` | records.json gains per-unit symbol identities (`"PKG::NAME"` or `null`) |
| 1.2 | `tests/wasm/stage1/loader/archive-link.mjs` (new) | build-side linker: per-function WAT → one WAT per tier + manifest (executed) |
| 1.3 | `tests/wasm/stage1/loader/d2.mjs` | one D2 record per archive; entries from the manifest instead of the two fixed exports |
| 1.4 | `tests/wasm/stage1/loader-target/bundles.mjs`, `materialize.mjs` | after compilation: link, `wat2wasm` once, D2 once, write `runtime.archive.wasm/json`; per-file container v2 keeps FASL + unit list only |
| 1.5 | `runtime/wasm32/target-bundle.mjs` | container v2 encode/decode (FASL, unit rows, archive digest); v1 kept |
| 1.6 | `runtime/wasm32/code-archive.mjs` (new) | archive admission, generations, per-unit publication (executed) |
| 1.7 | `runtime/wasm32/collector-owner.mjs` | `reserveRootBlock`, slice registration, `rootCells` skips reserved blocks |
| 1.8 | `runtime/wasm32/target-load-session.mjs` | admit archives at start; reserve at open, publish at opcode 72, release at close |
| 1.9 | `tests/wasm/stage1/loader-target/boot0.mjs` | capacity from manifests; tables/registry preallocated; archive files to the Worker |
| 1.10 | `tests/wasm/stage1/loader/write.mjs`, `runtime/wasm32/cross-image.mjs` | boot tier: link once, reference block, publish all at install |
| 1.11 | `runtime/wasm32/bundle.mjs`, `materializer.mjs` | unchanged for v1; `materializer.install` reused once per archive |
| 1.12 | `tests/wasm/stage1/loader-target/check.mjs` (or new `archive-check.mjs`) | A-8 (b) execution gate on the smoke fixture (executed) |

No shared-compiler file changes in stage 1. `wasm32-root-symbol-reads` stays; the
linker rewrites its output.

### 1.1 Producer: symbol identities per unit (`wasm32-bundle.lisp`) — UNEXECUTED

The linker shares a root cell between units only for entries that are the same
symbol. The wire names (`bootstrap_N`) are positional and cannot carry that.
`compile.lisp` already extracts the per-unit table for fixtures; the same call
belongs in the producer:

```lisp
(defun wasm32-unit-symbol-identities (module)
  ;; One entry per symbol-vector index: "PKG::NAME" for a symbol, NIL otherwise.
  (let ((table (make-array 8 :adjustable t :fill-pointer 0)))
    (wasm32-code-record module table)
    (map 'vector (lambda (x)
                   (if (and x (symbolp x) (symbol-package x))
                       (concatenate 'string (package-name (symbol-package x)) "::" (symbol-name x))
                       nil))
         table)))
;; in wasm32-compile-bundle-records, inside the unit object:
;;   (cons "symbol_identities" (wasm32-unit-symbol-identities module))
```

Uninterned symbols get NIL and keep a per-unit cell. Lists such as
`(satisfies proper-list-p)` get NIL. The linker never trusts identity for
sharing beyond this list, and the loader checks `SHARED_IDENTITY` at publish.

### 1.2 Linker (`archive-link.mjs`) — EXECUTED

Input: `records.json` (+ identities) or the boot `code-set.json`. Output: one
WAT and a manifest. Symbol reads become one load from `$roots`; code imports
become `$code_base + 4*offset`; helpers deduplicate by text after the rewrite.
The prototype takes identities from `fixture-functions.json` (argument 6);
production reads `symbol_identities` from records.json.

```js
// Build-side archive linker (proposal). Input: per-function WAT as the compiler
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
  const types=new Map(),fixed=new Map(),helpers=new Map(),bodies=[],exportsList=[],manifest={version:1,packaging:'code-archive-v2',units:[],functions:[],helpers:[]};
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
    for(const [,w] of form.matchAll(/\$symbol_([A-Za-z0-9_]+)/g)){const id=u.identities?.[byWire.get(w)];if(id!=null&&!shared.has(id))shared.set(id,shared.size);}}}
  let rootBase=shared.size;k=0;
  manifest.shared_symbols=[...shared.keys()];
  for(const u of units){
    const unitRow={name:u.name,symbol_count:u.symbol_count,root_base:rootBase,functions:[],shared:[]};
    for(let i=0;i<u.symbol_count;i++){const id=u.identities?.[i];if(id!=null&&shared.has(id))unitRow.shared.push([id,i,shared.get(id)]);}
    for(const f of u.functions){
      const cell=new Map(f.symbols.map(([w,i])=>{need(i<u.symbol_count,'SYMBOL_INDEX');const id=u.identities?.[i];return [w,id!=null&&shared.has(id)?shared.get(id):rootBase+i];}));
      const fs_=forms(f.wat),tag='f'+k,local=new Map();let body=null,entry=null;
      for(const form of fs_){
        const m=form.match(/^\((\w+)\s+(?:\$([^\s()]+))?/),head=m[1],name=m[2];
        if(head==='type'){if(!types.has(name))types.set(name,form);continue;}
        if(head==='import'){const [,mod,field]=form.match(/^\(import "([^"]+)" "([^"]+)"/);
          need(mod!=='keywords','KEYWORD_IMPORT');if(mod==='symbols'||mod==='codes')continue; // replaced by $roots / $code_base
          if(!fixed.has(mod+'.'+field))fixed.set(mod+'.'+field,form);else need(fixed.get(mod+'.'+field)===form,'IMPORT_SHAPE '+field);continue;}
        if(head==='func'){if(name==='body'){body=form;continue;}if(form.includes('(export "entry")')){entry=form;continue;}local.set(name,form);continue;}
        need(false,'FORM '+head);}
      need(body&&entry,'ENTRIES');
      // A code import names the callee by its compiler wire; the callee's own function name may differ (boot code-set rows).
      const codeOffset=new Map(f.codes.map(c=>{const target=typeof c==='string'?c:c.target;need(offsetOf.has(target),'CODE '+target);return [typeof c==='string'?c:c.name,offsetOf.get(target)];}));
      const rewrite=t=>rewriteCodes(rewriteSymbols(t,cell),codeOffset);
      let map=new Map([...local.keys()].map(n=>[n,n]));
      for(let iter=0;iter<32;iter++){const next=new Map();
        for(const [n,t] of local)next.set(n,n+'__'+h(subst(rewrite(t).replace(/^\(func \$[^\s()]+/,'(func'),map)).slice(0,12));
        let same=true;for(const [n,v] of next)if(map.get(n)!==v)same=false;map=next;if(same)break;}
      const full=new Map([...map,['body','body__'+tag]]);
      for(const [n,t] of local){const v=map.get(n);if(!helpers.has(v))helpers.set(v,subst(rewrite(t).replace(/^\(func \$[^\s()]+/,'(func $'+v),full));}
      bodies.push(subst(rewrite(body).replace('(export "tail_entry")',''),full).replace(/^\(func \$body__\w+/,'(func $body__'+tag));
      bodies.push(subst(rewrite(entry).replace('(export "entry")','$entry__'+tag),full));
      exportsList.push(`(export "${tag}.entry" (func $entry__${tag}))`,`(export "${tag}.tail_entry" (func $body__${tag}))`);
      manifest.functions.push({name:f.name,code_offset:k,unit:u.name,export:tag,symbols:f.symbols,codes:[...codeOffset].map(([name,code_offset])=>({name,code_offset})),helpers:[...map.values()]});
      unitRow.functions.push(k);k++;
    }
    manifest.units.push(unitRow);rootBase+=u.symbol_count;
  }
  manifest.root_cells=rootBase;manifest.function_count=k;manifest.helpers=[...helpers.keys()];
  fixed.set('env.roots','(import "env" "roots" (global $roots i32))');fixed.set('env.code_base','(import "env" "code_base" (global $code_base i32))');
  const fd=fs.openSync(outWat,'w');const emit=t=>fs.writeSync(fd,t+'\n');
  emit('(module');for(const t of types.values())emit(t);for(const t of fixed.values())emit(t);for(const t of helpers.values())emit(t);for(const t of bodies)emit(t);for(const t of exportsList)emit(t);emit(')');fs.closeSync(fd);
  return manifest;}
export function unitsFromRecords(records,identities={}){ // bundle records.json: nested lambdas are children; identities[unit] from the producer
  return records.units.map(u=>{const functions=[];const walk=rec=>{functions.push({name:rec[1],wat:rec[4],symbols:rec[5]??[],codes:rec[6]??[]});need(rec[7]===null,'KEYWORDS');for(const c of rec[8]??[])walk(c);};walk(u.record);return {name:u.name,symbol_count:u.symbol_count,functions,identities:identities[u.name]??null};});}
export function unitsFromCodeSet(codeSet){ // boot code-set.json: each module its own unit; symbols carry addresses
  const byId=new Map(codeSet.modules.map(m=>[m.id,m.name]));
  return codeSet.modules.map(m=>({name:m.name,symbol_count:(m.symbols??[]).length,functions:[{name:m.name,wat:m.wat,symbols:(m.symbols??[]).map(([w],i)=>[w,i]),codes:(m.codes??[]).map(([n,id])=>({name:n,target:byId.get(id)}))}],
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
```

Manifest rows: `units[{name, symbol_count, root_base, functions[], shared[[identity,index,cell]]}]`,
`functions[{name, code_offset, unit, export, symbols, codes, helpers}]`,
`shared_symbols`, `root_cells`, `function_count`, `helpers`. Production adds
`binary_sha256`, `template_sha256`, the one D2 record, and per unit
`record_version`/`record_sha256` (from `install_record`), which is what
`code-archive.mjs` checks.

Boot tier option: pass every identity (address) as shareable (`shareAll`) so the
15,564 per-module cells collapse to the distinct references (about 1,700);
values are pinned image addresses and identical across units, so
`SHARED_IDENTITY` holds.

### 1.3 D2 once per archive (`d2.mjs`) — UNEXECUTED

`inventory()` already classifies from `wasm-objdump` and derives the template
and full binaries; only the entry list assumes two exports. Replace the last
statement with a manifest-driven list and stream the listing:

```js
export function inventoryArchive(wat,stem,policy,versions,manifest){
 fs.writeFileSync(stem+'.wat',wat);
 execFileSync('/usr/local/bin/wat2wasm',['--enable-all',stem+'.wat','-o',stem+'.template.wasm']);
 const bytes=fs.readFileSync(stem+'.template.wasm');
 // Stream -d through the feature scan; retain only -x and the digests (A-6).
 const sections=execFileSync('/usr/local/bin/wasm-objdump',['-x',stem+'.template.wasm'],{encoding:'utf8',maxBuffer:256*1024*1024});
 const ops=new Set();let dHash=createHash('sha256');
 const dump=spawnSync('/usr/local/bin/wasm-objdump',['-d',stem+'.template.wasm'],{maxBuffer:4*1024*1024*1024});
 for(const line of dump.stdout.toString().split('\n')){dHash.update(line+'\n');const m=line.split('|')[1]?.trim();if(m)ops.add(m.split(/\s+/)[0]);}
 const features=featuresFrom(ops,sections),classification={binary_sha256:sha256(bytes),features,wait:[...ops].some(o=>o.startsWith('memory.atomic.wait')||o==='memory.atomic.notify'),legacy:[...ops].some(o=>['try','catch','catch_all','delegate','rethrow'].includes(o)),instruction_mnemonics:[...ops].sort(),sections_sha256:sha256(sections),instructions_sha256:dHash.digest('hex')};
 const x=inspect(bytes,{ownerRetry:true}),abi={minimum:1,maximum:32769,imports:x.imports,exports:x.exports.map(e=>({name:e.name,kind:e.kind,index:e.index,signature:x.types[x.functions[e.index]]}))};
 const template=manifest(bytes,abi,classification,policy),full=materialize(bytes,template,abi,classification,policy,'full');
 fs.writeFileSync(stem+'.wasm',full.bytes);
 const ranges=entryRanges(full.bytes,{ownerRetry:true}),byName=new Map(ranges.map(r=>[r.role,r]));
 return {generation:1,...versions,profile:FLOAT_PROFILE,d2:{abi,classification,template,outputs:{full:full.record}},
  binary_sha256:full.record.binary_sha256,template_sha256:template.template_sha256,
  entries:manifest.functions.map(f=>({code_offset:f.code_offset,
   entry:{index:x.exports.find(e=>e.name===f.export+'.entry').index,range:byName.get(f.export+'.entry')},
   tail_entry:{index:x.exports.find(e=>e.name===f.export+'.tail_entry').index,range:byName.get(f.export+'.tail_entry')},
   body_sha256:sha256(Buffer.concat([full.bytes.subarray(byName.get(f.export+'.entry').start,byName.get(f.export+'.entry').end),full.bytes.subarray(byName.get(f.export+'.tail_entry').start,byName.get(f.export+'.tail_entry').end)]))}))};
}
```

`entryRanges` already maps every export, so it needs no change. `inspect` needs
`ownerRetry:true` because the archive always imports the three services.

### 1.4 Build pipeline (`bundles.mjs`) — UNEXECUTED

After the per-file compile loop (records + FASL per file unchanged):

```js
// One archive for the tier. Units keep file order; the manifest records it.
const units=manifest.files.flatMap(file=>{const records=read(file.stem+'.records.json');
  return unitsFromRecords(records,Object.fromEntries(records.units.map(u=>[u.name,u.symbol_identities])))
    .map(u=>({...u,file:file.path}));});
const archiveManifest=link({units,outWat:out+'/runtime.archive.wat'});
Object.assign(archiveManifest,inventoryArchive(fs.readFileSync(out+'/runtime.archive.wat','utf8'),out+'/runtime.archive',policy,versions,archiveManifest));
for(const u of archiveManifest.units){const file=manifest.files.find(f=>f.path===u.file),r=read(file.stem+'.records.json').units.find(x=>x.name===u.name);
  const d=r.install_record??r.record;u.record_version=d[0];u.record_sha256=sha256(JSON.stringify(d));}
fs.writeFileSync(out+'/runtime.archive.json',JSON.stringify(archiveManifest));
manifest.archive={file:'runtime.archive.wasm',sha256:archiveManifest.binary_sha256,manifest:'runtime.archive.json'};
for(const file of manifest.files){ // container v2: FASL + unit names, no code
  const bytes=encodeTargetContainer({units:archiveManifest.units.filter(u=>u.file===file.path).map(u=>u.name),
    archive_sha256:archiveManifest.binary_sha256,fasl:fs.readFileSync(out+'/'+file.stem+'.w32fsl')});
  file.bundle=file.stem+'.w32bundle';file.sha256=sha256(bytes);fs.writeFileSync(out+'/'+file.bundle,bytes);}
```

`--reuse` keeps working at the WAT level: identical per-function WAT means an
identical archive input; the archive itself is rebuilt whenever any input
changed (one `wat2wasm`, 24 s / 5 GB for the whole runtime, F-8).

### 1.5 Container v2 (`target-bundle.mjs`) — UNEXECUTED

```js
const MAGIC2=0x42323357,VERSION2=2;
export function encodeTargetContainer({units,archive_sha256,fasl}){
  const data=snapshotBytes(fasl),manifest=utf8(JSON.stringify({version:VERSION2,archive_sha256,units,fasl_sha256:sha256(data)}));
  const output=new Uint8Array(HEADER+manifest.length+data.length),view=new DataView(output.buffer);
  [MAGIC2,VERSION2,manifest.length,data.length].forEach((n,i)=>view.setUint32(i*4,n,true));
  output.set(manifest,HEADER);output.set(data,HEADER+manifest.length);return output;}
export function decodeTargetContainer(input,digest){
  const bytes=snapshotBytes(input);need(sha256(bytes)===digest,'DIGEST');const view=new DataView(bytes.buffer);
  need(view.getUint32(0,true)===MAGIC2&&view.getUint32(4,true)===VERSION2,'VERSION');
  const m=view.getUint32(8,true),d=view.getUint32(12,true);need(HEADER+m+d===bytes.length,'TRAILING_BYTES');
  const manifest=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes.subarray(HEADER,HEADER+m)));
  need(manifest.version===VERSION2&&/^[0-9a-f]{64}$/.test(manifest.archive_sha256)&&Array.isArray(manifest.units),'MANIFEST');
  const fasl=bytes.slice(HEADER+m);need(sha256(fasl)===manifest.fasl_sha256,'FASL_DIGEST');
  return {manifest,fasl};}
```

`decodeTargetBundle` (v1) stays for post-image files.

### 1.6 Runtime admission (`code-archive.mjs`) — EXECUTED

```js
// Runtime-side archive admission (proposal): one compiled module per tier,
// generations, per-unit publication at opcode 72. Mirrors bundle.mjs/
// target-bundle.mjs checks where the v1 loader has them.
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
const need=(ok,why)=>{if(!ok)throw Error('code archive: '+why);};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const uint=n=>Number.isSafeInteger(n)&&n>=0&&n<=0xffffffff;
export const PACKAGING='code-archive-v2';
export function admitCodeArchive({bytes,manifest,digest,env,capabilities={},slotOffset,allocateCode,reserveRoots,registerRoots}){
  need(sha256(bytes)===digest,'DIGEST');
  need(manifest.version===1&&manifest.packaging===PACKAGING&&manifest.binary_sha256===digest,'MANIFEST');
  need(env.table!==env.tail_table,'DISTINCT_TABLES');
  const count=manifest.function_count,units=new Map(manifest.units.map(u=>[u.name,u]));
  need(manifest.functions.length===count&&manifest.functions.every((f,i)=>f.code_offset===i),'FUNCTIONS');
  const module=new WebAssembly.Module(bytes); // validate/inspect as bundle.mjs does, once; the caller may drop `bytes` now
  bytes=null;
  const ex=new Set(WebAssembly.Module.exports(module).map(e=>e.name));
  for(const f of manifest.functions)need(ex.has(f.export+'.entry')&&ex.has(f.export+'.tail_entry'),'EXPORT '+f.name);
  const view=()=>new DataView(env.memory.buffer),get=p=>view().getUint32(p,true),put=(p,v)=>view().setUint32(p,v,true);
  const registry=env.code_registry,capacity=get(registry);need(get(registry+4)===1,'REGISTRY');
  const generations=[];const states=new Map(); // unit name -> [{generation, state:'unreserved'|'reserved'|'published', session, roots, codes}]
  function createGeneration(){
    const journal=[];
    try{
      const codeBase=allocateCode(count,journal);            // consumes the whole window now (A-4)
      need(codeBase+count<=capacity&&codeBase+count+slotOffset<=env.table.length&&codeBase+count+slotOffset<=env.tail_table.length,'CAPACITY');
      const roots=reserveRoots(manifest.root_cells,journal);  // whole block, NIL-filled, unregistered (A-12)
      const imports={env:{...env,roots:roots.base,code_base:codeBase*4},
        ...Object.fromEntries(['owner','integer','floating'].filter(n=>capabilities[n]).map(n=>[n,{...capabilities[n]}]))};
      const instance=new WebAssembly.Instance(module,imports);
      const g={index:generations.length,codeBase,roots,instance,units:new Map()};
      generations.push(g);return g;
    }catch(e){for(let i=journal.length-1;i>=0;i--)journal[i]();throw e;}
  }
  const unitState=(g,name)=>g.units.get(name)??{state:'unreserved'};
  return Object.freeze({
    manifest,generations:()=>generations.length,
    // LOAD open: reserve the file's units in the oldest generation where they are unreserved (A-4)
    reserve(session,unitNames){
      for(const name of unitNames)need(units.has(name),'UNIT '+name);
      let g=generations.find(g=>unitNames.every(n=>unitState(g,n).state==='unreserved'));
      if(!g)g=createGeneration();
      for(const name of unitNames)g.units.set(name,{state:'reserved',session});
      return g;
    },
    release(session){ // LOAD close: reserved-but-unpublished units return to unreserved; published stay
      for(const g of generations)for(const [name,u] of g.units)if(u.state==='reserved'&&u.session===session)g.units.delete(name);
    },
    // opcode 72: publish one unit from the generation that holds its reservation
    install(session,name,record,symbolValues){
      const unit=units.get(name);need(unit,'CODE_RECORD');
      need(sha256(JSON.stringify(record))===unit.record_sha256,'CODE_RECORD');
      need(Array.isArray(symbolValues)&&symbolValues.length===unit.symbol_count&&symbolValues.every(uint),'SYMBOL_COUNT');
      const g=generations.find(g=>['reserved','published'].includes(unitState(g,name).state)&&unitState(g,name).session===session);
      need(g,'UNRESERVED_UNIT');
      const u=g.units.get(name),cells=Array.from({length:unit.symbol_count},(_,i)=>g.roots.base+4*(unit.root_base+i));
      if(u.state==='published'){need(same(cells.map(get),symbolValues),'IMPORT_IDENTITY');return g.codeBase+unit.functions[0];}
      const NIL=77825,sharedWrites=[];
      for(const [,index,cell] of unit.shared??[]){const p=g.roots.base+4*cell,value=symbolValues[index];
        if(get(p)===NIL&&!g.sharedFilled?.has(cell))sharedWrites.push([p,value,cell]);else need(get(p)===value,'SHARED_IDENTITY');}
      const journal=[];const write=(p,v)=>{const old=get(p);journal.push(()=>put(p,old));put(p,v);};
      try{
        for(const id of unit.functions){const code=g.codeBase+id,slot=code+slotOffset,p=registry+8+16*code;
          need([0,4,8,12].every(o=>get(p+o)===0)&&env.table.get(slot)===null&&env.tail_table.get(slot)===null,'SLOT_OCCUPIED');}
        cells.forEach((p,i)=>write(p,symbolValues[i]));
        g.sharedFilled??=new Set();
        for(const [p,value,cell] of sharedWrites){write(p,value);g.sharedFilled.add(cell);journal.push(()=>g.sharedFilled.delete(cell));}
        registerRoots(g.roots,[...cells,...sharedWrites.map(([p])=>p)],journal); // only published slices are roots (A-15)
        for(const id of unit.functions){const code=g.codeBase+id,slot=code+slotOffset,p=registry+8+16*code,f=manifest.functions[id];
          [slot,4,17,23].forEach((w,i)=>write(p+4*i,w));
          const entry=g.instance.exports[f.export+'.entry'],tail=g.instance.exports[f.export+'.tail_entry'];
          env.table.set(slot,entry);env.tail_table.set(slot,tail);journal.push(()=>{env.table.set(slot,null);env.tail_table.set(slot,null);});}
        u.state='published';return g.codeBase+unit.functions[0];
      }catch(e){for(let i=journal.length-1;i>=0;i--)journal[i]();throw e;}
    }
  });
}
```

Production additions at the top of `admitCodeArchive`, before `new WebAssembly.Module`:
`validate` once (`loader.mjs` style: fixed imports exactly the 13 the archive
declares, `IMPORT_MANIFEST`, `EXPORT_SET` = 2 × function_count), `materializer.install`
once (template + patched full binary, the one D2 record), and
`entryRanges`/`body_sha256` per row against `manifest.entries`. The
`SHARED_IDENTITY` refusal is the runtime guard for §1.1.

### 1.7 Collector owner (`collector-owner.mjs`) — UNEXECUTED

Reserve a block once per generation (no per-cell scan), register per unit,
and make the v1 path skip reserved blocks so v1 and v2 coexist.

```js
 #blocks=[]; // reserved root blocks, whether or not any slice is registered
 #inReservedBlock(p){return this.#blocks.some(b=>p>=b.start&&p<b.end);}
 reserveRootBlock(count){
  this.#requireBoundary();need(Number.isInteger(count)&&count>0,'root block count');
  const region=this.#region('external'),list=this.#region('root-list');
  let start=region.start;
  for(const b of this.#blocks)start=Math.max(start,b.end);
  for(const g of this.#layout.groups)for(const p of g.slots)if(p>=start)start=p+4;
  const end=start+4*count;need(end<=region.end,'root capacity');
  const live=this.#validate().slots.length; // charged whole, as A-12 requires
  need(live+count<=this.#layout.logCapacity&&(live+count)*4<=list.end-list.start,'root capacity');
  for(let p=start;p<end;p+=4)this.#set(p,NIL);
  const block={start,end,registered:new Set()};this.#blocks.push(block);
  const group=()=>this.#layout.groups.find(g=>g.kind==='module-constants');
  return Object.freeze({base:start,count,
   register:cells=>{this.#requireBoundary();
    for(const p of cells)need(p>=start&&p<end&&p%4===0&&!block.registered.has(p),'root slice');
    for(const p of cells){block.registered.add(p);group().slots.push(p);}},
   unregister:cells=>{this.#requireBoundary();const set=new Set(cells);
    for(const p of cells)need(block.registered.has(p),'root slice');
    for(const p of cells){block.registered.delete(p);this.#set(p,NIL);}
    group().slots=group().slots.filter(p=>!set.has(p));},
   release:()=>{this.#requireBoundary();need(block.registered.size===0,'released roots');
    this.#blocks.splice(this.#blocks.indexOf(block),1);}});
 }
 // rootCells (v1): one added condition so it never allocates inside a reserved block.
 //   for(let p=region.start;p<region.end&&slots.length<values.length;p+=4)if(!used.has(p)&&!this.#inReservedBlock(p))slots.push(p);
```

`#admit` and `storage` need no change; `registeredRootCells` keeps counting
registered slices only. Per-collection listing of individual cells is
unchanged in stage 1 (stage 2 splits its timer; a C range path is a later
decision).

### 1.8 Load session (`target-load-session.mjs`) — UNEXECUTED

```js
export function targetLoadSession({files, archives=[], memory, env, owner, versions, policy, capabilities,
  nextCode, nextSlot, slotOffset=nextSlot-nextCode, post, pinned, onOpen=()=>{}, onClose=()=>{}, onInstall=()=>{},
  measure=(_p,run)=>run(), onAdmission=()=>{}}) {
  const source=bundleNamespace({files,measure}),paths=source.session(),open=new Map();
  // v2 archives: admitted once, before any Lisp runs (A-5). One generation now.
  const admitted=new Map();
  for(const a of archives){
    const session=admitCodeArchive({bytes:a.bytes,manifest:a.manifest,digest:a.digest,env,capabilities,slotOffset,
      allocateCode:(n,journal)=>{const base=nextCode;nextCode+=n;journal.push(()=>{nextCode=base;});return base;},
      reserveRoots:(n,journal)=>{const block=owner.atSafepoint(o=>o.reserveRootBlock(n));journal.push(()=>owner.atSafepoint(()=>block.release()));return block;},
      registerRoots:(block,cells,journal)=>{owner.atSafepoint(()=>block.register(cells));journal.push(()=>owner.atSafepoint(()=>block.unregister(cells)));}});
    admitted.set(a.digest,session);onAdmission(a.digest);
  }
  ... // file(args) op 0, after the v1 branch:
      const container=source.containers.get(path); // {archive_sha256, units}
      if(container&&get(args+8)===0){
        const archive=admitted.get(container.archive_sha256);need(archive,'ARCHIVE_ABSENT');
        const token=Symbol(path);archive.reserve(token,container.units);   // A-4: reserve at open
        pending={path,token,archive,install:targetCodeService({memory,session:{
          install:(name,record,symbols)=>archive.install(token,name,record,symbols)}})};
      }
      const result=client(args),value=result>>2;
      if(op===0&&pending?.archive&&value<0)pending.archive.release(pending.token); // open failed
      ...
      if(op===3&&value>=0){const prior=open.get(fd);open.delete(fd);if(prior){prior.archive?.release(prior.token);onClose(prior.path,fd);}}
```

`targetCodeService` is unchanged: it decodes the record and symbol vector and
calls `session.install(record[1], record, symbols)`. `%WASM-HOST-INSTALL-CODE`
still returns `code_id*4`. Root cells are filled inside `archive.install`
under the owner boundary the `registerRoots` hook takes; the value writes
themselves happen in `code-archive.mjs` before registration, which is the
order A-12 specifies (fill, register, rows, tables), all journaled.

### 1.9 Boot driver (`boot0.mjs`) — UNEXECUTED

```js
// main thread: archives are separate files named in bundle-manifest.json
const archives=bundleDirs.flatMap(dir=>{const m=JSON.parse(fs.readFileSync(dir+'/bundle-manifest.json'));
  if(!m.archive)return [];return [{digest:m.archive.sha256,bytes:new Uint8Array(fs.readFileSync(dir+'/'+m.archive.file)),
    manifest:JSON.parse(fs.readFileSync(dir+'/'+m.archive.manifest))}];});
// Worker: capacity from manifests (A-4); tables at full size before any generation (A-12)
const G=Number(workerData.generations??2),slotOffset=8,budget=8192;
const rows=16+codeSet.modules.length+G*archives.reduce((n,a)=>n+a.manifest.function_count,0)+budget;  // 31,032 for G=2
const capacity=rows+slotOffset;
assert(registry+8+16*rows<=external,'registry region');
const memory=new WebAssembly.Memory({initial:448,maximum:32769,shared:true});
env.table=new WebAssembly.Table({element:'anyfunc',initial:capacity});env.tail_table=new WebAssembly.Table({element:'anyfunc',initial:capacity});
put(registry,rows);put(registry+4,1);
const loader=targetLoadSession({files:workerData.files,archives:workerData.archives,memory,env,owner,versions,policy,capabilities,pinned,
  nextCode:Math.max(...codeSet.modules.map(m=>m.code_id))+1,nextSlot:Math.max(...Object.values(expected.slots))+1,...});
```

The external region (1 MiB at boot0) holds 262,144 cells; one runtime
generation needs 125,199 (or fewer with shared cells). `G=2` requires the
region to grow to at least 2 × 125,199 × 4 + boot cells; derive it from the
manifests in the same place (stage 2's layout builder does this generally).

### 1.10 Boot tier (`write.mjs`, `cross-image.mjs`) — UNEXECUTED

```js
// write.mjs: replace the per-module inventory loop
const units=unitsFromCodeSet(codeSet);      // identity = image address (see the shareAll option in §1.2)
const archiveManifest=link({units,outWat:path.join(out,'boot.archive.wat')});
Object.assign(archiveManifest,inventoryArchive(fs.readFileSync(path.join(out,'boot.archive.wat'),'utf8'),path.join(out,'boot.archive'),policy,versions,archiveManifest));
for(const u of archiveManifest.units)u.references=units.find(x=>x.name===u.name).references.map(reference); // heap/static references, no host address
const bundle={version:1,packaging:'code-archive-v2',...versions,first_code_id:codeSet['first-code-id'],archive:archiveManifest};
// cross-image.mjs: admit(): one generation, roots filled from references, everything published in install()
const roots=owner.reserveRootBlock(set.archive.root_cells);
for(const u of set.archive.units)u.references.forEach((ref,i)=>put(roots.base+4*(u.root_base+i),heap.reference(ref)));
for(const [identity,cell] of sharedCells(set.archive))put(roots.base+4*cell,heap.reference(identity)); // shared cells hold the same reference
const instance=new WebAssembly.Instance(module,{env:{...env,roots:roots.base,code_base:set.first_code_id*4},...capabilities});
// install(): registry rows and paired tables for every function, then heap.install(), with the v1 rollback shape
```

Boot never reloads, so it has exactly one generation and `nextCode` starts at
`first_code_id + function_count`.

### 1.12 Gates for stage 1 (scripts to add)

- A-8 (a): for each function, rebuild the v1 module text from the archive
  pieces with renames inverted and compare `wat2wasm` output to the retained
  `code_N.template.wasm` byte for byte. The linker's `manifest.functions[].helpers`
  lists the helper variants each function used, in original order.
- A-8 (b): independent scan of v1 and archive text: every
  `(i32.load (global.get $symbol_w))` / `(global.get $symbol_w)` site ↔ one
  `(i32.load offset=4*cell (global.get $roots))` site with `cell` from the
  manifest; every `(global.get $code_n)` ↔ `(i32.add (global.get $code_base) (i32.const 4*off))`.
- Execution: `archive-check.mjs` below on the smoke fixture (executed), then
  READY via `boot0.mjs` with both archives, the two post-image loads, the two
  refusals, `--trace` census equality against P-0's `execution`.
- A-4/A-12: the second-generation, partial-close and refusal cases below;
  add a forced collection between root fill and first call under the real owner.

```js
// Functional check of the archive path on the retained smoke fixture: mirrors
// tests/wasm/stage1/loader-target/check.mjs cases, plus a second generation.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
import {admitCodeArchive} from './code-archive.mjs';
const out=process.argv[2],arch=process.argv[3],read=n=>JSON.parse(fs.readFileSync(out+'/'+n));
const bytes=fs.readFileSync(arch+'/smoke.wasm'),manifest=JSON.parse(fs.readFileSync(arch+'/smoke.manifest.json'));
manifest.binary_sha256=sha256(bytes);
const records=read('records.json'),functions=read('fixture-functions.json'),pools=read('fixture-pools.json');
for(const u of manifest.units){const r=records.units.find(x=>x.name===u.name);u.record_sha256=sha256(JSON.stringify(r.install_record??r.record));}
const N=77825,T=77838,tcr=1024,registry=4096,root=131064;
const memory=new WebAssembly.Memory({initial:64,maximum:32769,shared:false});
const view=new DataView(memory.buffer),get=p=>view.getUint32(p,true),put=(p,n)=>view.setUint32(p,n,true);
const env={memory,tcr,code_registry:registry,table:new WebAssembly.Table({element:'anyfunc',initial:256}),tail_table:new WebAssembly.Table({element:'anyfunc',initial:256}),
  call_error:new WebAssembly.Tag({parameters:['i32']}),type_error:new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit:new WebAssembly.Tag({parameters:['i32']})};
put(registry,256);put(registry+4,1);
const unexpected=()=>{throw Error('unexpected service');};
let nextCode=16,nextRoot=524288;const registered=new Set();
const session=admitCodeArchive({bytes,manifest,digest:manifest.binary_sha256,env,slotOffset:8,
  capabilities:{owner:{ensure:unexpected},integer:{calculate:unexpected},floating:{calculate:unexpected}},
  allocateCode:(n,journal)=>{const base=nextCode;nextCode+=n;journal.push(()=>{nextCode=base;});return base;},
  reserveRoots:(n,journal)=>{const base=nextRoot;nextRoot+=4*n;for(let i=0;i<n;i++)put(base+4*i,N);journal.push(()=>{nextRoot=base;});return {base,count:n};},
  registerRoots:(roots,cells,journal)=>{cells.forEach(p=>{assert(p>=roots.base&&p<roots.base+4*roots.count);registered.add(p);});journal.push(()=>cells.forEach(p=>registered.delete(p)));}});
const unitOf=name=>manifest.units.find(u=>functions[u.name].name?.symbol===name);
const record=u=>{const r=records.units.find(x=>x.name===u.name);return r.install_record??r.record;};
let next=1048576;const allocate=n=>{const p=next;next+=Math.ceil(n/8)*8;return p;};const literal=new Map();
function encode(v,vector=false){
  if(v===null)return N;if(v===true)return T;if(Number.isInteger(v))return (v*4)>>>0;
  if(Number.isInteger(v.character))return v.character*256+75;if(v.vector)return encode(v.vector,true);
  if(v.symbol){const k=JSON.stringify([v.package,v.symbol]);if(!literal.has(k)){const p=allocate(32),name=encode(v.symbol);[1850,name,N,N,N,0,N,0].forEach((x,i)=>put(p+4*i,x));literal.set(k,p+6);}return literal.get(k);}
  if(typeof v==='string'){const cs=Array.from(v),p=allocate(4+cs.length*4);put(p,cs.length*256+191);cs.forEach((c,i)=>put(p+4+i*4,c.codePointAt(0)));return p+6;}
  assert(Array.isArray(v));if(vector||v.length===0){const p=allocate(4+v.length*4);put(p,v.length*256+250);v.forEach((x,i)=>put(p+4+i*4,encode(x)));return p+6;}
  let tail=N;for(let i=v.length-1;i>=0;i--){const p=allocate(8);put(p,tail);put(p+4,encode(v[i]));tail=p+1;}return tail;}
const debug=encode([1,null,[]],true);
for(const [o,v] of [[48,3145728],[52,3211264],[56,3145728],[64,root+8],[68,root+8],[72,root+32776],[76,196608],[80,196608],[84,212992],[88,212992],[92,212992],[96,229376],[104,262144],[108,0],[116,0],[120,root+8200],[124,root+8264],[128,root],[188,N]])put(tcr+o,v);
put(root,0);put(root+4,1);put(root+8,35*4);
const LOAD='load-1';
function install(name,symbolsOverride){
  const u=unitOf(name),meta=functions[u.name];
  const imports=symbolsOverride??meta.symbols.map(s=>encode(s));
  for(const i of record(u)[9]??[])put(imports[i]+22,4*(i+1));
  const code=session.install(LOAD,u.name,record(u),imports);
  const arity=encode(meta.arity,true);put(arity-2+6*4,encode(meta.arity[6],true));
  const pool=encode([null,null,0x574153,0,[],null,...pools[u.name]],true);put(pool-2,arity);put(pool+2,debug);
  const fn=allocate(32);[1578,code*4,N,4,arity,debug,pool,0].forEach((v,i)=>put(fn+i*4,v));
  const slot=get(registry+8+16*code);
  const call=args=>{call.words=args.map(v=>encode(v));return call.raw(call.words);};
  call.raw=words=>{words.forEach((v,i)=>put(root+8+4*i,v));return env.table.get(slot)(fn+6,words.length);};
  call.code=code;call.fn=fn+6;call.imports=imports;return call;}
session.reserve(LOAD,manifest.units.map(u=>u.name));
const checked=(f,args)=>{try{return f(args);}catch(e){if(e.is?.(env.call_error))throw Error('checked '+e.getArg(env.call_error,0));if(e.is?.(env.type_error)){const d=e.getArg(env.type_error,0);const lit=[...literal].find(([k,v])=>v===d);const el=i=>{const w=get(d-2+4*i);const l=[...literal].find(([k,v])=>v===w);return l?l[0]:w%8===6?'obj:'+get(w-6).toString(16):w;};throw Error('type_error '+d+' '+e.getArg(env.type_error,1)+' header='+(d%8===6?get(d-6).toString(16):'-')+' elements='+el(0)+','+el(1)+' allocNext='+next);}if(e.is?.(env.nonlocal_exit))throw Error('nonlocal_exit '+e.getArg(env.nonlocal_exit,0));throw e;}};
const addSeven=install('TARGET-LOADER-ADD-SEVEN');
assert.deepEqual(checked(addSeven,[35]),[42*4,1]);
const extrema=install('TARGET-LOADER-EXTREMA');
for(const [args,expected] of read('extrema-native.json')){const [first,count]=checked(extrema,args);assert.equal(count,expected.length);assert.equal(first>>2,expected[0]);assert.deepEqual(expected.map((_,i)=>get(root+8200+4*i)>>2),expected);}
const values=install('TARGET-LOADER-VALUES');put(tcr+124,root+8328);
for(const [input,result] of read('values-native.json')){const args=input??[],expected=result??[];const [first,count]=checked(values,args);assert.equal(count,expected.length);const words=expected.map(x=>x===null?N:x*4);assert.equal(first,words[0]??N);}
put(tcr+124,root+8264);
const assq=install('TARGET-LOADER-ASSQ');let assqCases=0;
for(const [args,expected] of read('assq-native.json')){if(expected==='TYPE-ERROR'){assert.throws(()=>assq(args),e=>e.is?.(env.type_error));}else{const [value,count]=checked(assq,args);assert.equal(count,1);let cursor=assq.words[1],found=N;while(cursor!==N){const pair=get(cursor+3);if(pair!==N&&get(pair+3)===assq.words[0]){found=pair;break;}cursor=get(cursor-1);}assert.equal(value,found);}assqCases++;}
const ordinaryKeys=install('TARGET-LOADER-ORDINARY-KEYS'),methodKeys=install('TARGET-LOADER-METHOD-KEYS');
const amount={package:'KEYWORD',symbol:'AMOUNT'},other={package:'KEYWORD',symbol:'OTHER'};
const keywordResults=[checked(ordinaryKeys,[40,amount,2])[0]>>2,checked(methodKeys,[null,40,amount,2,other,9])[0]>>2,checked(methodKeys,[null,40,other,9])[0]>>2];
assert.throws(()=>ordinaryKeys([40,other,9]),e=>e.is?.(env.call_error));keywordResults.push(true);
assert.deepEqual(keywordResults,read('keyword-native.json'));
const nested=manifest.units.find(u=>u.functions.length>1);assert(nested,'nested unit');
const nestedCode=session.install(LOAD,nested.name,record(nested),functions[nested.name].symbols.map(s=>encode(s)));
for(const id of nested.functions){const code=16+id;assert.equal(get(registry+8+16*code),code+8);assert.equal(typeof env.table.get(code+8),'function');}
// Same unit, same values, same session: identity, same code id.
assert.equal(session.install(LOAD,unitOf('TARGET-LOADER-ADD-SEVEN').name,record(unitOf('TARGET-LOADER-ADD-SEVEN')),addSeven.imports),addSeven.code);
assert.throws(()=>session.install(LOAD,unitOf('TARGET-LOADER-ADD-SEVEN').name,record(unitOf('TARGET-LOADER-ADD-SEVEN')),addSeven.imports.map((v,i)=>i===0?N:v)),/IMPORT_IDENTITY/);
// A second LOAD of the same file: reservation lands in a fresh generation; new ids; old closure intact.
const LOAD2='load-2';const g2=session.reserve(LOAD2,manifest.units.map(u=>u.name));assert.equal(session.generations(),2);
const u=unitOf('TARGET-LOADER-ADD-SEVEN');const code2=session.install(LOAD2,u.name,record(u),functions[u.name].symbols.map(s=>encode(s)));
assert.notEqual(code2,addSeven.code);assert.equal(code2,g2.codeBase+u.functions[0]);
assert.deepEqual(checked(addSeven,[1]),[8*4,1]);
const fn2=allocate(32);const arity=encode(functions[u.name].arity,true);put(arity-2+24,encode([],true));const pool=encode([null,null,0x574153,0,[],null,...pools[u.name]],true);put(pool-2,arity);put(pool+2,debug);
[1578,code2*4,N,4,arity,debug,pool,0].forEach((v,i)=>put(fn2+i*4,v));put(root+8,2*4);
assert.deepEqual(env.table.get(get(registry+8+16*code2))(fn2+6,1),[9*4,1]);
// Partial close releases reservations, keeps publications.
session.release(LOAD2);assert.throws(()=>session.install(LOAD2,unitOf('TARGET-LOADER-EXTREMA').name,record(unitOf('TARGET-LOADER-EXTREMA')),[]),/UNRESERVED_UNIT|SYMBOL_COUNT/);
// Refusals leave state: wrong record digest, wrong symbol count.
const before=[nextCode,registered.size,Array.from(new Uint32Array(memory.buffer,registry,2+256*4))];
assert.throws(()=>session.install(LOAD,unitOf('TARGET-LOADER-VECTOR-INIT').name,[6,'x'],[]),/CODE_RECORD/);
assert.throws(()=>session.install(LOAD,unitOf('TARGET-LOADER-VECTOR-INIT').name,record(unitOf('TARGET-LOADER-VECTOR-INIT')),[]),/SYMBOL_COUNT/);
assert.deepEqual([nextCode,registered.size,Array.from(new Uint32Array(memory.buffer,registry,2+256*4))],before);
console.log(JSON.stringify({status:'PASS',functions:manifest.function_count,helpers:manifest.helpers.length,rootCells:manifest.root_cells,generations:session.generations(),registeredRoots:registered.size,extremaCases:read('extrema-native.json').length,valuesCases:read('values-native.json').length,assqCases,keywordResults}));
```

---

## Stage 2 — heap and stack sizing, growth policy, timer split (A-14, R-8)

### Inventory

| # | file | change |
|---|---|---|
| 2.1 | `runtime/wasm32/layout.mjs` (new) | derive a disjoint, aligned layout from a configuration and the manifests |
| 2.2 | `tests/wasm/stage1/loader-target/boot0.mjs` | use the layout; drop the fixed region constants; advertise the same stack sizes it allocates |
| 2.3 | `runtime/wasm32/collector-owner.mjs` | headroom growth in `ensure`; `freeTarget` in the layout; split the copy timer |
| 2.4 | `tests/wasm/stage1/loader-target/startup-timing.mjs` | no change; new phases `collector.prepare` / `collector.c` appear in the journal |
| 2.5 | `tests/wasm/stage1/loader-target/startup-baseline.py` | `--space=16|32|64` runs, one process each |

### 2.1 Layout builder — UNEXECUTED

Today's `boot0.mjs` fixes `temp` and `control` at 16 KiB each while
`process-service` advertises 1 MiB / 512 KiB. The builder places every region
from one configuration and refuses overlap; the numbers below are A-14's
starting values, not an optimum.

```js
const KiB=1024,MiB=1048576,PAGE=65536;
export const DEFAULT_CONFIG={spaceBytes:32*MiB,freeTarget:16*MiB,valueStack:1*MiB,tempStack:512*KiB,controlStack:1*MiB,
  bindings:16*KiB,logCapacity:262144,generations:2,postImageCodes:8192,slotOffset:8};
export function deriveLayout(config,{bootFunctions,bootRootCells,runtimeFunctions,runtimeRootCells,image,tcr=1024,cStack=[1048576,1114112]}){
  const c={...DEFAULT_CONFIG,...config};const align=(n,a)=>Math.ceil(n/a)*a;
  const rows=16+bootFunctions+c.generations*runtimeFunctions+c.postImageCodes;
  const rootCells=bootRootCells+c.generations*runtimeRootCells+c.logCapacity/4;
  const regions=[],claim=(name,role,start,bytes,extra={})=>{const r={name,role,start,end:start+bytes,...extra};
    for(const o of regions)if(r.start<o.end&&o.start<r.end)throw Error('layout overlap '+name+'/'+o.name);regions.push(r);return r;};
  claim('tcr','tcr',tcr,256);claim('c-stack','c-stack',cStack[0],cStack[1]-cStack[0]); // fixed by the compiled C service
  for(const [i,r] of image.entries())claim('image-'+i,'image',r.start,r.end-r.start,r.extra??{});
  let p=Math.max(...regions.map(r=>r.end));const next=(name,role,bytes,a=PAGE)=>{p=align(p,a);const r=claim(name,role,p,bytes);p=r.end;return r;};
  const bindings=next('bindings','bindings',c.bindings);
  const vstack=next('vstack','vstack',c.valueStack),temp=next('temp','temp',c.tempStack),control=next('control','control',c.controlStack);
  const registry=next('registry','image',align(8+16*rows,8)); // read by generated code; pinned like image data
  const rootList=next('root-list','root-list',align(4*rootCells,PAGE));
  const external=next('external','external',align(4*rootCells,PAGE));
  const globals=next('runtime-globals','runtime-globals',16,16);
  const scratch=next('scratch','scratch',align(96+c.spaceBytes/8*20+c.logCapacity*12,PAGE)); // owner #workspace bound
  const spaces=[next('heap-0','space',c.spaceBytes),next('heap-1','space',c.spaceBytes)];
  return {regions:regions.filter(r=>r.role!=='space'),spaces:spaces.map(s=>({name:s.name,start:s.start,end:s.end})),
    rows,slotOffset:c.slotOffset,tableCapacity:rows+c.slotOffset,registry:registry.start,freeTarget:c.freeTarget,
    tcrWords:{48:spaces[0].start,52:spaces[0].end,56:spaces[0].start,64:vstack.start+8,68:vstack.start+8,72:vstack.end,
      76:temp.start,80:temp.start,84:temp.end,88:control.start,92:control.start,96:control.end,104:bindings.start,
      120:vstack.start+8200,124:vstack.start+8264,128:vstack.start},
    stackDefaults:[c.valueStack,c.controlStack,c.tempStack],initialPages:Math.ceil(p/PAGE)};
}
```

`boot0.mjs` then does `const L=deriveLayout(config,{...})`, builds `memory`
with `L.initialPages`, writes `L.tcrWords`, passes `L.regions/spaces` to
`CollectorOwner.create`, sizes tables from `L.tableCapacity`, and passes
`L.stackDefaults` to `processService` so the advertised sizes equal the
allocated areas. The `image` regions and the boot image's fixed addresses
(`static`, roots, registry) stay where the cross-loader put them; the builder
only refuses to overlap them.

### 2.3 Growth with headroom, and the timer split — UNEXECUTED

```js
 // collector-owner.mjs: layout gains freeTarget (0 keeps today's behaviour).
 ensure(bytes){
  this.#requireBoundary();need(integer(bytes)&&bytes>0&&bytes%8===0,'allocation request');
  this.#validateLive();
  if(this.#t(52)-this.#t(48)>=bytes)return {collected:false,grown:false};   // fits: never refuse for lack of headroom
  if(this.collectionInhibition)return this.#growInhibited(bytes);
  const collection=this.collect();
  const live=this.#t(48)-this.#t(56),free=this.#t(52)-this.#t(48),target=this.#layout.freeTarget??0;
  if(free>=bytes&&free-bytes>=target)return {collected:true,grown:false,collection};
  // Grow at the collection that first leaves less than the target free, not at the next failure.
  const capacity=align(Math.max(live+bytes+target,this.#t(52)-this.#t(56)),PAGE);
  const moved=this.#relocateHeap(capacity);
  return {collected:true,grown:true,collection,moved};
 }
 #copyInto(destination){
  const m=this.#measure??((_p,run)=>run());
  const prepared=m('collector.prepare',()=>{ // host: root enumeration, list write, scratch sizing
   const {active,slots}=this.#validate(),scratch=this.#region('scratch'),list=this.#region('root-list');
   need(destination.start!==active.start&&destination.end<=this.view.byteLength,'destination');
   this.#workspace();
   new Uint8Array(this.#memory.buffer,scratch.start,96).fill(0);
   const set=(o,v)=>this.#set(scratch.start+o,v);set(0,this.#layout.tcr);set(16,destination.start);set(20,destination.end);set(68,this.#layout.logCapacity);set(72,list.start);set(76,slots.length);set(80,scratch.end);
   slots.forEach((p,i)=>this.#set(list.start+4*i,p));
   return {active,slots,scratch};});
  const count=this.collectionCount;need(count<536870911,'collection count exhausted');
  this.#busy=true;
  try{
   const status=m('collector.c',()=>this.#collector.collect(prepared.scratch.start)); // C: inventory, object map, copy
   need(status===0,'collection refused '+status);need(this.collectionCount===count+1,'collection count publication');
   return {source:prepared.active.start,destination:destination.start,objects:this.#get(prepared.scratch.start+84),reclaimed:this.#get(prepared.scratch.start+92),rootSlots:prepared.slots.length,usedBytes:this.#t(48)-this.#t(56)};
  }finally{this.#busy=false;}
 }
```

The `collector.copy` span stays as the parent so P-0's journal shape is kept;
`usedBytes` and `rootSlots` per collection let the report separate the fixed
host part from the proportional C part (review AMEND on A-14).

### 2.5 The 16/32/64 comparison

`startup-baseline.py` gains `--space=<MiB>`; it passes
`{"spaceBytes":N*MiB}` to `boot0.mjs --layout=...`, one fresh process per
value, 600 s timeout, partial journals retained; report per run: READY time,
peak/READY RSS, collections, `collector.prepare` and `collector.c` totals,
final space sizes, root allocation time, stack high-water (sampled, lower
bound). The 32 MiB run is the default run.

---

## Stage 3 — input ownership and release (A-16, R-9)

### Inventory

| # | file | change |
|---|---|---|
| 3.1 | `tests/wasm/stage1/loader-target/boot0.mjs` (main) | read archives into standalone buffers; transfer, never clone; keep only FASL bytes and a directory on the main thread |
| 3.2 | `runtime/wasm32/target-load-session.mjs` `bundleNamespace` | namespace entries own FASL bytes only; containers are compact rows |
| 3.3 | `runtime/wasm32/code-archive.mjs` | drop `bytes` after `new WebAssembly.Module` (already in §1.6); manifest kept compact |
| 3.4 | `runtime/wasm32/target-bundle.mjs` | v2 decode does not snapshot the whole container twice |
| 3.5 | `tests/wasm/stage1/loader-target/retention-check.mjs` (new) | retaining-path and forced-GC diagnostic |

### 3.1 Transfer instead of clone — UNEXECUTED

```js
// main thread
function standalone(path){const size=fs.statSync(path).size,buffer=new ArrayBuffer(size),fd=fs.openSync(path,'r');
  let off=0;while(off<size)off+=fs.readSync(fd,new Uint8Array(buffer,off),0,size-off,off);fs.closeSync(fd);return buffer;} // not a pooled Buffer
const archiveBuffers=archives.map(a=>standalone(a.path));
const files=[...selected.values()].map(f=>{const {manifest,fasl}=decodeTargetContainer(f.bytes,f.sha256); // main keeps FASL + directory only
  return {path:f.path,sha256:f.sha256,fasl,units:manifest.units,archive_sha256:manifest.archive_sha256};});
const worker=new Worker(new URL(import.meta.url),{workerData:{...,files,archives:archives.map((a,i)=>({digest:a.digest,manifest:a.manifest,bytes:archiveBuffers[i]}))},
  transferList:archiveBuffers}); // sender's buffers are detached here
```

The main-thread namespace serves reads from `files[].fasl` (5.8 MB in total);
`serviceRequest` is unchanged. Nothing else on the main thread references an
archive after construction.

### 3.2 Compact namespace rows — UNEXECUTED

```js
export function bundleNamespace({files,cwd='/ccl',cclRoot='/ccl',measure=(_p,run)=>run()}){
  const entries=new Map([['/',{path:'/',kind:'directory'}]]),containers=new Map();
  for(const file of files){
    need(!entries.has(file.path),'DUPLICATE_FILE');
    const fasl=file.fasl??measure('namespace.decode',()=>decodeTargetContainer(file.bytes,file.sha256).fasl,{path:file.path});
    ...parents...
    entries.set(file.path,{path:file.path,kind:'file',bytes:fasl,sha256:sha256(fasl)});
    containers.set(file.path,{archive_sha256:file.archive_sha256,units:file.units}); // no raw container retained
    file.bytes=undefined; // caller-held alias released
  }
  ...
  return Object.freeze({namespace,containers,session});
}
```

### 3.3 / 3.4 Release points

- `admitCodeArchive`: `bytes=null` after the module is constructed; the
  manifest kept is the compact one (rows, entries, digests); the D2
  classification record is verified then dropped from the runtime object.
- `decodeTargetContainer`: one `snapshotBytes` of the input, `fasl` sliced
  once; no template, no module copies.
- Per-open: `pending`/`open` rows hold `{path, token, archive, install}`; on
  close or failed open the row is deleted and `archive.release(token)` runs.
- Worker: after all archives are admitted, `workerData.archives = undefined`
  so the detached-and-received buffers are not pinned by `workerData`.

### 3.5 Retention check — UNEXECUTED

```js
// node --expose-gc retention-check.mjs <out> ; a focused fixture, not the timed READY run
const registry=new FinalizationRegistry(label=>console.log('collected',label));
registry.register(archiveBuffer,'runtime.archive bytes');
... admit, load one file, close it ...
archiveBuffer=undefined; workerData.archives=undefined;
globalThis.gc(); await new Promise(r=>setTimeout(r,0)); globalThis.gc();
console.log(process.memoryUsage()); // expect 'collected runtime.archive bytes' before this line
```

Milestones to record (A-16/P-1): owned backing-buffer bytes and counts by
thread and category at admission start/end, file close and READY, beside
P-0's counters; expected at READY: no application-owned reference to any
archive buffer, container buffer or validation manifest; retained: FASL
bytes, compact rows, live generations.

---

## Order and gates, restated for the three stages

1. Stage 1: build the runtime archive; READY with `boot0.mjs`; A-8 (a) and
   (b); archive-check; second generation, partial close, refusals; count
   product modules = 1,048; then the boot archive (§1.10) → 7; P-0
   instrumentation rerun against F-13.
2. Stage 2: layout builder on v1 or v2 (it is independent); `ensure`
   headroom; timer split; 16/32/64 runs; record fixed versus proportional
   collection cost.
3. Stage 3: transfer and compact rows; release points; retention check;
   memory milestones; then P-4's LL21-b record with measured retention.
