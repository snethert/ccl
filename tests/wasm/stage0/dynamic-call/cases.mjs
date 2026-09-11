import assert from 'node:assert/strict';
import {ABIHarness} from './harness.mjs';

const describe=v=>v===null?'NIL':typeof v==='object'?{car:v.car}:v;
const payload=v=>v===null?0:typeof v==='object'?v.car:v;
function expectedFold(args,index,values) {
  const code=[10,11,12,20,21,30,31,40][index],env=500+index*11;
  const sum=args.reduce((a,v,i)=>(a+Math.imul(payload(v),(i+1)))|0,(index===1?2000:1000)+env);
  return [((sum*4)|0)>>2,{car:code},args.length?describe(args[0]):'NIL',args.length?describe(args.at(-1)):'NIL',{car:env},args.length].slice(0,values);
}
function verify(h,r,expected,{args,code=10,condition=0,cleanup=1}={}) {
  assert.equal(r.snapshot.state.error,condition,'unexpected Lisp condition');
  assert.equal(r.snapshot.state.cleanup_count,cleanup,'cleanup count');
  assert.deepEqual(r.values.map(v=>h.describe(v)),expected,'complete result sequence');
  assert.deepEqual(r.result,[condition?-1:expected.length?(r.values[0]|0):65,expected.length],'ABI returned first value/count');
  for(const p of h.packets.filter(p=>p.phase===3)) {
    assert.equal(p.vsp,h.baseline.vsp,'callee VSP was not restored before caller cleanup');
    assert.equal(p.roots,h.baseline.roots,'callee roots were not restored before caller cleanup');assert.equal(p.frames.length,0);
  }
  if(args) {
    const p=h.packets.find(p=>p.phase===4&&p.frames[0]?.header[4]===code*4);
    assert.ok(p,'callee entry did not execute');
    const got=p.frames[0].args.slice(1).map(([,kind,value])=>kind===0?'NIL':kind===1?(value|0)>>2:{car:(value|0)>>2});
    assert.deepEqual(got,args.map(describe),'ordered arguments at emitted entry');
    assert.equal(p.frames[0].header[12],args.length);
  }
  return h.evidence(r);
}
async function fold(h,args,{anchor=0,values=6,path=0,mode=0,policy=3,nested=false,nonlocal=false}={}) {
  h.prepare(args,{values,mode,policy});const r=await h.run(anchor,args.length,{path,nested,nonlocal});
  if(nonlocal)return verify(h,r,[],{condition:h.map.workers[0].tcr.start});
  const evidence=verify(h,r,expectedFold(args,anchor,values),{args,code:h.build.schema.entries[anchor].code});
  if(mode&1)assert.ok(h.collections.length,'suspension did not collect');
  if(mode&16) {
    const before=h.packets.find(p=>p.phase===1),after=h.packets.find(p=>p.phase===2);
    assert.ok(before&&after);assert.notEqual(before.frames[0].args[0][0],after.frames[0].args[0][0],'ephemeral self did not move');
  }
  return evidence;
}
const long=()=>Array.from({length:32},(_,i)=>i===3?{car:73}:i===31?{car:211}:i-7);
export const positives=[
  {name:'independent-cons-layout-and-graphs',id:'S0-LL04-a',run:layoutCheck},
  {name:'ownership-rejected-before-publication',id:'S0-LL13-a',run:async h=>{
    const results=[];
    for(const option of ['mapOverlap','undersizedStack']) {
      const bad=new ABIHarness(h.build,h.name,{[option]:true});
      try {await assert.rejects(()=>bad.reset(),/overlap|undersized C stack/);assert.equal(bad.main,undefined);assert.equal(bad.actors.length,0);results.push({option,publication:'NOT_REACHED'});}
      finally {await bad.close();}
    }
    return {ownership:h.map,controls:results};
  }},
  ...Array.from({length:7},(_,n)=>({name:'ordered-'+n,id:'S0-LL05-a',run:h=>fold(h,Array.from({length:n},(_,i)=>(i+1)*3-7))})),
  {name:'long-overflow',id:'S0-LL05-a',run:h=>fold(h,long())},
  {name:'direct-call',id:'S0-LL05-a',run:h=>fold(h,long(),{path:1})},
  {name:'runtime-adapter-tail-transfer',id:'S0-LL05-b',run:h=>fold(h,long(),{path:2})},
  {name:'zero-values',id:'S0-LL05-a',run:h=>fold(h,[null,-7,0,{car:33}],{values:0})},
  {name:'one-value',id:'S0-LL05-a',run:h=>fold(h,[1,2,3,4],{values:1})},
  {name:'moved-registers-overflow-and-ephemeral-self',id:'S0-LL05-a',run:h=>fold(h,long(),{mode:17})},
  {name:'lower-debug-policy',id:'S0-LL05-a',run:h=>fold(h,[1,{car:73},3,4],{mode:1,policy:1})},
  {name:'reentrant-C-callback',id:'S0-LL05-a',run:h=>fold(h,[1,{car:31},3,4,5,6],{mode:1,nested:true})},
  {name:'C-nonlocal-restoration-and-idle-collection',id:'S0-LL05-d',run:h=>fold(h,[1,{car:31},3,4,5,6],{mode:1,nonlocal:true})},
  {name:'cleanup-throws',id:'S0-LL05-d',run:async h=>{h.prepare([1,2],{mode:8});return verify(h,await h.run(0,2),[],{condition:919});}},
  {name:'exact-arity',id:'S0-LL05-a',run:h=>fold(h,[7,11],{anchor:2})},
  {name:'arity-condition',id:'S0-LL05-a',run:async h=>{h.prepare([7]);return verify(h,await h.run(2,1),[],{condition:917});}},
  {name:'designator-condition',id:'S0-LL05-a',run:async h=>{h.prepare([]);return verify(h,await h.run(99,0),[],{condition:916});}},
  {name:'argument-capacity-condition',id:'S0-LL05-a',run:async h=>{h.prepare([],{count:33});return verify(h,await h.run(0,33),[],{condition:911});}},
  ...[['explicit-stack-capacity-condition','stack_limit',914],['frame-generation-exhaustion','frame_serial',915]].map(([name,field,condition])=>({name,id:'S0-LL05-a',run:async h=>{
    h.prepare([]);h.setField(0,field,field==='stack_limit'?h.field(0,'vsp')+128:0xffffffff);return verify(h,await h.run(0,0),[],{condition});
  }})),
  {name:'lazy-arity-condition',id:'S0-LL05-c',options:{lazyCodes:[12]},run:async h=>{h.prepare([7]);return verify(h,await h.run(2,1),[],{condition:917});}},
  ...[0,1].map(values=>({name:'tail-chain-values-'+values,id:'S0-LL05-d',run:async h=>{
    h.prepare([h.build.schema.tail_iterations,2],{values});const r=await h.run(5,2);const e=verify(h,r,expectedFold([0,2],5,values));
    assert.equal(r.snapshot.state.tail_count,h.build.schema.tail_iterations);assert.ok(r.snapshot.state.peak_vsp-h.baseline.vsp<=640);assert.ok(r.snapshot.state.peak_roots<=10);return e;
  }})),
  ...[2,3,4,6,32].map(n=>({name:'optional-rest-'+n,id:'S0-LL05-a',run:async h=>{
    const args=Array.from({length:n},(_,i)=>i===5?{car:83}:i+1);h.prepare(args,{fillHeap:n===32});const r=await h.run(3,n);
    const expected=[1,2,n>2?3:99,n>3?4:77,r.values[4]===65?'NIL':h.describe(r.values[4]),(n>2?1:0)+(n>3?2:0)];
    const e=verify(h,r,expected,{args,code:20});assert.deepEqual(h.list(r.values[4]),args.slice(4).map(describe),'rest list sequence');return e;
  }})),
  ...[
    ['keyword-defaults',[],[99,77,'NIL','NIL','NIL',0],0],
    ['keyword-order-and-duplicate',[1001,17,1000,19,1000,23],[19,17,1,1,'NIL',6],0],
    ['keyword-allow-other',[1003,77,1002,1,1000,31],[31,77,1,'NIL',1,6],0],
    ['keyword-unknown',[1003,77],[],918],['keyword-odd',[1000],[],918],
    ['keyword-leftmost-allow-other',[1002,null,1002,1,1003,77],[],918]
  ].map(([name,args,expected,condition])=>({name,id:'S0-LL05-a',run:async h=>{h.prepare(args);return verify(h,await h.run(4,args.length),expected,{args:condition?null:args,code:21,condition});}})),
  ...[0,6,30].map(n=>({name:'apply-'+n,id:'S0-LL05-a',run:async h=>{
    const prefix=n===30?[101,103]:[],suffix=Array.from({length:n},(_,i)=>i===3?{car:81}:i+7),args=[...prefix,...suffix];
    h.prepare(prefix,{apply:{values:suffix}});const r=await h.run(0,prefix.length,{path:4});return verify(h,r,expectedFold(args,0,6),{args});
  }})),
  {name:'apply-improper-condition',id:'S0-LL05-a',run:async h=>{h.prepare([],{apply:{values:[1,2],improper:3}});return verify(h,await h.run(0,0,{path:4}),[],{condition:921});}},
  {name:'apply-cycle-condition',id:'S0-LL05-a',run:async h=>{h.prepare([],{apply:{values:[1,2],cycle:true}});return verify(h,await h.run(0,0,{path:4}),[],{condition:911});}},
  {name:'nested-multiple-value-call',id:'S0-LL05-a',run:async h=>{
    const args=[{car:37},-7,0,13,19,23];h.prepare(args,{mode:1});const r=await h.run(7,args.length);
    const expected=[...expectedFold(args,0,6).slice(0,3),...expectedFold(args,1,6).slice(0,3)];
    const e=verify(h,r,expected,{args,code:40});assert.equal(r.snapshot.state.effects,12,'nested side-effect order');assert.ok(h.collections.length>=2);return e;
  }},
  {name:'matching-mixed-table-signatures',id:'S0-LL05-b',run:async h=>{const r=await h.actors[0].simple('probe');assert.equal(r.result,3.5);assert.equal(r.snapshot.entered,1);return h.evidence(r);}},
  {name:'lazy-generic-long-overflow',id:'S0-LL05-c',options:{lazyCodes:[10]},run:h=>fold(h,long())},
  {name:'lazy-variable-arity',id:'S0-LL05-c',options:{lazyCodes:[20]},run:async h=>{h.prepare([1,2,3,4,5,6]);const r=await h.run(3,6);const e=verify(h,r,[1,2,3,4,h.describe(r.values[4]),3],{args:[1,2,3,4,5,6],code:20});assert.deepEqual(h.list(r.values[4]),[5,6]);return e;}},
  {name:'lazy-runtime-adapter',id:'S0-LL05-c',options:{lazyCodes:[10]},run:h=>fold(h,long(),{path:2})},
  {name:'lazy-exact-arity',id:'S0-LL05-c',options:{lazyCodes:[12]},run:h=>fold(h,[{car:31},7],{anchor:2})},
  {name:'long-growing-shrinking-tail-chain',id:'S0-LL05-d',run:async h=>{
    h.prepare([h.build.schema.tail_iterations,2]);const r=await h.run(5,2);const e=verify(h,r,expectedFold([0,2],5,6));
    assert.equal(r.snapshot.state.tail_count,h.build.schema.tail_iterations,'tail iterations');assert.equal(r.snapshot.state.entry_count,h.build.schema.tail_iterations+1);
    assert.ok(r.snapshot.state.peak_vsp-h.baseline.vsp<=640,'tail stack grew');assert.ok(r.snapshot.state.peak_roots<=10,'tail roots grew');
    assert.ok(h.word(h.global('world_completed'))>=50,'tail chain never collected');return e;
  }},
  {name:'code-version-and-symbol-redefinition',id:'S0-LL21-b',run:async h=>{
    h.prepare([7,11]);const first=await h.run(-1,2);verify(h,first,expectedFold([7,11],0,6));
    await h.actors[0].simple('redefine');h.packets=[];h.prepare([7,11]);const second=await h.run(-1,2);verify(h,second,expectedFold([7,11],1,6),{cleanup:2});
    h.packets=[];h.prepare([7,11]);const old=await h.run(0,2);verify(h,old,expectedFold([7,11],0,6),{cleanup:3});return {...h.evidence(old),first,second};
  }},
  {name:'late-worker-first-call-installation',id:'S0-LL21-b',options:{lazyCodes:[10]},run:async h=>{
    h.prepare([7,{car:43}]);const first=await h.run(0,2);verify(h,first,expectedFold([7,{car:43}],0,6));
    await h.late();h.packets=[];h.prepare([11,{car:47}],{id:2});const last=await h.run(0,2,{id:2});verify(h,last,expectedFold([11,{car:47}],0,6));return {...h.evidence(last),first};
  }}
];

export const controls=[
  {name:'lost-tail-binding-extent',mutant:{loseBinding:true},test:'long-growing-shrinking-tail-chain',failureCode:908},
  {name:'swapped-arguments',mutant:{swapArgs:true},test:'ordered-6',pattern:/complete result sequence|ordered arguments/},
  {name:'lost-overflow',mutant:{dropOverflow:true},test:'long-overflow',pattern:/complete result sequence|ordered arguments/},
  {name:'wrong-self',mutant:{wrongSelf:true},test:'ordered-6',pattern:/complete result sequence/},
  {name:'lost-values',mutant:{dropValues:true},test:'ordered-6',pattern:/complete result sequence/},
  {name:'wrong-value-count',mutant:{wrongCount:true},test:'ordered-6',pattern:/complete result sequence|ABI returned/},
  {name:'zero-not-nil',mutant:{zeroNotNil:true},test:'zero-values',pattern:/ABI returned/},
  {name:'omitted-argument-roots',mutant:{omitRoots:true},test:'moved-registers-overflow-and-ephemeral-self',failureCode:906},
  {name:'cached-moved-self',mutant:{staleRoot:true},test:'moved-registers-overflow-and-ephemeral-self',failureCode:102},
  {name:'cached-lazy-stub-self',mutant:{staleStub:true},test:'lazy-generic-long-overflow',failureCode:102},
  {name:'omitted-VSP-restoration',mutant:{omitVspRestore:true},test:'ordered-6',pattern:/callee VSP/},
  {name:'omitted-root-restoration',mutant:{omitRootRestore:true},test:'ordered-6',pattern:/callee roots/},
  {name:'lost-pending-multiple-values',mutant:{losePreservedValues:true},test:'nested-multiple-value-call',pattern:/complete result sequence/},
  {name:'omitted-cleanup',mutant:{omitCleanup:true},test:'ordered-6',pattern:/cleanup count/},
  {name:'tail-frame-leak',mutant:{tailLeak:true},test:'long-growing-shrinking-tail-chain',pattern:/unexpected Lisp condition/},
  {name:'wrong-signature-before-entry',options:{wrongSignature:true},test:'ordered-6',pattern:/signature mismatch|null function/,beforeEntry:true},
  {name:'same-signature-wrong-role',options:{wrongRole:true},test:'ordered-6',pattern:/ROLE_MISMATCH/},
  {name:'bypassed-role-validation',options:{wrongRole:true,bypassRole:true},test:'ordered-6',pattern:/complete result sequence/},
  {name:'null-uninstalled-slot',options:{nullStub:true},test:'lazy-generic-long-overflow',pattern:/null function|signature mismatch/},
  {name:'missing-installation-module',options:{missingModule:true},test:'lazy-generic-long-overflow',pattern:/MISSING_CODE_MODULE/},
  {name:'installation-digest-mismatch',options:{badHash:true},test:'lazy-generic-long-overflow',pattern:/CODE_DIGEST_MISMATCH/},
  {name:'installation-profile-mismatch',mutant:{profile:true},test:'lazy-generic-long-overflow',pattern:/MEMORY_PROFILE_MISMATCH/},
  {name:'installation-start-function',mutant:{unauthorizedStart:true},test:'lazy-generic-long-overflow',pattern:/UNAUTHORIZED_INITIALIZATION/},
  {name:'old-version-replaced',options:{oldVersionAlias:true},test:'ordered-6',pattern:/complete result sequence|unknown debug source site/},
  {name:'duplicate-result-root-ownership',mutant:{duplicateResultRoot:true},test:'late-worker-first-call-installation',failureCode:201},
  {name:'stale-owned-result-count',mutant:{staleResultCount:true},test:'nested-multiple-value-call',failureCode:102},
  {name:'one-sided-emitted-cons-swap',mutant:{swapCons:true},test:'independent-cons-layout-and-graphs',pattern:/independent emitted cons oracle/}
];

export async function executeCase(build,candidate,test,control) {
  const h=new ABIHarness(build,candidate,{...test.options,...control?.options});let evidence,error,rejected=false;
  try {await h.reset();evidence=await test.run(h);}
  catch(e) {
    error=e.stack;
    if(control) {
      if(control.failureCode)rejected=!!h.words&&h.word(h.global('failure_code'))===control.failureCode;
      else rejected=control.pattern.test(error)&&!/deadline|timed.out/.test(error);
      if(control.beforeEntry)rejected&&=h.failureRecord?.snapshot?.state.entry_count===0&&h.failureRecord?.snapshot?.entered===0;
    }
  } finally {await h.close();}
  const status=control?(rejected?'REJECTED':'FAIL'):error?'FAIL':'PASS';
  return {name:control?.name||test.name,id:test.id,candidate,status,negative:!!control,error,
    evidence:evidence||{failure:h.failureRecord,packets:h.packets,io:h.io,collections:h.collections,failure_code:h.words&&h.word(h.global('failure_code'))}};
}

async function layoutCheck(h) {
  const p=h.allocate(44,(-28)>>>0),inner=h.allocate(76,65),nested=h.allocate(inner,65),left=h.allocate(inner,p),right=h.allocate(inner,left);
  const cycleA=h.allocate(92,65),cycleB=h.allocate(108,cycleA);h.put(cycleA-1,cycleB);
  const fixtures=[[p,44,(-28)>>>0],[nested,inner,65],[left,inner,p],[right,inner,left],[cycleA,92,cycleB],[cycleB,108,cycleA]];
  const results=[];
  for(const [pointer,car,cdr] of fixtures) {
    assert.deepEqual([h.word(pointer+3),h.word(pointer-1)],[car,cdr]);
    const c=await h.actors[0].simple('layout',[pointer,0]),wasm=await h.actors[0].simple('wasm_layout',[pointer,0]);
    assert.deepEqual(c.result.map(v=>v>>>0),[car,cdr,65,65],'independent C cons oracle');
    assert.deepEqual(wasm.result.map(v=>v>>>0),[car,cdr,65,65],'independent emitted cons oracle');
    results.push({pointer,car,cdr,C:c.result,Wasm:wasm.result});
  }
  for(const kind of ['layout','wasm_layout']) {
    h.put(p-1,(-28)>>>0);h.put(p+3,44);await h.actors[0].simple(kind,[p,1]);
    assert.deepEqual([h.word(p-1),h.word(p+3)],[(-36)>>>0,124],'independent cons mutation oracle');
  }
  return {status:'PASS',fixtures:results,mutation:[h.word(p-1),h.word(p+3)],ownership:h.map};
}
