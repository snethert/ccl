import fs from 'node:fs';
import {numericChecks} from './numeric-check.mjs';
const [runtime,out]=process.argv.slice(2);
const binaries=Object.fromEntries(['collector','integer','float','detector'].map(name=>[name,new Uint8Array(fs.readFileSync(runtime+'/'+name+'.wasm'))]));
const result=numericChecks(binaries);
fs.writeFileSync(out,JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));
