import fs from 'node:fs';
import {check} from './check.mjs';
const [output,only]=process.argv.slice(2);
const names=JSON.parse(fs.readFileSync(new URL('./binaries.json',import.meta.url)));
const binaries=Object.fromEntries(names.map(name=>[name,new Uint8Array(fs.readFileSync(new URL('./'+name+'.wasm',import.meta.url)))]));
try {
  const result=check(binaries,{only});
  fs.writeFileSync(output,JSON.stringify({...result,engine:process.version,versions:process.versions},null,2)+'\n');
  console.log(JSON.stringify({status:'PASS',checks:result.checks}));
} catch(error) {
  fs.writeFileSync(output,JSON.stringify({status:'FAIL',error:String(error),stack:error.stack},null,2)+'\n');
  console.error(String(error));process.exitCode=1;
}
