import fs from 'node:fs';import {sha256} from './sha256.mjs';
const dir=process.argv[2],generation=Number(process.argv[3]),bundle=JSON.parse(fs.readFileSync(dir+'/bundle.json')),rows=bundle.modules.filter(m=>m.generation<=generation);
const hashes=new Set();let bytes=0;globalThis.retained=rows.map(m=>{const b=fs.readFileSync(dir+'/full/'+m.name+'.wasm');hashes.add(sha256(b));bytes+=b.length;return new WebAssembly.Module(b);});
console.log(JSON.stringify({modules:rows.length,unique_binaries:hashes.size,encoded_bytes:bytes,flags:process.execArgv}));
