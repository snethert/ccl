import assert from './assert.mjs';
import {browserConfiguration} from './browser-config.mjs';
try{
 const q=new URL(import.meta.url).searchParams,options={defaults:[1048576,1048576,524288],stackSize:0};
 const observed=browserConfiguration(options);
 if(q.get('mode')==='probe')postMessage(observed);
 else{
  const names=await(await fetch('./assets.json')).json(),assets={};
  for(const name of names)assets[name]=new Uint8Array(await(await fetch('./'+name)).arrayBuffer());
  const cases=JSON.parse(new TextDecoder().decode(assets['cases.json']));
  assert.deepEqual(cases.at(-1).input,observed.input,'BROWSER_INPUT_CHANGED');
  const {execute}=await import('./check.mjs');postMessage(execute(assets,Number(q.get('base'))));
 }
}catch(e){postMessage({error:String(e)+'\n'+e.stack});}
