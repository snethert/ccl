import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {decodeTargetBundle} from '../../../../runtime/wasm32/target-bundle.mjs';
const dir=process.argv[2];
const manifest=JSON.parse(fs.readFileSync(dir+'/bundle-manifest.json'));
// Parse code section: hash each function body (excluding the two entry bodies) to count distinct helper bodies.
function bodies(bytes){let p=8;const leb=()=>{let n=0,s=0,b;do{b=bytes[p++];n+=(b&127)*2**s;s+=7;}while(b&128);return n;};
 const out=[];while(p<bytes.length){const id=bytes[p++],size=leb(),end=p+size;if(id===10){const count=leb();for(let i=0;i<count;i++){const n=leb();out.push(bytes.subarray(p,p+n));p+=n;}}p=end;}return out;}
const distinct=new Map();let total=0,totalBytes=0,modules=0;
for(const f of manifest.files){const d=decodeTargetBundle(fs.readFileSync(dir+'/'+f.bundle),f.sha256);
 for(const m of d.manifest.codeSet.modules){modules++;const bs=bodies(d.modules.get(m.name).bytes);const entryIdx=new Set(m.entries.map(e=>e.function_index));
  const fnImports=m.d2.outputs.full.imports.filter(i=>i.kind==='function').length;
  bs.forEach((body,i)=>{if(entryIdx.has(i+fnImports))return;total++;totalBytes+=body.length;const h=createHash('sha256').update(body).digest('hex');distinct.set(h,(distinct.get(h)||0)+1);});}}
const uniqueBytes=[...distinct.keys()].length;
console.log(JSON.stringify({modules,helperBodies:total,helperBytes:totalBytes,distinctHelperBodies:uniqueBytes,top:[...distinct.values()].sort((a,b)=>b-a).slice(0,5)}));
