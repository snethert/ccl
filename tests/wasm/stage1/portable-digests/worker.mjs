try {
 if(!crossOriginIsolated||typeof Buffer!=='undefined'||typeof process!=='undefined')throw Error('Worker environment');
 // Trip immediately on accidental host dependence, without supplying a shim.
 Object.defineProperty(globalThis,'Buffer',{get(){throw Error('NODE_BUFFER_DEPENDENCY');}});
 const hashes=await (await fetch('./hashes.json')).json(),assets={};
 for(const n of Object.keys(hashes))assets[n]=new Uint8Array(await (await fetch('./assets/'+n)).arrayBuffer());
 const {checks}=await import('./checks.mjs'),{bindingCheck}=await import('./binding-browser.mjs');
 const shared=checks(assets,hashes),binding=[];
 const base=Number(new URL(import.meta.url).searchParams.get('base'));
 binding.push(bindingCheck(assets,base));
 if(JSON.stringify(bindingCheck(assets,base,true))!==JSON.stringify(binding[0]))throw Error('installer snapshot equality');
 for(const [n,b]of Object.entries(assets)){
  const actual=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b)),x=>x.toString(16).padStart(2,'0')).join('');
  if(actual!==hashes[n])throw Error('WebCrypto '+n);
 }
 postMessage({shared,binding});
}catch(e){postMessage({error:e.stack??String(e)});}
