import fs from 'node:fs';
import {decodeTargetBundle} from '../../../../runtime/wasm32/target-bundle.mjs';
import {inspect} from '../../../../runtime/wasm32/binary.mjs';
const dir=process.argv[2];
const manifest=JSON.parse(fs.readFileSync(dir+'/bundle-manifest.json'));
let total=0,body=0,modules=0,fnCount=0,maxFn=0,maxBytes=0,units=0;
const perFile=[];
for(const f of manifest.files){
  const b=fs.readFileSync(dir+'/'+f.bundle);
  const d=decodeTargetBundle(b,f.sha256);
  let ft=0,fb=0;
  for(const m of d.manifest.codeSet.modules){
    const bytes=d.modules.get(m.name).bytes;modules++;total+=bytes.length;ft+=bytes.length;
    const r=m.entries.reduce((n,e)=>n+(e.range.end-e.range.start),0);body+=r;fb+=r;
    maxBytes=Math.max(maxBytes,bytes.length);
    if(modules%500===1){const x=inspect(bytes,{ownerRetry:true});fnCount+=x.functions.length;maxFn=Math.max(maxFn,x.functions.length);}
  }
  units+=d.manifest.units.length;
  perFile.push([f.path.split('/').pop(),d.manifest.codeSet.modules.length,ft]);
}
perFile.sort((a,b)=>b[2]-a[2]);
console.log(JSON.stringify({modules,units,totalBytes:total,entryBodyBytes:body,helperFraction:(1-body/total).toFixed(3),maxModuleBytes:maxBytes,sampledFunctionCountsTotal:fnCount,sampledModules:Math.ceil(modules/500),maxFunctionsPerSampledModule:maxFn,largestFiles:perFile.slice(0,6),smallestFiles:perFile.slice(-3)}));
