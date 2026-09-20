// Each cold trial runs in a fresh process. Warm metrics keep GC inside samples,
// explicit GC between trials; timings are descriptive, never a speed ranking.
import fs from 'node:fs';import v8 from 'node:v8';import os from 'node:os';import {performance} from 'node:perf_hooks';
import {compile,publish} from './bundle.mjs';import {inspect} from './binary.mjs';
const dir=process.argv[2],mode=process.argv[3],read=n=>JSON.parse(fs.readFileSync(dir+'/'+n)),bytes=n=>fs.readFileSync(dir+'/full/'+n+'.wasm'),template=n=>fs.readFileSync(dir+'/templates/'+n+'.wasm');
const bundle=read('bundle.json'),expected=read('expected.json'),policy=read('materialization.json').policy;
const raw=new Map(bundle.modules.map(m=>[m.name,bytes(m.name)])),templates=new Map(bundle.modules.map(m=>[m.name,template(m.name)])),rawRead=n=>raw.get(n),tempRead=n=>templates.get(n);
const memory=new WebAssembly.Memory({initial:16,maximum:32769,shared:true}),table=new WebAssembly.Table({element:'anyfunc',initial:expected.table_capacity}),tail=new WebAssembly.Table({element:'anyfunc',initial:expected.table_capacity});
const tags=new Map(),im=new Map();for(const m of bundle.modules){const imp={};for(const i of inspect(rawRead(m.name)).imports){const ns=imp[i.module]??={};if(i.kind==='tag'&&!tags.has(i.name))tags.set(i.name,new WebAssembly.Tag({parameters:i.signature.params}));ns[i.name]=i.kind==='memory'?memory:i.kind==='table'?(i.name==='tail_table'?tail:table):i.kind==='tag'?tags.get(i.name):0;}im.set(m.name,imp);}
const stamp=()=>({rss:process.memoryUsage().rss,heap_used:process.memoryUsage().heapUsed,external:process.memoryUsage().external,...v8.getHeapCodeStatistics()});
if(mode==='cold'){
 global.gc();const before=stamp(),rows=[],retained=[];
 for(const m of bundle.modules){const start=performance.now(),module=new WebAssembly.Module(rawRead(m.name)),compiled=performance.now(),instance=new WebAssembly.Instance(module,im.get(m.name)),instantiated=performance.now();table.set(m.slot,instance.exports.entry);tail.set(m.slot,instance.exports.tail_entry);const installed=performance.now();retained.push({module,instance});rows.push({name:m.name,compile_ms:compiled-start,instantiate_ms:instantiated-compiled,publish_ms:installed-instantiated});}
 global.gc();console.log(JSON.stringify({rows,before,after:stamp(),retained_modules:retained.length,retained_encoded_bytes:[...raw.values()].reduce((n,x)=>n+x.length,0)}));
}else{
 const compiled=compile(bundle,expected,rawRead,tempRead,policy);let sink;
 const operations={instantiate:()=>{sink=compiled.map(x=>new WebAssembly.Instance(x.module,im.get(x.record.name)));},validated_install:()=>{for(const m of bundle.modules){table.set(m.slot,null);tail.set(m.slot,null);}sink=publish(compile(bundle,expected,rawRead,tempRead,policy),n=>im.get(n),table,tail);}};
 const rows=[];for(const [metric,fn]of Object.entries(operations)){let end=performance.now()+1000;while(performance.now()<end)fn();for(let trial=0;trial<30;trial++){global.gc();let count=0,start=performance.now();do{fn();count++;}while(performance.now()-start<250);const elapsed=performance.now()-start;rows.push({metric,trial,count,elapsed_ms:elapsed,ms_per_bundle:elapsed/count});}}
 console.log(JSON.stringify({rows,live_sink:sink.length,host:{node:process.version,v8:process.versions.v8,platform:process.platform,arch:process.arch,os:os.release(),cpu:os.cpus()[0].model,flags:process.execArgv}}));
}
