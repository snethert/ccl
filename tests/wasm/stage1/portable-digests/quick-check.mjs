import fs from 'node:fs';
import path from 'node:path';
import {checks} from './checks.mjs';
import {bindingCheck} from './binding-browser.mjs';
const dir=process.argv[2],hashes=JSON.parse(fs.readFileSync(path.join(dir,'hashes.json'))),assets={};
for(const n of Object.keys(hashes))assets[n]=new Uint8Array(fs.readFileSync(path.join(dir,'assets',n)));
const result=checks(assets,hashes);
try{bindingCheck(assets,1048576,true);}catch(e){throw Error('installer snapshot publication failure: '+String(e));}
console.log(JSON.stringify(result));
