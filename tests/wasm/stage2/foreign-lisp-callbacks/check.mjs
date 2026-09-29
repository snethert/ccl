const NIL=77825;
export function callbackChecks({test,setup,equal,assert,throws}){
 const register=(f,l,type='integer',fn=f.fn())=>f.request(12,f.vec([l,f.str(type),fn]));
 const good=(f,_fn,n)=>{equal(n,1);const a=f.get(f.get(f.tcr+64));return [f.vec([f.get(a-2)]),1];};
 for(const placement of [0,65536])test('lisp-callback-moving-'+placement,()=>{
  let calls=0;
  const f=setup({placement,callback:true,callbackRun(f,fn,n){calls++;equal(n,1);equal(f.get(f.tcr+32),2);
   const r=f.owner.atSafepoint(o=>o.collect());new Uint8Array(f.memory.buffer,r.source,r.usedBytes).fill(0xa5);
   const a=f.get(f.get(f.tcr+128)+8),word=f.get(a-2);equal(word,168);assert(fn>=r.source,'old function in retired heap');
   return [f.vec([word+4]),1];
  }}),l=f.library(),h=register(f,l);assert(h>0,'registered');
  equal(f.call(l,'cb-twice',[h,168]),0);equal(f.output()[0],172);equal(calls,2);equal(f.call(l,'cb-call',[h,168]),0);equal(calls,3);
  equal(f.request(13,h),4);equal(f.request(13,h),0);equal(f.call(l,'cb-call',[h,168]),-4);
  equal(f.call(l,'cb-saved',[168]),0);equal(f.output()[0],-4>>>0);
 });
 test('lisp-callback-boxing-move',()=>{
  let before,calls=0;const f=setup({callback:true,callbackRun(f,fn,n){calls++;equal(n,1);assert(fn!==before,'callable reloaded');equal(f.get(fn-6),1578);
   const a=f.get(f.get(f.tcr+64));return [f.vec([f.get(a-2)]),1];}}),l=f.library();before=f.fn();const h=register(f,l,'integer',before);
  f.put(f.args+4,8);f.put(f.args+8,f.vec([l,f.str('cb-call'),f.vec([h,168]),NIL]));
  for(let p=f.get(f.tcr+48);p<f.get(f.tcr+52);p+=8){f.put(p,250);f.put(p+4,0);}
  f.put(f.tcr+48,f.get(f.tcr+52));const count=f.owner.collectionCount;
  equal(f.service(f.args),0);equal(calls,1);equal(f.output()[0],168);assert(f.owner.collectionCount>=count+2,'boxing and foreign collections');
 });
 test('lisp-callback-scalars',()=>{
  const f=setup({callback:true,callbackRun(f){const a=f.get(f.get(f.tcr+64));return [a,1];}}),l=f.library(),h=register(f,l,'scalars');
  equal(f.call(l,'cb-scalars',[h,f.integer(-2147483648),f.integer(-9223372036854775808n),f.float(-0,'f32'),f.float(1.25,'f64')]),0);
  const [a,b,c,d]=f.output();equal(f.get(a-2)|0,-2147483648);equal(f.v().getBigInt64(b-2,true),-9223372036854775808n);equal(f.v().getFloat32(c-2,true),-0);equal(f.v().getFloat64(d+2,true),1.25);
 });
 test('lisp-callback-void',()=>{const f=setup({callback:true,callbackRun:f=>[f.vec([]),1]}),l=f.library(),h=register(f,l,'void');equal(f.call(l,'cb-void',[h]),0);equal(f.output().length,0);});
 for(const [name,result] of [['failure',()=>[NIL,1]],['count',f=>[f.vec([4]),0]],['arity',f=>[f.vec([4,8]),1]],['type',f=>[f.vec([NIL]),1]],['object',()=>[0,1]]])
  test('lisp-callback-result-'+name,()=>{let calls=0;const f=setup({callback:true,callbackRun(f){calls++;return result(f);}}),l=f.library(),h=register(f,l);
   equal(f.call(l,'cb-twice',[h,4]),-16);equal(calls,1);equal(f.get(f.tcr+32),2);equal(f.call(l,'cb-after'),0);equal(f.output()[0],4);equal(f.request(13,h),4);});
 test('lisp-callback-escape',()=>{const f=setup({callback:true,callbackRun(){throw new WebAssembly.Exception(new WebAssembly.Tag({parameters:['i32']}),[77825]);}}),l=f.library(),h=register(f,l);
  throws(()=>f.call(l,'cb-call',[h,4]),/AggregateError/);equal(f.call(l,'cb-call',[h,4]),-4);});
 test('lisp-callback-reentry',()=>{const f=setup({callback:true,callbackRun(f){equal(f.service(f.args),-4);return [f.vec([4]),1];}}),l=f.library(),h=register(f,l);equal(f.call(l,'cb-call',[h,4]),0);});
 for(const [name,change] of [
  ['function',(_f)=>NIL],['interior',(f,w)=>w+8],['header',(f,w)=>{f.put(w-6,1834);return w;}],
  ['id-zero',(f,w)=>{f.put(w-2,0);return w;}],['id-limit',(f,w)=>{f.put(w-2,8);return w;}],
  ['generation',(f,w)=>{f.put(w+6,8);return w;}],['row-kind',(f,w)=>{f.put(f.layout.registry+32,0);return w;}],
  ['row-flags',(f,w)=>{f.put(f.layout.registry+36,0);return w;}],['slot',(f,w)=>{f.put(f.layout.registry+24,2);return w;}],
  ['empty-slot',(f,w)=>{f.callbackEnv.table.set(1,null);return w;}]
 ])test('lisp-callback-refuse-'+name,()=>{const f=setup({callback:true,callbackRun:good}),l=f.library(),w=change(f,f.fn());
   equal(register(f,l,'integer',w),-4);equal(f.moves.length,1);});
 test('lisp-callback-stack',()=>{let calls=0;const f=setup({callback:true,callbackRun(){calls++;return [NIL,1];}}),l=f.library(),h=register(f,l);
  const old=f.get(f.tcr+124);f.put(f.tcr+124,f.get(f.tcr+72)-64);
  equal(f.call(l,'cb-call',[h,0]),-16);equal(calls,0);equal(f.get(f.tcr+124),f.get(f.tcr+72)-64);f.put(f.tcr+124,old);});
 test('lisp-callback-registration-retry',()=>{const f=setup({callback:true,callbackRun:good}),l=f.library();equal(register(f,l,'missing'),-4);
  const h=register(f,l);equal(h,8);equal(f.call(l,'cb-call',[h,4]),0);equal(f.output()[0],4);});
 for(const [name,edit] of [
  ['table',f=>{f.callbackEnv.table={};}],['registry-negative',f=>{f.callbackEnv.code_registry=-1;}],
  ['registry-fraction',f=>{f.callbackEnv.code_registry+=0.5;}],['registry-span',f=>{f.callbackEnv.code_registry=f.memory.buffer.byteLength;}],
  ['row-span',f=>{f.callbackEnv.code_registry=f.memory.buffer.byteLength-8;f.put(f.callbackEnv.code_registry,100);}]
 ])test('lisp-callback-env-'+name,()=>{const f=setup({callback:true}),l=f.library();edit(f);equal(register(f,l),-4);equal(f.moves.length,1);});
 test('lisp-callback-env',()=>{const f=setup(),l=f.library();equal(register(f,l),-4);});
 for(const n of [2,4])test('lisp-callback-request-'+n,()=>{const f=setup({callback:true}),l=f.library(),a=[l,f.str('integer'),f.fn(),NIL];equal(f.request(12,f.vec(a.slice(0,n))),-4);});
 test('lisp-callback-type',()=>{const f=setup({callback:true}),l=f.library();equal(register(f,l,'missing'),-4);});
 test('lisp-callback-capacity',()=>{const f=setup({callback:true,maximumTokens:1}),l=f.library();equal(register(f,l),-4);equal(f.moves.length,1);});
 test('lisp-callback-token-kind',()=>{const f=setup({callback:true}),l=f.library();equal(f.request(13,l),-4);equal(f.call(l,'cb-call',[l,0]),-4);});
 test('lisp-callback-affinity',()=>{const f=setup({callback:true,callbackRun:good,maximumNames:2}),l=f.library(),h=register(f,l),other=f.request(0,f.str('second'));
  equal(f.call(other,'cb-call',[h,0]),-4);equal(f.moves.length,2);});
 test('lisp-callback-close',()=>{const f=setup({callback:true,callbackRun:good}),l=f.library(),h=register(f,l);equal(f.request(1,l),0);equal(f.request(13,h),0);equal(f.call(l,'cb-call',[h,0]),-4);});
}
