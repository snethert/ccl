import fs from 'node:fs';
import assert from 'node:assert/strict';
import {BindingInstaller} from './runtime/installer.mjs';
import {FLOAT_PROFILE,sha} from './runtime/loader.mjs';
import {floatingCapabilities} from './runtime/floating-capabilities.mjs';
import {inspect} from './runtime/binary.mjs';
import {entryRanges} from './runtime/ranges.mjs';
export function checkInstaller({dir,gen,memory,tcr,get,put,owner:collectorOwner}){
 const NIL=77825,registry=1120000,raw=1130000,side=raw+32,symbol=raw+64+6,slot=8;
 const table=new WebAssembly.Table({element:'anyfunc',initial:32}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:32});
 new Uint8Array(memory.buffer,registry,520).fill(0);put(registry,32);put(registry+4,1);
 const template=gen.functions.get('core_gf_identity')-6;
 new Uint8Array(memory.buffer,raw,32).set(new Uint8Array(memory.buffer,template,32));
 put(raw,1834);put(raw+4,slot*4);put(raw+28,side+6);
 [2042,NIL,NIL,NIL,NIL,NIL,NIL,NIL].forEach((v,i)=>put(side+i*4,v));
 [1850,NIL,NIL,NIL,NIL,NIL,NIL,0].forEach((v,i)=>put(symbol-6+4*i,v));
 const bytes=fs.readFileSync(dir+'/compiled/core_gf_identity.wasm'),x=inspect(bytes,{ownerRetry:true});
 const row={name:'core_gf_identity',slot,code:slot,version:4,signature:17,role:23,sha256:sha(bytes),profile:FLOAT_PROFILE,imports:x.imports,entries:Object.fromEntries(x.exports.map(e=>[e.name,{index:e.index,role:e.name}])),ranges:entryRanges(bytes,{ownerRetry:true}),arity:[1,0,false,false,false,[]],captures:0};
 const integerBytes=fs.readFileSync(dir+'/integer.wasm'),floatBytes=fs.readFileSync(dir+'/float.wasm'),detectorBytes=fs.readFileSync(dir+'/detector.wasm');
 const bundle=floatingCapabilities({memory,tcr,owner:collectorOwner,callError:gen.call_error,integerBytes,integerDigest:sha(integerBytes),bytes:floatBytes,digest:sha(floatBytes),detectorBytes,detectorDigest:sha(detectorBytes),pinned:[]});
 const name=['FUNCALLABLE-WITNESS','GF'],owner=new BindingInstaller({...gen.env,floatingCapabilities:bundle,memory,table,tail_table,registry,reserved:4,symbols:[{name,address:symbol}],keywords:[],stub:new WebAssembly.Module(fs.readFileSync(dir+'/stub.wasm'))});
 const input={version:1,generation:1,previous:null,phase:'boot',modules:[row],functions:[{module:row.name,object:raw+6,immediates:side+6}],bindings:[{name,object:raw+6,previous:NIL}]};
 const imports={env:{...gen.env,table,tail_table,code_registry:registry},symbols:{...gen.symbols,...Object.fromEntries(gen.mods.find(m=>m.name==='core_gf_identity').symbols.map(([wire,id])=>[wire,gen.ownerWords.get(id)]))},codes:gen.codes,keywords:gen.keywords,owner:{ensure:bundle.ensure},integer:{calculate:bundle.integer},floating:{calculate:bundle.floating}};
 const checks=[],capture=()=>({bytes:Buffer.from(new Uint8Array(memory.buffer,registry,1100)),object:Buffer.from(new Uint8Array(memory.buffer,raw,96)),state:owner.state(),entry:table.get(slot),tail:tail_table.get(slot)});
 function refuse(label,change,reason){const m=structuredClone(input);const restore=change(m)||(()=>{}),before=capture();assert.throws(()=>owner.install(m,[name],[row],()=>bytes,imports),new RegExp(reason));assert.deepEqual(capture(),before);restore();checks.push(label);}
 refuse('explicit funcallable declaration',m=>{delete m.functions[0].immediates;},'OBJECT_HEADER');
 refuse('manifest vector identity',m=>{m.functions[0].immediates=get(raw+16);},'IMMEDIATES_IDENTITY');
 refuse('vector exact width',()=>{put(side,1786);return ()=>put(side,2042);},'OBJECT_HEADER');
 refuse('metadata binding',()=>{const old=get(raw+16);put(raw+16,NIL);return ()=>put(raw+16,old);},'METADATA_IDENTITY');
 const result=owner.install(input,[name],[row],()=>bytes,imports);assert.equal(result.generation,1);assert.equal(get(symbol+6),raw+6);
 put(tcr+64,132096);put(132096,124);put(tcr+116,0);put(tcr+120,132352);put(tcr+124,132512);
 const pair=table.get(slot)(raw+6,1);assert.deepEqual(pair,[124,1]);assert.equal(get(132352),124);put(tcr+116,0);
 checks.push('digest-bound loader installs and invokes the second shape');return checks;
}
