import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {checks,need} from './checks.mjs';
import {sha256} from './proposal/sha256.mjs';
const dir=process.argv[2],hashes=JSON.parse(fs.readFileSync(path.join(dir,'hashes.json'))),assets={};
const reference=b=>createHash('sha256').update(b).digest('hex');
for(const [n,h]of Object.entries(hashes)){const b=fs.readFileSync(path.join(dir,'assets',n));need(reference(b)===h,'node-binary-'+n);assets[n]=new Uint8Array(b);}
const shared=checks(assets,hashes),rows=[];
let seed=0x2561804;
const random=()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return seed>>>0;};
for(const n of [...Array.from({length:261},(_,i)=>i),...Array.from({length:128},()=>random()%100000),1048577]){
 const b=new Uint8Array(n);for(let i=0;i<n;i++)b[i]=random();
 const expected=reference(b);need(sha256(b)===expected,'random-length-'+n);rows.push({length:n,sha256:expected});
}
// Exercise the upper length word, rather than just testing its formula.
const large=new Uint8Array(0x20000000+9);large[0]=0x80;large[large.length-1]=0x37;
const expected=reference(large);need(sha256(large)===expected,'64-bit-length');rows.push({length:large.length,sha256:expected});
const {bindingCheck}=await import(pathToFileURL(path.join(dir,'binding-browser.mjs')));
const binding=[];for(const base of [1048576,2147483648])binding.push(bindingCheck(assets,base));
const snapshotBinding=bindingCheck(assets,1048576,true);need(JSON.stringify(snapshotBinding)===JSON.stringify(binding[0]),'installer snapshot equality');
fs.writeFileSync(path.join(dir,'node.json'),JSON.stringify({shared,random:rows,binding},null,2)+'\n');
console.log(JSON.stringify({checks:shared.checks,random:rows.length,bindings:binding.length}));
