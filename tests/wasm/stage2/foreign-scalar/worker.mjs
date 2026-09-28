import {check} from './check.mjs';
try {
  const names=await (await fetch('./binaries.json')).json();
  const binaries=Object.fromEntries(await Promise.all(names.map(async name=>[name,new Uint8Array(await (await fetch('./'+name+'.wasm')).arrayBuffer())])));
  postMessage({...check(binaries),userAgent:navigator.userAgent});
} catch(error) {postMessage({status:'FAIL',error:String(error),stack:error.stack});}
