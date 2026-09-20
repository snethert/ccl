import assert from './assert.mjs';
import {browserConfiguration} from './browser-config.mjs';
const options={defaults:[1024,2048,4096],stackSize:31};let checks=0;
const host=()=>({navigator:{hardwareConcurrency:8},performance:{v:12,now(){return this.v++;}},WebAssembly});
for(const cpu of [1,2,8,64]){
 const h=host();h.navigator.hardwareConcurrency=cpu;const x=browserConfiguration(options,h);
 assert.equal(x.input.cpuCount,cpu,'reported CPU');assert.equal(x.input.pageSize,65536,'actual Wasm page');assert.equal(x.input.clockTicks,1000,'millisecond units');assert.deepEqual(x.input.defaults,options.defaults);checks+=4;
}
for(const [name,edit,why]of [
 ['cpu missing',h=>delete h.navigator.hardwareConcurrency,'BROWSER_CPU'],
 ['cpu zero',h=>h.navigator.hardwareConcurrency=0,'BROWSER_CPU'],
 ['cpu fraction',h=>h.navigator.hardwareConcurrency=1.5,'BROWSER_CPU'],
 ['clock missing',h=>delete h.performance.now,'BROWSER_CLOCK'],
 ['clock NaN',h=>h.performance.now=()=>NaN,'BROWSER_CLOCK'],
 ['clock negative',h=>h.performance.now=()=>-1,'BROWSER_CLOCK'],
 ['clock backwards',h=>h.performance.now=function(){return this.v--;},'BROWSER_CLOCK'],
 ['memory missing',h=>delete h.WebAssembly,'BROWSER_MEMORY'],
 ['wrong page',h=>h.WebAssembly={Memory:class{constructor(){this.buffer=new ArrayBuffer(4096);}}},'WASM_PAGE']
]){const h=host();edit(h);assert.throws(()=>browserConfiguration(options,h),new RegExp(why),name);checks++;}
const o=structuredClone(options),result=browserConfiguration(o,host());o.defaults[0]=1;assert.equal(result.input.defaults[0],1024,'stack snapshot');checks++;
console.log(JSON.stringify({status:'PASS',checks}));
