import {sha256} from './proposal/sha256.mjs';
import {byteView,snapshotBytes,utf8,hex} from './proposal/bytes.mjs';
import {CollectorOwner} from './proposal/collector-owner.mjs';
import {integerService} from './proposal/integer-service.mjs';
import {floatService} from './proposal/float-service.mjs';
import {scalarFloatService,regionModule} from './proposal/scalar-service.mjs';
import {floatingCapabilities,admitFloatingCapabilities} from './proposal/floating-capabilities.mjs';
import {sha,validate,LazyLoader,PROFILE} from './proposal/loader.mjs';
import {inspect} from './proposal/binary.mjs';
import {BindingInstaller} from './proposal/installer.mjs';
export const need=(ok,name)=>{if(!ok)throw Error(name);};
export function checks(assets,hashes) {
 const results=[];
 const check=(ok,name)=>{need(ok,name);results.push(name);};
 const refuses=(fn,why,name)=>{let error;try{fn();}catch(e){error=e;}check(error?.message.includes(why),name);};
 // Published NIST one-block, two-block and million-a examples; empty is an
 // additional literal vector. Expectations are never produced by this SHA.
 for(const [label,input,expected] of [
  ['empty','','e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'],
  ['abc','abc','ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'],
  ['two-block','abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq','248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1'],
  ['million-a','a'.repeat(1000000),'cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0']
 ])check(sha256(input)===expected,'vector-'+label);
 for(const [name,expected] of Object.entries(hashes)) {
  const b=assets[name];check(sha256(b)===expected,'binary-'+name);
  const padded=new Uint8Array(b.length+19);padded.fill(0xa5);padded.set(b,7);
  check(sha256(padded.subarray(7,7+b.length))===expected,'offset-'+name);
  check(sha256(new DataView(padded.buffer,7,b.length))===expected,'view-'+name);
 }
 const source=new Uint8Array([9,1,2,3,8]),copy=snapshotBytes(source.subarray(1,4));source.fill(0);
 check(hex(copy)==='010203','snapshot-view-copy');
 const ab=new Uint8Array([4,5,6]),ac=snapshotBytes(ab.buffer);ab.fill(0);check(hex(ac)==='040506','snapshot-buffer-copy');
 const sb=new SharedArrayBuffer(5),sv=new Uint8Array(sb);sv.set([7,8,9,10,11]);const sc=snapshotBytes(new DataView(sb,1,3));sv.fill(0);check(hex(sc)==='08090a','snapshot-shared-copy');
 check(hex(utf8('λ😀\ud800'))==='cebbf09f9880efbfbd','utf8-nonascii');
 refuses(()=>byteView({length:3}),'Expected','reject-not-buffer');
 check(sha('abc')===sha256('abc'),'loader-sha-alias');
 const minimal=new Uint8Array([0,97,115,109,1,0,0,0]);inspect(minimal);
 for(let i=0;i<8;i++){const b=minimal.slice();b[i]^=1;refuses(()=>inspect(b),'HEADER','bad-header-'+i);}
 refuses(()=>inspect(minimal.subarray(0,7)),'HEADER','short-header');
 const regions=regionModule([{start:128,end:256}]);check(new WebAssembly.Instance(regions.module).exports.contains(128,128)===1,'region-name-encoding');
 const N=77825,T=77838,tcr=1024,base=131064,root=131080,image=786432,A=2097152;
 const memory=new WebAssembly.Memory({initial:48,maximum:32769,shared:true}),view=new DataView(memory.buffer);
 const put=(p,v)=>view.setUint32(p,v,true),get=p=>view.getUint32(p,true),set=(o,v)=>put(tcr+o,v);
 const ranges=[['tcr',tcr,tcr+256],['image',77824,77864],['image',image,image+16384],['vstack',base,base+32776],['temp',196608,212992],['control',212992,229376],['external',262144,266240],['bindings',266240,270336],['c-stack',1048576,1114112],['root-list',1180000,1198000],['scratch',1200000,1800000]];
 const layout={version:1,collector:'copying',workers:1,egc:false,tcr,maximumPages:32769,logCapacity:32768,regions:ranges.map(([role,start,end],i)=>({name:role+'-'+i,role,start,end})),spaces:[A,A+32768].map((start,i)=>({name:'heap-'+i,start,end:start+16384})),groups:['module-constants','callbacks','registry','host'].map(kind=>({kind,slots:[]}))};
 put(N-1,N);put(N+3,N);put(T-6,1850);for(let i=1;i<8;i++)put(T-6+4*i,N);
 for(const [o,v]of [[48,A],[52,A+16384],[56,A],[68,base+8],[72,base+32776],[64,root+24],[128,root],[80,196608],[76,196608],[84,212992],[92,212992],[88,212992],[96,229376],[104,266240],[108,0],[120,base+8200],[124,base+8264],[188,N],[200,7]])set(o,v);
 put(base,0);put(base+4,0);put(root,base);put(root+4,4);for(let i=0;i<4;i++)put(root+8+4*i,N);
 const collector=assets['collector.wasm'],owner=CollectorOwner.create(memory,collector,hashes['collector.wasm'],layout),callError=new WebAssembly.Tag({parameters:['i32']});
 check(owner instanceof CollectorOwner&&!(owner instanceof Promise),'synchronous-owner');
 const options={memory,tcr,owner,callError,bytes:assets['float.wasm'],digest:hashes['float.wasm'],detectorBytes:assets['detector.wasm'],detectorDigest:hashes['detector.wasm'],scalarBytes:assets['scalar.wasm'],scalarDigest:hashes['scalar.wasm'],integerBytes:assets['integer.wasm'],integerDigest:hashes['integer.wasm'],pinned:[{start:image,end:image+16384}]};
 const integer=integerService({...options,bytes:options.integerBytes,digest:options.integerDigest}),floating=floatService(options),scalar=scalarFloatService(options),bundle=floatingCapabilities(options);
 check([integer,floating,scalar,bundle.floating].every(x=>typeof x==='function'),'synchronous-services');
 check(Object.isFrozen(bundle),'frozen-bundle');
 check(admitFloatingCapabilities(bundle,{memory,tcr,call_error:callError})===bundle,'bundle-admission');
 put(root+4,2);put(root+8,12);put(root+12,20);check(integer(0,root)===1&&get(root+8)===32,'integer-add');
 for(const [p,v]of [[image,3],[image+16,5]]){put(p,791);put(p+4,0);view.setFloat64(p+8,v,true);}
 put(root+4,4);put(root+8,image+6);put(root+12,image+22);put(root+16,N);put(root+20,N);
 for(const [name,fn]of [['float',floating],['scalar',scalar],['bundle',bundle.floating]]){
  put(root+16,N);put(root+20,N);
  let status;try{status=fn(0,root,1);}catch(e){throw Error(name+' invocation: '+(e.is?.(callError)?e.getArg(callError,0):e));}const p=get(root+16)-6;check(status===3072&&get(p)===791&&view.getFloat64(p+8,true)===8,name+'-add');
 }
 const wrong='0'.repeat(64),mutate=b=>{const x=b.slice();x[x.length-1]^=1;return x;};
 for(const damaged of [false,true]){
  refuses(()=>CollectorOwner.create(memory,damaged?mutate(collector):collector,damaged?hashes['collector.wasm']:wrong,layout),'collector digest','collector-binding-'+damaged);
  refuses(()=>integerService({...options,bytes:damaged?mutate(options.integerBytes):options.integerBytes,digest:damaged?options.integerDigest:wrong}),'integer owner capability','integer-binding-'+damaged);
  refuses(()=>floatService({...options,bytes:damaged?mutate(options.bytes):options.bytes,digest:damaged?options.digest:wrong}),'FLOAT_CAPABILITY','float-binding-'+damaged);
  refuses(()=>floatService({...options,detectorBytes:damaged?mutate(options.detectorBytes):options.detectorBytes,detectorDigest:damaged?options.detectorDigest:wrong}),'FLOAT_CAPABILITY','detector-binding-'+damaged);
  refuses(()=>scalarFloatService({...options,scalarBytes:damaged?mutate(options.scalarBytes):options.scalarBytes,scalarDigest:damaged?options.scalarDigest:wrong}),'SCALAR_DIGEST','scalar-binding-'+damaged);
 }
 refuses(()=>validate(minimal,{sha256:wrong}),'BINARY_DIGEST','loader-digest');
 // A UTF-8 manifest head from the real synchronous installer, without modules.
 const table=new WebAssembly.Table({element:'anyfunc',initial:4}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:4});put(4096,4);put(4100,1);
 const installer=new BindingInstaller({memory,table,tail_table,call_error:callError,nonlocal_exit:new WebAssembly.Tag({parameters:['i32']}),registry:4096,reserved:1,symbols:[],keywords:[]});
 const manifest={version:1,generation:1,previous:null,phase:'boot',modules:[],functions:[],bindings:[],note:'λ😀'};
 const installed=installer.install(manifest,[],[],()=>{throw Error('unused');},{});
 check(installed.head===hashes['manifest.utf8'],'installer-utf8-head');
 // Change the owner's original bytes between digest checking and engine
 // validation. Only the loader's owned snapshot may reach the engine.
 for(const kind of ['view','buffer','data-view']){
  const source=assets['binding/one.wasm'],backing=new Uint8Array(source.length+(kind==='buffer'?0:12));
  backing.set(source,kind==='buffer'?0:5);
  const offered=kind==='buffer'?backing.buffer:kind==='view'?backing.subarray(5,5+source.length):new DataView(backing.buffer,5,source.length);
  const table=new WebAssembly.Table({element:'anyfunc',initial:4}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:4});
  const parsed=inspect(source),record={name:'one',slot:1,code:1,version:4,signature:17,role:23,sha256:hashes['binding/one.wasm'],profile:PROFILE,imports:parsed.imports,entries:Object.fromEntries(parsed.exports.map(x=>[x.name,{index:x.index,role:x.name}]))};
  const nonlocal_exit=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),registry=4096;
  put(registry,4);put(registry+4,1);[1,4,17,23].forEach((v,i)=>put(registry+24+4*i,v));
  const env={memory,tcr,table,tail_table,code_registry:registry,call_error:callError,type_error,nonlocal_exit},imports={env};
  for(const i of parsed.imports)if(i.module!=='env')(imports[i.module]??={})[i.name]=0;
  const loader=new LazyLoader({memory,table,tail_table,call_error:callError,nonlocal_exit,catalog:[record],stub:new WebAssembly.Module(assets['binding/stub.wasm']),readBytes:()=>offered});
  loader.defer('one',imports);
  const original=WebAssembly.validate;
  let snapshotIntact=false,installError;
  try{
   WebAssembly.validate=b=>{backing.fill(0);snapshotIntact=sha(b)===record.sha256;return original(b);};
   loader.install(1);
  }catch(e){installError=e;}finally{WebAssembly.validate=original;}
  check(snapshotIntact,'loader-owned-snapshot-'+kind);
  if(installError)throw installError;
  check(loader.snapshot()[0].state==='READY','loader-ready-'+kind);
 }
 return {status:'PASS',checks:results.length,results};
}
