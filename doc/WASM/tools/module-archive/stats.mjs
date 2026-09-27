import fs from 'node:fs';
import {decodeTargetBundle} from '../../../../runtime/wasm32/target-bundle.mjs';
const dir=process.argv[2];
const manifest=JSON.parse(fs.readFileSync(dir+'/bundle-manifest.json'));
let files=0,modules=0,units=0,bytes=0,templateBytes=0,symbolImports=0,codeImports=0,symbolCount=0,maxSym=0,maxImports=0,fnImports=0;
const importHist={};
for(const f of manifest.files){
  const b=fs.readFileSync(dir+'/'+f.bundle);
  const d=decodeTargetBundle(b,f.sha256);
  files++;bytes+=b.length;
  units+=d.manifest.units.length;
  for(const u of d.manifest.units)symbolCount+=u.symbol_count;
  for(const m of d.manifest.codeSet.modules){
    modules++;
    const bl=d.modules.get(m.name).bytes.length;templateBytes+=d.modules.get(m.name).template.length;
    const imps=m.d2.outputs.full.imports;
    const s=imps.filter(i=>i.module==='symbols').length,c=imps.filter(i=>i.module==='codes').length,fn=imps.filter(i=>i.kind==='function').length;
    symbolImports+=s;codeImports+=c;fnImports+=fn;maxSym=Math.max(maxSym,s);maxImports=Math.max(maxImports,imps.length);
    const k=Math.min(50,imps.length);importHist[k]=(importHist[k]||0)+1;
    if(modules===1)console.log('SAMPLE',JSON.stringify({name:m.name,code_id:m.code_id,version:m.version,symbol_mode:m.symbol_mode,imports:imps.map(i=>i.module+'.'+i.name+':'+i.kind),exports:m.d2.outputs.full.exports?.length,entries:m.entries,bytes:bl,features:m.d2.outputs.full.features}).slice(0,1500));
  }
}
console.log(JSON.stringify({files,units,modules,bundleBytes:bytes,templateBytes,symbolImports,codeImports,fnImports,symbolCountPerUnitTotal:symbolCount,maxSymbolImportsPerModule:maxSym,maxImportsPerModule:maxImports,perModuleImportHistogram:importHist}));
