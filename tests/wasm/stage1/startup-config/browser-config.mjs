import {processConfiguration} from './config.mjs';
const need=(ok,why)=>{if(!ok)throw Error(why);};
// Defaults and override describe owned Lisp stacks, never the browser JS stack.
export function browserConfiguration({defaults,stackSize=0},host=globalThis){
 const cpuCount=host.navigator?.hardwareConcurrency;
 need(Number.isSafeInteger(cpuCount)&&cpuCount>=1,'BROWSER_CPU');
 need(typeof host.performance?.now==='function','BROWSER_CLOCK');
 const first=host.performance.now(),second=host.performance.now();
 need(Number.isFinite(first)&&first>=0&&Number.isFinite(second)&&second>=first,'BROWSER_CLOCK');
 need(typeof host.WebAssembly?.Memory==='function','BROWSER_MEMORY');
 const pageSize=new host.WebAssembly.Memory({initial:1,maximum:1}).buffer.byteLength;
 need(pageSize===65536,'WASM_PAGE');
 const input={pageSize,clockTicks:1000,cpuCount,stackSize,defaults:structuredClone(defaults)};
 processConfiguration(input);
 return {input,provenance:{cpuCount:'navigator.hardwareConcurrency',pageSize:'one WebAssembly memory page',
  clockTicks:'1000 millisecond units per second for performance.now; not measured timer resolution',
  stacks:'owner configuration; not browser JavaScript stack capacity',clockAvailable:true}};
}
