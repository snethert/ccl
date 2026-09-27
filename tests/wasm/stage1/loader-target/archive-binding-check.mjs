// Bind the textual equivalence witness to the exact admitted engine bytes.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const [stem,out]=process.argv.slice(2),hash=b=>createHash('sha256').update(b).digest('hex');
fs.mkdirSync(out,{recursive:true});
const manifest=JSON.parse(fs.readFileSync(stem+'.json'));
execFileSync('/usr/local/bin/wat2wasm',['--enable-all',stem+'.wat','-o',out+'/reassembled.wasm']);
const bytes=fs.readFileSync(out+'/reassembled.wasm');assert.equal(hash(bytes),manifest.template_sha256);
assert.equal(bytes[manifest.d2.template.offset],1);bytes[manifest.d2.template.offset]=3;
assert.equal(hash(bytes),manifest.binary_sha256);assert.deepEqual(bytes,fs.readFileSync(stem+'.wasm'));
const result={status:'PASS',binary:manifest.binary_sha256,template:manifest.template_sha256,
 manifest:hash(fs.readFileSync(stem+'.json'))};
fs.writeFileSync(out+'/result.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
