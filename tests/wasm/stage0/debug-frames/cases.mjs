import assert from 'node:assert/strict';
import {FrameHarness} from './harness.mjs';
const pause=(code,occurrence=1)=>({code,occurrence});

async function activation(h,{count=6,policy=3,nested=false,exception=false,version=1,verify=true}={}) {
  const E=h.schema.events,a=h.actors[0],collector=h.actors[1];
  h.expected={count,policy,version,tsp:h.field(0,'tsp'),csp:h.field(0,'csp')};const before=h.prepareValues(0,count);
  h.setField(0,'mode',nested?1:exception?2:0);
  const checkpoints=Object.fromEntries(['root_head','binding_depth','vsp','tsp','csp','mv_base','mv_owner_top',
    'handler_cookie','binding_cookie','active_request','frame_head','frame_cursor'].map(f=>[f,h.field(0,f)]));
  const startGC=h.word(h.global('world_completed'));
  const job=a.run(version===1?'outer':'new_outer',[count,policy,nested&&exception?1:0],
    nested?[pause(E.WAITING),pause(E.WAITING,2)]:[pause(E.WAITING)],'program');
  const primary=await h.ioRequest();await a.at(E.WAITING);
  const headerBefore=h.frameHeaderOracle([42,41]);
  await collector.run('collect_and_park');
  const headerMoved=h.frameHeaderOracle([42,41]);
  for(let i=0;i<headerBefore.length;i++) {
    assert.notEqual(headerBefore[i].payload_words[2],headerMoved[i].payload_words[2],'emitted self root did not move');
    assert.equal(headerBefore[i].payload_words[8],headerMoved[i].payload_words[8],'raw slot treated as a tagged root');
  }
  assert.equal(h.word(before.root-1),0xdeadbeef,'old heap was not poisoned');
  let secondary;
  if(nested) {
    h.interrupt(primary);a.resume();secondary=await h.ioRequest();await a.at(E.WAITING,2);
    h.frameHeaderOracle([43,42,41]);
    await collector.run('collect_and_park');h.immutableReplies();
    h.complete(secondary);a.resume();
    if(!exception)h.complete(primary);
  } else {
    if(exception)h.interrupt(primary);else h.complete(primary);
    a.resume();
  }
  const done=await job;h.drainReplies();
  assert.deepEqual(done.result,[exception?-1:count?4:65,count]);
  for(const [field,value] of Object.entries(checkpoints))
    assert.equal(done.snapshot[field],value,'frame head was not restored: '+field);
  assert.equal(done.snapshot.c_sp,h.map.workers[0].stack.end,'C stack was not restored');
  assert.equal(done.snapshot.state,h.schema.states.PARKED,'idle emitted entry is not parked');
  assert.equal(done.snapshot.admitted,0);
  assert.equal(done.snapshot.cleanup,exception?1:0);
  assert.equal(h.word(h.global('world_completed')),startGC+(nested?2:1));
  if(count) assert.deepEqual(done.snapshot.values,[4,-28>>>0,h.word(h.field(0,'root_slot')),
    h.word(h.word(h.field(0,'root_slot'))-1),0,2147483644],'nonlocal/normal result region changed');
  if(exception) {
    assert.equal(h.requestSnapshot(primary).active,1,'exception abandoned a live descriptor early');
    assert.equal(h.requestSnapshot(primary).cancel_requested,1);
    h.complete(primary,{cancel:true});
    await collector.run('collect_and_park'); // Idle exceptional handoff must remain collectible.
  }
  const old=h.replies.find(r=>r.kind===1&&r.phase===1).frames.at(-1);
  assert.equal((await a.run('debug_handle_query',[old.address,old.generation,h.field(0,'lifetime')])).result,0,'popped frame handle remained valid');
  assert.equal((await a.run('debug_read_capture')).result,800,'permanently rooted shared cell did not survive return/collection');
  if(verify)h.verifyReplies();
  return {before:headerBefore,after_moving_gc:headerMoved,old_handle:{address:old.address,generation:old.generation,lifetime:h.field(0,'lifetime')},
    primary:h.ticketRecord(primary),secondary:secondary?h.ticketRecord(secondary):null,final:done.snapshot};
}
export async function ordinary(h,options={}) {await h.reset();return activation(h,options);}
export async function reuse(h,{newVersion=false,wrongLifetime=false}={}) {
  await h.reset();const first=await activation(h);
  const handle=first.old_handle;
  await h.actors[0].run('set_handle',[handle.address,wrongLifetime?h.field(0,'frame_serial')+1:handle.generation,
    handle.lifetime+(wrongLifetime?1:0)],[],'program');
  const second=await activation(h,{version:newVersion?2:1});
  const replies=h.replies.filter(r=>r.kind===2);assert.equal(replies.length,1);assert.equal(replies[0].valid,0,'stale frame handle was accepted after storage reuse');
  let retainedOld;
  if(newVersion) {
    retainedOld=await activation(h,{version:1});
    const outer=h.replies.filter(r=>r.kind===1&&r.phase===5).map(r=>r.frames[0]);
    assert.deepEqual(outer.map(f=>[f.code_id/4,f.version,f.site]),[[41,1,4102],[41,2,4112],[41,1,4102]],'superseded debug metadata was relabeled');
  }
  return {first,second,retained_old:retainedOld,handle_replies:h.replies.filter(r=>r.kind===2)};
}
async function fullFrameStack(h) {
  await h.reset();h.expected={count:6,policy:3,version:1,tsp:h.field(0,'tsp'),csp:h.field(0,'csp')};h.prepareValues(0,6);
  const fields=['root_head','frame_head','frame_cursor','vsp','tsp','csp','binding_depth','mv_base','mv_owner_top','active_request','binding_cookie','handler_cookie'];
  const before=Object.fromEntries(fields.map(f=>[f,h.field(0,f)])),a=h.actors[0],E=h.schema.events;
  const job=a.run('deep',[],[pause(E.WAITING)],'program');
  const request=await h.ioRequest();await a.at(E.WAITING);
  const headers=h.frameHeaderOracle(Array(8).fill(41));
  await h.actors[1].run('collect_and_park');h.frameHeaderOracle(Array(8).fill(41));
  h.complete(request);a.resume();const done=await job;h.drainReplies();h.verifyReplies();
  assert.equal(done.result,0);for(const f of fields)assert.equal(done.snapshot[f],before[f],'full frame stack restoration: '+f);
  assert.equal(done.snapshot.state,h.schema.states.PARKED);assert.equal(done.snapshot.admitted,0);
  assert.equal(done.snapshot.c_sp,h.map.workers[0].stack.end);
  assert.equal(h.replies.filter(r=>r.kind===1).length,2);
  assert.ok(h.replies.every(r=>r.bytes.length/2>2048),'maximum frame reply did not exceed the old buffer size');
  return {headers,final:done.snapshot};
}
export const positives=[
  {name:'full-frame-capacity-through-moving-gc',fn:fullFrameStack},
  {name:'zero-values-through-moving-suspension',fn:h=>ordinary(h,{count:0})},
  {name:'six-values-through-moving-suspension',fn:ordinary},
  {name:'nested-debugger-zero-values',fn:h=>ordinary(h,{count:0,nested:true})},
  {name:'nested-debugger-six-values',fn:h=>ordinary(h,{nested:true})},
  {name:'explicit-unavailable-value-policy',fn:h=>ordinary(h,{policy:1})},
  {name:'nonlocal-frame-restoration',fn:h=>ordinary(h,{exception:true})},
  {name:'nested-debugger-nonlocal-restoration',fn:h=>ordinary(h,{nested:true,exception:true})},
  {name:'generation-rejects-reused-frame-handle',fn:reuse},
  {name:'thread-lifetime-rejects-live-frame-handle',fn:h=>reuse(h,{wrongLifetime:true})},
  {name:'live-and-superseded-code-metadata',fn:h=>reuse(h,{newVersion:true})}
];
export const negatives=[
  {name:'reject-live-frame-handle',options:{mutant:'rejectLiveHandle'},fn:ordinary,pattern:/live frame handle was rejected/},
  {name:'stale-debug-root-slot',options:{mutant:'staleSlot'},fn:ordinary,code:102},
  {name:'reused-frame-generation',options:{mutant:'reusedGeneration'},fn:reuse,pattern:/stale frame handle was accepted/},
  {name:'wrong-source-site',options:{programMutant:'wrongSite'},fn:ordinary,code:704},
  {name:'wrong-code-version',options:{programMutant:'wrongVersion'},fn:ordinary,code:704},
  {name:'fabricated-unavailable-value',options:{mutant:'fabricatedValue'},fn:h=>ordinary(h,{policy:1}),pattern:/unavailable value was fabricated/},
  {name:'shadowed-name-as-lexical-identity',options:{mutant:'wrongLexicalId'},fn:ordinary,pattern:/shadowed lexical identity changed/},
  {name:'omitted-frame-restoration',options:{programMutant:'omitRestore'},fn:ordinary,pattern:/frame head was not restored/},
  {name:'omitted-root-publication',options:{mutant:'missingRoot'},fn:ordinary,code:705},
  {name:'frame-generation-exhaustion',fn:async h=>{await h.reset();h.setField(0,'frame_serial',0xffffffff);return activation(h);},code:703},
  {name:'explicit-frame-stack-overflow',fn:async h=>{await h.reset();h.setField(0,'frame_limit',h.map.workers[0].frames.start+160);return activation(h);},code:701}
];
export async function execute(build,write) {
  const results=[];
  for(const test of [...positives,...negatives]) {
    const h=new FrameHarness(build,test.options);const negative=negatives.includes(test);let status='PASS',detail,error;
    try {detail=await test.fn(h);if(negative)throw Error('negative control unexpectedly passed');}
    catch(e) {
      error=e.stack;
      status=negative&&((test.code&&h.failureSnapshot?.globals.failure_code===test.code)||(test.pattern&&test.pattern.test(e.message)))?'REJECTED':'FAIL';
    } finally {await h.close();}
    const record=h.evidence({name:test.name,status,negative,detail,error,first_failure:h.failureSnapshot,
      all_workers_terminated:h.actors.filter(Boolean).every(a=>a.closed)});
    write(test.name,record,negative);results.push(record);console.log(status,test.name);
    if(status==='FAIL')throw Error('frame case failed: '+test.name+'; original evidence retained');
  }
  return results;
}
