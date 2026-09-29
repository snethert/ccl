import {callbackChecks} from './lisp-callbacks.mjs';
import {stringChecks} from './strings.mjs';
import {finalizerChecks} from './finalizers.mjs';
import {createNamespace} from './runtime/namespace.mjs';
import {foreignLibraries} from './runtime/foreign-libraries.mjs';
import {foreignService} from './runtime/foreign-service.mjs';
import {CollectorOwner} from './runtime/collector-owner.mjs';
import {deriveLayout} from './runtime/layout.mjs';
import {sha256} from './runtime/sha256.mjs';
import {declaration} from './declaration.mjs';
export function check(binaries,{only}={}) {
 const rows=[],assert=(ok,s)=>{if(!ok)throw Error(s);},equal=(a,b,s='equality')=>assert(Object.is(a,b),s+': '+a+' != '+b);
 const test=(name,run)=>{if(only&&name!==only)return;try{run();rows.push(name);}catch(e){throw Error(name+': '+e,{cause:e});}};
 const throws=(run,pattern)=>{try{run();}catch(e){assert(pattern.test(String(e)),'wrong refusal: '+e);return;}throw Error('missing refusal '+pattern);};
 const namespace=(bytes=binaries.library,limits={})=>createNamespace({version:1,cwd:'/lib',cclRoot:'/',limits,entries:[
  {path:'/',kind:'directory'},{path:'/lib',kind:'directory'},
  {path:'/lib/example.wasm',kind:'file',bytes,sha256:sha256(bytes)}]});
 function registry({ns=namespace(),edit=()=>{},maximumBytes,imports:provided,boundary:providedBoundary}={}){
  const events=[],entries=[],imports=provided??{host:{collect(){},observe(n){events.push(n);}}},d=declaration(sha256(binaries.library));
  const config={namespace:ns,libraries:[{path:'example.wasm',declaration:d,imports}],boundary:providedBoundary??{enter(op){entries.push(op);},leave(){}},errorTag:new WebAssembly.Tag({parameters:['i32']})};
  if(maximumBytes!==undefined)config.maximumBytes=maximumBytes;edit(config);
  return {open:()=>foreignLibraries(config),config,events,entries};
 }
 test('namespace-once',()=>{const f=registry(),r=f.open(),l=r.open('example');equal(r.open('example'),l);equal(f.events.length,1);equal(f.entries.length,2);});
 test('namespace-snapshot',()=>{const bytes=binaries.library.slice(),f=registry({ns:namespace(bytes)}),r=f.open();bytes.fill(0);
  f.config.libraries[0].declaration.sha256='0'.repeat(64);f.config.libraries[0].imports.host.observe=()=>{throw Error('replaced');};
  equal(r.open('example').state,'ready');equal(f.events.length,1);});
 test('namespace-close',()=>{const f=registry(),r=f.open(),l=r.open('example');r.close('example');equal(l.state,'retired');throws(()=>r.open('example'),/RETIRED/);equal(f.events.length,1);});
 test('namespace-close-unopened',()=>{const f=registry(),r=f.open();r.close('example');throws(()=>r.open('example'),/RETIRED/);equal(f.entries.length,0);});
 test('namespace-unknown',()=>{const f=registry(),r=f.open();throws(()=>r.open('missing'),/UNKNOWN_LIBRARY/);throws(()=>r.close('missing'),/UNKNOWN_LIBRARY/);equal(f.entries.length,0);});
 for(const [name,edit,pattern] of [
  ['duplicate-name',c=>c.libraries.push(c.libraries[0]),/NAME/],
  ['duplicate-path',c=>c.libraries.push({...c.libraries[0],path:'/lib/./example.wasm',declaration:{...c.libraries[0].declaration,name:'alias'}}),/DUPLICATE_PATH/],
  ['missing',c=>c.libraries[0].path='/missing',/NOT_FOUND/],
  ['host-path',c=>c.libraries[0].path='file:///etc/passwd',/NOT_FOUND/],
  ['limit',c=>c.maximumBytes=0,/LIMIT/],['limit-overflow',c=>c.maximumBytes=67108865,/LIMIT/],
  ['limit-fraction',c=>c.maximumBytes=0.5,/LIMIT/],['list',c=>c.libraries={},/LIBRARIES/],
  ['name',c=>c.libraries[0].declaration.name='',/NAME/],['name-type',c=>c.libraries[0].declaration.name=7,/NAME/],['imports',c=>c.libraries[0].declaration.imports={},/IMPORTS/]
 ])test('namespace-'+name,()=>{const f=registry({edit});throws(()=>f.open(),pattern);equal(f.entries.length,0);});
 test('namespace-empty',()=>{const f=registry({ns:namespace(new Uint8Array())}),r=f.open();throws(()=>r.open('example'),/SIZE/);equal(f.entries.length,0);});
 test('namespace-size',()=>{const f=registry({maximumBytes:1}),r=f.open();throws(()=>r.open('example'),/SIZE/);equal(f.entries.length,0);throws(()=>r.open('example'),/RETIRED/);});
 test('namespace-digest',()=>{const f=registry({edit:c=>c.libraries[0].declaration.sha256='0'.repeat(64)}),r=f.open();throws(()=>r.open('example'),/DIGEST/);equal(f.entries.length,0);});
 test('namespace-descriptor-close',()=>{const ns=namespace(binaries.library,{handles:1}),inner=ns.session();let closed=0,opened=0;
  const f=registry({ns:{session:()=>({...inner,open(...a){opened++;return inner.open(...a);},close(fd){closed++;return inner.close(fd);}})},maximumBytes:1}),r=f.open();
  throws(()=>r.open('example'),/SIZE/);equal(opened,1);equal(closed,1);const fd=inner.open('example.wasm');inner.close(fd);});
 test('namespace-close-before-entry',()=>{const inner=namespace().session();let handles=0;
  const f=registry({ns:{session:()=>({...inner,open(...a){handles++;return inner.open(...a);},close(fd){handles--;return inner.close(fd);}})},boundary:{enter(){equal(handles,0);},leave(){}}});f.open().open('example');});
 test('namespace-short-reads',()=>{const inner=namespace().session();let reads=0;
  const f=registry({ns:{session:()=>({...inner,pread(fd,p,n){reads++;return inner.pread(fd,p,Math.min(n,7));}})}});equal(f.open().open('example').state,'ready');assert(reads>1,'chunk loop');});
 for(const [name,read] of [['empty',()=>new Uint8Array()],['oversize',(_fd,_p,n)=>new Uint8Array(n+1)],['wrong-type',()=>[1]]])
  test('namespace-read-'+name,()=>{const inner=namespace().session();let closed=0;const f=registry({ns:{session:()=>({...inner,pread:read,close(fd){closed++;return inner.close(fd);}})}});
   throws(()=>f.open().open('example'),/READ/);equal(closed,1);equal(f.entries.length,0);});
 test('namespace-initialization-failure',()=>{const f=registry({imports:{host:{collect(){throw Error('init failure');},observe(){}}}}),r=f.open();
  throws(()=>r.open('example'),/WebAssembly.Exception/);const count=f.entries.length;throws(()=>r.open('example'),/./);equal(f.entries.length,count,'failed initialization never retried');});
 test('namespace-initialization-reentry',()=>{let r;const f=registry({imports:{host:{collect(){throws(()=>r.open('example'),/REENTRY/);throws(()=>r.close('example'),/REENTRY/);},observe(){}}}});r=f.open();equal(r.open('example').state,'ready');});

 function setup({placement=0,maximumTokens=536870911,boxCollect=false,onCollect=()=>{},measure,name='example',maximumNames=1,callback=false,callbackRun}={}){
  const layout=deriveLayout({spaceBytes:65536,freeTarget:0,valueStack:1048576+placement},{bootFunctions:0,runtimeFunctions:0,runtimeRootCells:0,image:[{start:77824,end:77864}]}),tcr=layout.tcr;
  const memory=new WebAssembly.Memory({initial:layout.initialPages,maximum:32769,shared:true}),v=()=>new DataView(memory.buffer);
  const get=p=>v().getUint32(p,true),put=(p,n)=>v().setUint32(p,n,true);
  put(77824,77825);put(77828,77825);put(77832,1850);for(let p=77836;p<77864;p+=4)put(p,77825);
  for(const [o,n] of Object.entries({...layout.tcrWords,8:1,32:2,188:77825}))put(tcr+Number(o),n);
  put(layout.runtimeGlobals,1);for(const group of layout.groups)put(group.slots[0],77825);
  const head=layout.root+40,args=head+16;put(head,layout.root);put(head+4,5);put(head+8,77825);put(head+12,77825);
  put(args,60);put(args+4,0);put(args+8,77825);put(tcr+64,args);put(tcr+128,head);
  const owner=CollectorOwner.create(memory,binaries.collector,sha256(binaries.collector),layout,{measure}),events=[],moves=[];
  const imports={host:{collect(){const r=owner.collectForeign();new Uint8Array(memory.buffer,r.source,r.usedBytes).fill(0xa5);moves.push(r);onCollect();},observe(n){events.push(n);}}};
  const libraries=registry({imports,boundary:owner.foreignBoundary,edit:c=>{c.libraries[0].declaration.name=name;if(maximumNames===2){const row=c.libraries[0];c.libraries.push({...row,path:'second.wasm',declaration:{...row.declaration,name:'second'}});}} ,ns:maximumNames===2?createNamespace({version:1,cwd:'/lib',cclRoot:'/',entries:[{path:'/',kind:'directory'},{path:'/lib',kind:'directory'},...['example','second'].map(n=>({path:'/lib/'+n+'.wasm',kind:'file',bytes:binaries.library,sha256:sha256(binaries.library)}))]}):namespace()}).open();
  const wrapper=boxCollect?{atSafepoint(fn){return owner.atSafepoint(o=>{const r=o.collect();new Uint8Array(memory.buffer,r.source,r.usedBytes).fill(0xa5);return fn(o);});}}:owner;
  const callbackEnv=callback?{table:new WebAssembly.Table({element:'anyfunc',initial:2}),code_registry:layout.registry}:undefined;
  if(callback){
   put(layout.registry,2);put(layout.registry+24,1);put(layout.registry+28,4);put(layout.registry+32,17);put(layout.registry+36,23);
   const entry=new WebAssembly.Instance(new WebAssembly.Module(binaries.bridge),{host:{run:(...a)=>callbackRun(f,...a)}}).exports.entry;
   callbackEnv.table.set(1,entry);
  }
  const service=foreignService({memory,tcr,owner:wrapper,libraries,maximumTokens,callbackEnv});
  const alloc=(header,length)=>{const p=get(tcr+48),size=8*Math.ceil((4+length)/8);assert(p+size<=get(tcr+52),'test heap');new Uint8Array(memory.buffer,p,size).fill(0);put(p,header);put(tcr+48,p+size);return p+6;};
  const str=s=>{const chars=Array.from(s,c=>c.codePointAt(0)),w=alloc(chars.length*256+191,chars.length*4);chars.forEach((c,i)=>put(w-2+i*4,c));return w;};
  const vec=values=>{const w=alloc(values.length*256+250,values.length*4);values.forEach((x,i)=>put(w-2+i*4,x));return w;};
  const bytes=a=>{const w=alloc(a.length*256+199,a.length);new Uint8Array(memory.buffer,w-2,a.length).set(a);return w;};
  const integer=n=>{n=BigInt(n);if(n>=-536870912n&&n<=536870911n)return Number(n)*4>>>0;const limbs=BigInt.asIntN(32,n)===n?1:2,w=alloc(limbs*256+7,limbs*4);
   for(let i=0;i<limbs;i++)put(w-2+i*4,Number(BigInt.asUintN(32,n>>BigInt(i*32))));return w;};
  const float=(n,type)=>{const w=alloc(type==='f32'?271:791,type==='f32'?4:12);if(type==='f32')v().setFloat32(w-2,n,true);else v().setFloat64(w+2,n,true);return w;};
  const request=(op,payload)=>{put(args+4,op*4);put(args+8,payload);return service(args);};
  const call=(lib,name,values=[])=>request(2,vec([lib,str(name),vec(values),NIL]));
  const output=()=>{const w=get(get(args+8)-2+12),n=get(w-6)>>>8;return Array.from({length:n},(_,i)=>get(w-2+4*i));};
  const rawCollector=()=>new WebAssembly.Instance(new WebAssembly.Module(binaries.collector),{env:{memory}}).exports;
  const fn=()=>{const w=alloc(1578,28);[4,NIL,4,NIL,NIL,NIL,0].forEach((v,i)=>put(w-2+i*4,v));return w;};
  const f={owner,memory,tcr,layout,rawCollector,request,call,output,str,vec,bytes,integer,float,get,v,args,events,moves,service,put,fn,callbackEnv,library:()=>request(0,str('example'))};return f;
 }
 const NIL=77825;
 finalizerChecks({test,setup,equal,assert,throws});
 stringChecks({test,setup,equal,assert});
 callbackChecks({test,setup,equal,assert,throws});
 test('service-fixnum-size',()=>{const f=setup(),l=f.library();equal(f.request(3,f.vec([l,NIL])),-4);equal(f.moves.length,1);});
 test('service-fixnum-offset',()=>{const f=setup(),h=f.request(3,f.vec([f.library(),80000]));equal(f.request(5,f.vec([h,NIL])),-4);equal(f.request(4,h),4);});
 test('service-object-tag',()=>{const f=setup(),l=f.library();equal(f.call(l,'echo',[f.vec([4]),0,f.float(1,'f32'),f.float(2,'f64')]),-4);equal(f.moves.length,1);});
 test('service-body-span',()=>{const f=setup(),h=f.request(3,f.vec([f.library(),16])),b=f.bytes([1]);f.put(b-6,0xffffffc7);
  equal(f.request(6,f.vec([h,0,b])),-4);f.put(b-6,455);equal(f.request(4,h),4);});
 test('service-buffer-as-library',()=>{const f=setup(),h=f.request(3,f.vec([f.library(),16]));equal(f.call(h,'releases'),-4);equal(f.request(3,f.vec([h,16])),-4);equal(f.moves.length,2);equal(f.request(4,h),4);});
 test('service-open-capacity',()=>{const f=setup({maximumTokens:1,maximumNames:2});assert(f.library()>0,'first open');equal(f.request(0,f.str('second')),-4);equal(f.events.length,1);});

 for(const placement of [0,65536])test('service-scalars-moving-'+placement,()=>{
  const f=setup({placement,boxCollect:true}),l=f.library();assert(l>0,'open');equal(f.library(),l,'once');
  equal(f.call(l,'echo',[f.integer(-2147483648n),f.integer(-9223372036854775808n),f.float(-0,'f32'),f.float(1.25,'f64')]),0);
  const [a,b,c,d]=f.output();equal(f.get(a-6),263);equal(f.get(a-2)|0,-2147483648);equal(f.get(b-6),519);equal(f.v().getBigInt64(b-2,true),-9223372036854775808n);
  equal(f.get(c-6),271,'f32 header');equal(f.get(d-6),791,'f64 header');equal(f.v().getFloat32(c-2,true),-0);equal(f.v().getFloat64(d+2,true),1.25);assert(f.moves.length===2,'init and call collected');
  equal(f.call(l,'echo',[f.integer(2147483647n),f.integer(9223372036854775807n),f.float(Infinity,'f32'),f.float(NaN,'f64')]),0);
  const [e,g,h,i]=f.output();equal(f.get(e-2),2147483647);equal(f.v().getBigInt64(g-2,true),9223372036854775807n);equal(f.v().getFloat32(h-2,true),Infinity);assert(Number.isNaN(f.v().getFloat64(i+2,true)),'NaN');
 });
 test('service-buffer-moving',()=>{const f=setup(),l=f.library(),h=f.request(3,f.vec([l,64])),r=f.request(5,f.vec([h,16]));
  assert(h>0&&r>0,'opaque tokens');equal(f.request(6,f.vec([h,16,f.bytes([65,195,169,240,159,140,141,0])])),0);
  equal(f.call(l,'run',[r,32,0]),0);equal(f.output()[0],1110*4);
  equal(f.request(7,f.vec([h,16,f.bytes(new Uint8Array(8))])),0);const word=f.get(f.get(f.args+8)-2+8);
  equal(String(new Uint8Array(f.v().buffer,word-2,8)),'66,195,169,240,159,140,141,0');
  equal(f.request(4,h),4);equal(f.request(4,h),0);equal(f.call(l,'run',[r,0,0]),-4);equal(f.events.filter(n=>n===2).length,1);
 });
 for(const [mode,status,releases] of [[1,-12,1],[2,-8,0]])test('service-failure-'+mode,()=>{const f=setup(),l=f.library(),h=f.request(3,f.vec([l,32])),r=f.request(5,f.vec([h,0]));
  equal(f.call(l,'run',[r,0,mode*4]),status);equal(f.request(4,h),releases*4);equal(f.events.filter(n=>n===2).length,releases);});
 test('service-destructor-trap',()=>{const f=setup(),l=f.library(),a=f.request(3,f.vec([l,32])),b=f.request(3,f.vec([l,32]));
  equal(f.call(l,'mode',[4]),0);equal(f.request(4,a),-8);equal(f.request(4,b),0);equal(f.events.filter(n=>n===2).length,1);});
 test('service-close',()=>{const f=setup(),l=f.library(),h=f.request(3,f.vec([l,32]));equal(f.request(1,l),0);equal(f.request(4,h),0);equal(f.library(),-4);equal(f.call(l,'releases'),-4);});
 test('service-token-limit',()=>{const f=setup({maximumTokens:1}),l=f.library();equal(f.request(3,f.vec([l,32])),-4);equal(f.moves.length,1,'refuse before allocator');});
 test('service-range-token-limit',()=>{const f=setup({maximumTokens:2}),l=f.library(),h=f.request(3,f.vec([l,32]));equal(f.request(5,f.vec([h,0])),-4);equal(f.request(4,h),4);});
 for(const maximumTokens of [0,0.5,536870912])test('service-token-configuration-'+maximumTokens,()=>throws(()=>setup({maximumTokens}),/TOKEN_LIMIT/));
 test('service-string-limit',()=>{const name='a'.repeat(4097),f=setup({name});equal(f.request(0,f.str(name)),-4);equal(f.events.length,0);});
 test('service-character-limit',()=>{const f=setup(),word=f.str('a');f.put(word-2,0x110000);equal(f.request(0,word),-4);});
 test('service-object-span',()=>{const f=setup();equal(f.request(0,f.v().byteLength+6),-4);const word=f.str('a');f.put(word-6,0xffffffbf);equal(f.request(0,word),-4);});
 test('service-integer-empty',()=>{const f=setup(),l=f.library(),word=f.vec([]);f.put(word-6,7);equal(f.call(l,'echo',[word,0,f.float(1,'f32'),f.float(2,'f64')]),-4);});
 test('service-reentry',()=>{let f,l,calls=0;f=setup({onCollect(){if(!l)return;const p=f.args+256;f.put(p,60);f.put(p+4,0);f.put(p+8,f.str('example'));equal(f.service(p),-4);calls++;}});l=f.library();equal(f.call(l,'echo',[0,0,f.float(1,'f32'),f.float(2,'f64')]),0);equal(calls,1);});
 test('service-request-bounds',()=>{const f=setup();equal(f.service(f.v().byteLength-8),-4);equal(f.service(-1),-4);equal(f.service(0.5),-4);});
 test('service-integer-limbs',()=>{const f=setup(),l=f.library(),bad=f.vec([0,0,0]);f.put(bad-6,775);
  equal(f.call(l,'echo',[bad,0,f.float(1,'f32'),f.float(2,'f64')]),-4);equal(f.moves.length,1);});
 test('service-float-shape',()=>{const f=setup(),l=f.library(),bad=f.float(1,'f64');f.put(bad-6,527);
  equal(f.call(l,'echo',[0,0,bad,f.float(2,'f64')]),-4);equal(f.moves.length,1);});
 test('service-character',()=>{const f=setup({name:'\ud800'}),bad=f.str('a');f.put(bad-2,0xd800);equal(f.request(0,bad),-4);equal(f.events.length,0);});
 test('service-copy-refusal-preserves',()=>{const f=setup(),l=f.library(),h=f.request(3,f.vec([l,16]));
  equal(f.request(6,f.vec([h,12,f.bytes([65,66])])),-4);equal(f.request(7,f.vec([h,0,f.bytes([5,6,7,8])])),0);
  const word=f.get(f.get(f.args+8)-2+8);equal(String(new Uint8Array(f.v().buffer,word-2,4)),'0,0,0,0');});
 for(const [name,run] of [
  ['operation',f=>f.request(99,NIL)],['library',f=>f.request(0,f.str('absent'))],
  ['token-kind',f=>f.request(4,f.library())],['token-unknown',f=>f.request(4,123456)],
  ['arity',f=>f.call(f.library(),'echo',[])],['export',f=>f.call(f.library(),'absent')],
  ['integer-type',f=>f.call(f.library(),'echo',[NIL,0,f.float(1,'f32'),f.float(2,'f64')])],
  ['integer-range',f=>f.call(f.library(),'echo',[f.integer(2147483648n),0,f.float(1,'f32'),f.float(2,'f64')])],
  ['float-type',f=>f.call(f.library(),'echo',[0,0,f.float(1,'f64'),f.float(2,'f64')])],
  ['string-type',f=>f.request(0,f.vec([]))],['size',f=>f.request(3,f.vec([f.library(),0]))],
  ['request-shape',f=>f.request(3,f.vec([f.library()]))],
  ['request-extra',f=>f.request(3,f.vec([f.library(),16,0]))],
  ['arity-extra',f=>f.call(f.library(),'releases',[0])]
 ])test('service-refuse-'+name,()=>{const f=setup();equal(run(f),-4);equal(f.events.filter(n=>n===2).length,0);});
 assert(rows.length>0,'no selected checks');return {status:'PASS',checks:rows.length,rows};
}
