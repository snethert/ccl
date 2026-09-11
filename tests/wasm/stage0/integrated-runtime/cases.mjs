import assert from 'node:assert/strict';
import { setTimeout as delay } from 'node:timers/promises';
import { Harness } from './harness.mjs';

const pause=(code,occurrence=1)=>({code,occurrence});
export async function moving(h,count=6) {
  const E=h.schema.events; await h.reset(); const before=h.prepareValues(0,count);
  const job=h.actors[0].run('outer',[2,count],[pause(E.WAITING)],'program');
  const ticket=await h.request(); await h.actors[0].at(E.WAITING);
  assert.equal(h.field(0,'cleanup'),0); assert.equal(h.state(0),h.schema.states.FOREIGN);
  assert.equal(h.field(0,'binding_depth'),8); assert.equal(h.field(0,'binding_cookie'),0x11223344);
  const publishedBefore=h.roots(0); assert.equal(publishedBefore.length,3,'C, binding and permanent root frames must all be live');
  const payload=h.requestSnapshot(ticket).payload;
  await h.actors[1].run('collect_and_park');
  const publishedAfter=h.roots(0),moved=h.word(h.field(0,'root_slot'));
  assert.deepEqual(publishedAfter.map(r=>r.address),publishedBefore.map(r=>r.address));
  for(const frame of publishedAfter) assert.deepEqual(frame.values,[moved,moved],'collector failed to update a live root frame');
  assert.deepEqual(h.requestSnapshot(ticket).payload,payload,'GC changed stable request payload');
  h.complete(ticket,{bytes:h.build.lazy}); h.actors[0].resume();
  return {...h.verifyResume(before,await job,{count,installed:true}),published_before:publishedBefore,published_after:publishedAfter};
}

export async function competitors(h,{wrap=false,newRequest=false}={}) {
  const E=h.schema.events; await h.reset({generation:wrap?0xfffffffe:0});
  const start=h.word(h.global('world_gen'));
  const a=h.actors[1],b=h.actors[2];
  const jobA=a.run('allocate_after_collection',[],[pause(E.BEFORE_CAS),pause(E.ACQUIRED),pause(E.RELEASED)]);
  const jobB=b.run('allocate_after_collection',[],[pause(E.BEFORE_CAS),pause(E.CAS_LOST),pause(E.PROBE,2)]);
  await Promise.all([a.at(E.BEFORE_CAS),b.at(E.BEFORE_CAS)]);
  a.resume(); await a.at(E.ACQUIRED);
  b.resume(); await b.at(E.CAS_LOST);
  assert.equal(h.word(h.global('world_gen')),(start+1)>>>0,'loser changed owner marker');
  assert.equal(h.word(h.global('world_owner')),2,'loser stole collector ownership');
  b.resume(); a.resume(); await a.at(E.RELEASED); await b.at(E.PROBE,2);
  assert.equal(h.word(h.global('world_gen')),(start+2)>>>0,'wrapping release must use parity');
  let extra;
  if(newRequest) {
    const c=h.actors[0]; extra=c.run('collect_and_park',[],[pause(E.ACQUIRED)]);
    await c.at(E.ACQUIRED);
    assert.equal(h.word(h.global('world_gen')),(start+3)>>>0);
    // Both the former owner and the losing requester must retry admission.
    a.resume(); b.resume(); c.resume();
    await extra;
  } else {a.resume();b.resume();}
  const [first,second]=await Promise.all([jobA,jobB]);
  assert.equal(first.snapshot.allocation_checks,1); assert.equal(second.snapshot.allocation_checks,1);
  assert.ok(second.events.some(e=>e.code===E.CAS_LOST));
  if(newRequest) {
    assert.ok(first.snapshot.stops>0,'former owner bypassed new collector');
    assert.ok(second.snapshot.stops>=2,'loser bypassed new request during admission');
  }
  assert.equal(h.word(h.global('world_gen')),(start+(newRequest?4:2))>>>0);
  return {initial_generation:start,new_request:newRequest,allocation_rechecks:[first.snapshot.allocation_checks,second.snapshot.allocation_checks]};
}

export async function admission(h,initialState) {
  const E=h.schema.events; await h.reset(); h.setField(0,'state',initialState);
  const a=h.actors[0],b=h.actors[1];
  const probe=a.run('child_read',[],[pause(E.PROBE),pause(E.STOPPED)]);
  await a.at(E.PROBE);
  const collection=b.run('collect_and_park',[],[pause(E.ACQUIRED)]); await b.at(E.ACQUIRED);
  a.resume(); await a.at(E.STOPPED);
  assert.equal(h.field(0,'admitted'),0,'tentative RUNNING granted heap rights');
  b.resume(); await collection; a.resume();
  const done=await probe; assert.equal(done.result,400); assert.ok(done.snapshot.reloads>0);
  return {initial_state:initialState,stops:done.snapshot.stops};
}

export async function membership(h) {
  const E=h.schema.events; await h.reset({lateChild:true});
  const creator=h.actors[2],collector=h.actors[1];
  const child=h.map.workers[3].tcr.start;
  const create=creator.run('creator',[child],[pause(E.CREATOR_READY),pause(E.CHILD_PUBLISHED)]);
  await creator.at(E.CREATOR_READY);
  const gc=collector.run('collect_and_park',[],[pause(E.SNAPSHOT)]); await collector.at(E.SNAPSHOT);
  creator.resume(); await creator.at(E.CHILD_PUBLISHED);
  const original=h.word(h.field(3,'root_slot'));
  assert.equal(h.word(h.field(2,'root_slot')),65,'handoff retained an accidental parent root');
  assert.equal(h.state(3),h.schema.states.PARKED);
  // Instantiate the child only after actual shared heap/registry mutation.
  await h.configureChild();
  collector.resume(); creator.resume();
  const [done]=await Promise.all([gc,create]);
  const closed=done.events.find(e=>e.code===E.MEMBERSHIP_CLOSED);
  assert.equal(closed.detail,4,'final membership rescan omitted child');
  const moved=h.word(h.field(3,'root_slot'));
  assert.notEqual(moved,original,'child handoff root was not relocated');
  assert.equal((await h.actors[3].run('child_read')).result,800);
  return {original_handoff:original,moved_handoff:moved,closed_membership:closed.detail};
}

export async function io(h,kind='unfinished',{poll=false,loseOutcome=false,count=6,cancel=false,schedulerSeed=0}={}) {
  const E=h.schema.events; await h.reset(); const before=h.prepareValues(0,count);
  if(schedulerSeed) h.enableScheduler(schedulerSeed);
  h.setField(0,'pending',8); // unrelated bit must survive GC and interrupt updates.
  const a=h.actors[0],b=h.actors[1];
  const pauses=[pause(E.INTERRUPT),pause(E.REARM),pause(E.INTERRUPT,2)];
  if(kind!=='blocked-wait') pauses.push(pause(E.WAITING));
  if(kind==='gc-during-wake') pauses.push(pause(E.STOPPED));
  const job=a.run('outer',[1,count],pauses,'program');
  const ticket=await h.request();
  if(kind==='blocked-wait') await a.next(m=>m.kind==='observation'&&m.event.code===E.WAITING);
  else await a.at(E.WAITING);
  let pollJob;
  if(poll) {pollJob=h.actors[2].run('polling',[],[pause(E.POLLING)]);await h.actors[2].at(E.POLLING);h.actors[2].resume();}
  if(kind==='gc-during-wake') {
    const gc=b.run('collect_and_park',[],[pause(E.ACQUIRED)]); await b.at(E.ACQUIRED);
    h.interrupt(ticket); a.resume(); await a.at(E.STOPPED);
    assert.equal(h.field(0,'interrupts'),0,'interrupt serviced before GC admission');
    b.resume(); await gc; a.resume();
  } else {
    await b.run('collect_and_park');
    if(kind==='completion-before-interrupt') {
      h.complete(ticket,{cancel}); h.interrupt(ticket,{loseOutcome});
      assert.equal(h.requestSnapshot(ticket).outcome,cancel?2:1,'terminal outcome overwritten by interrupt');
    } else {
      const notified=h.interrupt(ticket);
      if(kind==='blocked-wait') assert.equal(notified,1,'test did not interrupt an actual blocked waiter');
      if(kind==='completion-after-interrupt') h.complete(ticket,{cancel});
    }
    if(kind!=='blocked-wait') a.resume();
  }
  await a.at(E.INTERRUPT);
  assert.equal(h.field(0,'admitted'),1); assert.equal(h.field(0,'pending'),8);
  assert.notEqual(h.field(0,'observed_root'),before.root,'interrupt service used stale roots');
  assert.equal(h.field(0,'observed_raw'),h.field(0,'observed_root')-1);
  assert.equal(h.requestSnapshot(ticket).consumed,0,'completion suppressed unserviced interrupt');
  const terminal=kind==='completion-before-interrupt'||kind==='completion-after-interrupt';
  if(!terminal) assert.equal(h.requestSnapshot(ticket).outcome,0,'interrupt completed the host operation');
  a.resume();
  if(!terminal) {
    await a.at(E.REARM);
    assert.equal(h.requestSnapshot(ticket).generation,ticket.generation,'rearm reused request generation');
    if(kind==='interrupt-during-rearm') h.interrupt(ticket);
    h.complete(ticket,{cancel}); a.resume();
    if(kind==='interrupt-during-rearm') {await a.at(E.INTERRUPT,2);a.resume();}
  }
  const done=await job;
  assert.equal(done.snapshot.interrupts,kind==='interrupt-during-rearm'?2:1);
  assert.equal(done.snapshot.pending,8); assert.equal(h.requestSnapshot(ticket).consumed,cancel?2:1);
  const result=h.verifyResume(before,done,{count});
  if(poll) {
    h.put(h.global('poll_finish'),1); const polled=await pollJob;
    assert.ok(polled.snapshot.progress>0,'mutator polling did not execute');
    const pending=h.records.flatMap(r=>r.events||[]).find(e=>e.id===1&&e.code===E.PENDING_SET&&e.detail===2);
    const stopped=polled.events.find(e=>e.code===E.STOPPED);
    assert.ok(pending&&stopped,'missing measured safepoint');
    result.safepoint_latency_ms=stopped.at_ms-pending.at_ms;
    assert.ok(result.safepoint_latency_ms>=0,'invalid safepoint timestamp order');
    const collection=h.records.find(r=>r.id===1&&r.events?.some(e=>e.code===E.ACQUIRED));
    const acquired=collection.events.find(e=>e.code===E.ACQUIRED),closed=collection.events.find(e=>e.code===E.MEMBERSHIP_CLOSED);
    assert.ok(acquired&&closed,'missing complete rendezvous timing');
    result.rendezvous_ms=closed.at_ms-acquired.at_ms;
  }
  return {...result,kind,terminal:cancel?'cancel-ack':'completion',request_generation:ticket.generation,interrupts:done.snapshot.interrupts};
}

export async function nested(h,{misroute=false}={}) {
  const E=h.schema.events; await h.reset(); const before=h.prepareValues(0,6); h.setField(0,'mode',1);
  const a=h.actors[0];
  const job=a.run('outer',[1,6],[pause(E.WAITING),pause(E.WAITING,2),pause(E.REARM)],'program');
  const primary=await h.request(); await a.at(E.WAITING);
  await h.actors[1].run('collect_and_park');
  h.interrupt(primary); a.resume();
  const debuggerRequest=await h.request(); await a.at(E.WAITING,2);
  assert.notEqual(primary.address,debuggerRequest.address,'nested debugger reused primary descriptor');
  assert.equal(h.requestSnapshot(primary).active,1); assert.equal(h.requestSnapshot(primary).outcome,0);
  // Interrupt the Lisp thread while its nested debugger owns the current wait.
  h.interrupt(primary,{wrongDescriptor:misroute});
  assert.equal(h.requestSnapshot(debuggerRequest).wake,1,'nested interrupt did not target active descriptor');
  const beforeSecond={...before,root:h.word(h.field(0,'root_slot'))};
  const payloads=[h.requestSnapshot(primary).payload,h.requestSnapshot(debuggerRequest).payload];
  await h.actors[1].run('collect_and_park');
  assert.deepEqual([h.requestSnapshot(primary).payload,h.requestSnapshot(debuggerRequest).payload],payloads);
  h.complete(debuggerRequest); a.resume(); await a.at(E.REARM);
  assert.equal(h.field(0,'cleanup'),0); assert.equal(h.requestSnapshot(primary).generation,primary.generation);
  assert.equal(h.requestSnapshot(debuggerRequest).active,0);
  h.complete(primary); a.resume(); const done=await job;
  assert.equal(done.snapshot.nested,1); assert.equal(done.snapshot.interrupts,2); assert.equal(h.word(h.global('world_completed')),2);
  return {...h.verifyResume(beforeSecond,done),primary:h.ticketRecord(primary),debugger:h.ticketRecord(debuggerRequest)};
}

export async function retirement(h,{ack=true,idleCollection=false}={}) {
  const E=h.schema.events; await h.reset(); const before=h.prepareValues(0,6); h.setField(0,'mode',2);
  const a=h.actors[0],b=h.actors[1];
  const job=a.run('outer',[1,6],[pause(E.WAITING)],'program');
  const ticket=await h.request(); await a.at(E.WAITING);
  await b.run('collect_and_park'); h.interrupt(ticket); a.resume();
  const exit=await job;
  assert.deepEqual(exit.result,[-1,6]); assert.equal(exit.snapshot.cleanup,1,'nonlocal exit did not clean up once');
  assert.equal(exit.snapshot.c_sp,h.map.workers[0].stack.end,'exceptional C SP not restored');
  for(const field of ['root_head','binding_depth','vsp','tsp','csp']) assert.equal(exit.snapshot[field],before.snapshot[field]);
  assert.equal(h.requestSnapshot(ticket).cancel_requested,1); assert.equal(h.requestSnapshot(ticket).active,1);
  if(idleCollection) {
    // No command is queued for worker 0: its emitted activation has returned to JS.
    // The real collector must finish while that Worker stays idle.
    await b.run('collect_and_park');
    assert.equal(h.word(h.global('world_completed')),2,'collection during exceptional idle did not complete');
    assert.equal(h.state(0),h.schema.states.PARKED,'idle exceptional Worker is not parked');
    assert.equal(h.field(0,'admitted'),0,'idle exceptional Worker retained heap rights');
    assert.equal(h.requestSnapshot(ticket).active,1,'idle collection released the outstanding host request');
  }
  const address=h.map.workers[0].tcr.start;
  await a.run('retire');
  const retiredAt=h.field(0,'retire_serial');
  assert.equal((await b.run('reclaim_and_park',[address])).result,0,'reclaimed without subsequent collection');
  const payload=h.requestSnapshot(ticket).payload;
  await b.run('collect_and_park');
  assert.deepEqual(h.requestSnapshot(ticket).payload,payload,'retired request payload changed during GC');
  assert.equal((await b.run('reclaim_and_park',[address])).result,0,'reclaimed before host acknowledgement');
  assert.equal(h.requestSnapshot(ticket).generation,ticket.generation);
  h.complete(ticket,{cancel:ack});
  assert.equal((await b.run('reclaim_and_park',[address])).result,1,'terminal request was not reclaimable');
  const after=h.requestSnapshot(ticket);
  assert.equal((await b.run('reclaim_and_park',[address])).result,0,'reclamation was applied twice');
  assert.deepEqual(h.requestSnapshot(ticket),after,'duplicate reclamation changed lifetime');
  assert.throws(()=>h.complete(ticket),/STALE_REQUEST_GENERATION/);
  assert.deepEqual(h.requestSnapshot(ticket),after,'late host write changed reused storage');
  return {terminal:ack?'cancel-ack':'completion',request:h.ticketRecord(ticket),retired_at:retiredAt,
    lifetime_after:h.field(0,'lifetime'),generation_after:after.generation,late_completion:'REJECTED'};
}

export async function missingWake(h,kind) {
  const E=h.schema.events; await h.reset(); h.prepareValues(0,6);
  h.actors[0].run('outer',[1,6],[],'program'); const ticket=await h.request();
  await h.actors[0].next(m=>m.kind==='observation'&&m.event.code===E.WAITING);
  await delay(5); // Only establishes the attempted schedule; the witness below proves an actual waiter.
  h.interrupt(ticket,{pendingOnly:kind==='pending-only',omitNotify:kind==='omitted-notify'});
  await delay(5);
  const before={interrupts:h.field(0,'interrupts'),request:h.requestSnapshot(ticket)};
  const waiters=Atomics.notify(h.words,(ticket.address+h.schema.request.wake)/4,1);
  assert.equal(waiters,1,'negative schedule did not establish an actual blocked waiter');
  assert.equal(before.interrupts,0,'negative schedule already serviced interrupt');
  assert.equal(before.request.outcome,0);
  // This injected host defect is rejected by a waiter-count witness, not a timeout.
  const defect=Error('FOREIGN_INTERRUPT_NOT_NOTIFIED');
  h.hostEvents.push({kind:'rejection-witness',waiters,before}); h.fail(defect);
  throw defect;
}

export async function outcomeAfterWake(h) {
  const E=h.schema.events; await h.reset(); h.prepareValues(0,6);
  const a=h.actors[0];
  a.run('outer',[1,6],[pause(E.WAITING),pause(E.WAITING,2)],'program');
  const ticket=await h.request(); await a.at(E.WAITING);
  // Reverse the real host's two completion phases. Let C consume the wake,
  // observe PENDING, and rearm before the faulty host publishes the outcome.
  h.finishComplete(ticket); a.resume(); await a.at(E.WAITING,2);
  assert.equal(h.requestSnapshot(ticket).wake,0,'Worker did not rearm');
  assert.equal(h.requestSnapshot(ticket).outcome,0,'outcome was already published');
  a.resume(); await delay(5);
  h.beginComplete(ticket);
  const before={thread:h.threadSnapshot(0),request:h.requestSnapshot(ticket)};
  const waiters=Atomics.notify(h.words,(ticket.address+h.schema.request.wake)/4,1);
  assert.equal(waiters,1,'negative schedule did not establish an actual blocked waiter');
  assert.equal(before.request.outcome,1,'late terminal outcome is not durable');
  assert.equal(before.request.consumed,0,'late outcome already consumed');
  const defect=Error('HOST_OUTCOME_AFTER_FINAL_WAKE');
  h.hostEvents.push({kind:'rejection-witness',fault:'outcome-after-final-wake',waiters,before});
  h.fail(defect); throw defect;
}

export async function delayedHostCommit(h,{unprotected=false}={}) {
  const E=h.schema.events; await h.reset(); h.prepareValues(0,6);
  const a=h.actors[0];
  const first=a.run('outer',[1,6],[pause(E.WAITING)],'program');
  const old=await h.request();await a.at(E.WAITING);
  h.beginComplete(old);h.interrupt(old);a.resume();await first;
  const second=a.run('outer',[1,6],[pause(E.WAITING)],'program');
  const current=await h.request();await a.at(E.WAITING);
  assert.equal(current.address,old.address);assert.equal(current.generation,old.generation+1);
  const before=h.requestSnapshot(current);
  h.finishComplete(old,{unprotected});
  assert.deepEqual(h.requestSnapshot(current),before,'late host commit wrote a reused descriptor');
  h.complete(current);a.resume();await second;
  return {original:h.ticketRecord(old),reused:h.ticketRecord(current)};
}

export const positiveCases=[
  ...[0,1,6].map(count=>({name:`moving-install-${count}-values`,id:'S0-LL20-a',fn:h=>moving(h,count)})),
  {name:'competing-collectors',id:'S0-LL20-b',fn:h=>competitors(h)},
  {name:'wrap-and-new-request-during-admission',id:'S0-LL20-b',fn:h=>competitors(h,{wrap:true,newRequest:true})},
  {name:'parked-admission',id:'S0-LL20-b',fn:h=>admission(h,1)},
  {name:'stopped-admission',id:'S0-LL20-b',fn:h=>admission(h,4)},
  {name:'child-handoff-final-rescan',id:'S0-LL20-b',fn:membership},
  ...['unfinished','blocked-wait','completion-before-interrupt','completion-after-interrupt','gc-during-wake','interrupt-during-rearm'].map(kind=>({name:'io-'+kind,id:'S0-LL20-b',fn:h=>io(h,kind)})),
  ...['completion-before-interrupt','completion-after-interrupt','interrupt-during-rearm'].map(kind=>({name:'cancel-ack-'+kind,id:'S0-LL20-b',fn:h=>io(h,kind,{cancel:true})})),
  {name:'nested-debugger-two-collections',id:'S0-LL20-c',fn:nested},
  {name:'nonlocal-exit-cancel-ack-lifetime',id:'S0-LL20-c',fn:h=>retirement(h)},
  {name:'nonlocal-exit-raced-completion-lifetime',id:'S0-LL20-c',fn:h=>retirement(h,{ack:false})},
  {name:'collection-between-nonlocal-exit-and-retirement',id:'S0-LL20-c',fn:h=>retirement(h,{idleCollection:true})},
  {name:'host-commit-after-descriptor-reuse',id:'S0-LL20-c',fn:delayedHostCommit}
];

export const negativeCases=[
  {name:'stale-C-temporary',id:'S0-LL20-a',options:{mutant:'staleC'},fn:moving,code:102},
  {name:'stale-Wasm-local',id:'S0-LL20-a',options:{staleWasm:true},fn:moving,code:102},
  {name:'fetch-add-acquisition',id:'S0-LL20-b',options:{mutant:'fetchAdd'},fn:competitors,pattern:/loser changed owner marker/},
  {name:'omitted-final-rescan',id:'S0-LL20-b',options:{mutant:'omitRescan'},fn:membership,pattern:/final membership rescan omitted child/},
  {name:'pending-bit-only',id:'S0-LL20-b',fn:h=>missingWake(h,'pending-only'),pattern:/FOREIGN_INTERRUPT_NOT_NOTIFIED/},
  {name:'omitted-notify',id:'S0-LL20-b',fn:h=>missingWake(h,'omitted-notify'),pattern:/FOREIGN_INTERRUPT_NOT_NOTIFIED/},
  {name:'host-outcome-after-final-wake',id:'S0-LL20-b',fn:outcomeAfterWake,pattern:/HOST_OUTCOME_AFTER_FINAL_WAKE/},
  {name:'omitted-exception-park',id:'S0-LL20-c',options:{omitExceptionPark:true},fn:async h=>{
    try { await retirement(h,{idleCollection:true}); }
    catch(e) {
      const s=h.failureSnapshot;
      assert.ok(s,'missing fatal collection snapshot');
      assert.equal(s.threads[0].state,h.schema.states.RUNNING);
      assert.equal(s.threads[0].admitted,1);
      assert.equal(s.threads[0].cleanup,1);
      assert.equal(s.globals.world_completed,1);
      assert.equal(s.globals.world_gen,3);
      assert.equal(s.globals.world_owner,2);
      throw Error('idle exceptional Worker blocked collection');
    }
  },pattern:/idle exceptional Worker blocked collection/},
  {name:'lost-terminal-outcome',id:'S0-LL20-b',fn:h=>io(h,'completion-before-interrupt',{loseOutcome:true}),pattern:/terminal outcome overwritten/},
  {name:'premature-request-reuse',id:'S0-LL20-c',options:{mutant:'prematureReuse'},fn:retirement,pattern:/reclaimed before host acknowledgement/},
  {name:'collector-trap-fails-world',id:'S0-LL20-b',options:{mutant:'ownerTrap'},fn:async h=>{await h.reset();await h.actors[1].run('collect_and_park');},code:901},
  {name:'unpublished-child-admission',id:'S0-LL20-b',fn:async h=>{await h.reset();await h.actors[3].run('child_read');},code:103},
  {name:'unguarded-final-host-wake',id:'S0-LL20-c',fn:h=>delayedHostCommit(h,{unprotected:true}),pattern:/late host commit wrote a reused descriptor/}
  ,{name:'interrupt-wrong-nested-descriptor',id:'S0-LL20-c',fn:h=>nested(h,{misroute:true}),pattern:/nested interrupt did not target active descriptor/}
];

export async function executeCases(build,write) {
  const results=[];
  for(const test of [...positiveCases,...negativeCases]) {
    const h=new Harness(build,test.options); let status='PASS',detail,error;
    const negative=negativeCases.includes(test), started=performance.now();
    try {
      detail=await test.fn(h);
      if(negative) throw Error('negative control unexpectedly passed');
    } catch(e) {
      error=e.stack;
      const rejected=negative&&((test.code&&h.failureSnapshot?.globals.failure_code===test.code)||(test.pattern&&test.pattern.test(e.message)));
      if(!rejected) status='FAIL';
      else {
        status='REJECTED';
        if(test.code===901) {
          assert.equal(h.failureSnapshot.globals.world_gen&1,1,'failed owner marker was cleared');
          assert.equal(h.failureSnapshot.globals.world_owner,2,'failed owner was replaced');
        }
      }
    } finally {await h.close();}
    const record=h.evidence({name:test.name,id:test.id,status,negative,detail,error,elapsed_ms:performance.now()-started,
      fatal_snapshot:h.failureSnapshot,all_workers_terminated:h.actors.filter(Boolean).every(a=>a.closed)});
    write(test.name,record,negative); results.push(record);
    console.log(`${status} ${test.name}`);
    if(status==='FAIL') throw Error(`case failed: ${test.name}; retained original evidence`);
  }
  return results;
}

export async function randomized(build,write,{seeds=1000,limits}={}) {
  assert.ok(limits,'predeclared progress limits required');
  const h=new Harness(build), summaries=[],raw=[];
  const kinds=['unfinished','completion-before-interrupt','completion-after-interrupt','gc-during-wake','interrupt-during-rearm'];
  try {
    for(let seed=1;seed<=seeds;seed++) {
      let x=seed; const random=()=>{x^=x<<13;x^=x>>>17;x^=x<<5;return x>>>0;};
      const kind=kinds[random()%kinds.length],count=[0,1,6][random()%3],cancel=!!(random()&1),start=performance.now();
      try {
        const detail=await io(h,kind,{poll:true,count,cancel,schedulerSeed:seed});
        const elapsed=performance.now()-start;
        assert.ok(elapsed<=limits.per_schedule_timeout_ms,'random schedule exceeded time limit');
        assert.ok(detail.rendezvous_ms<=limits.rendezvous_timeout_ms,'whole rendezvous exceeded time limit');
        const summary={seed,kind,count,cancel,status:'PASS',elapsed_ms:elapsed,safepoint_latency_ms:detail.safepoint_latency_ms,rendezvous_ms:detail.rendezvous_ms};
        summaries.push(summary);raw.push(h.evidence(summary));
      } catch(e) {write('random-failure',h.evidence({seed,kind,count,error:e.stack}),false);throw e;}
      if(seed%100===0) console.log(`PASS randomized schedules ${seed}/${seeds}`);
    }
  } finally {await h.close();}
  write('randomized-raw',raw,false);
  const sorted=summaries.map(s=>s.safepoint_latency_ms).sort((a,b)=>a-b);
  const p99=sorted[Math.ceil(sorted.length*.99)-1],max=sorted.at(-1);
  const report={seeds:summaries.length,seed_range:[1,seeds],policy:'xorshift32 selects a family, value count, terminal outcome and runnable Worker at each automatic scheduler boundary; ready sets and choices are retained',
    safepoint_latency_p99_ms:p99,safepoint_latency_max_ms:max,
    rendezvous_max_ms:Math.max(...summaries.map(s=>s.rendezvous_ms)),schedules:summaries};
  write('randomized-summary',report,false);
  assert.ok(seeds>=limits.random_schedule_seeds_minimum,'minimum randomized schedule count not met');
  assert.ok(p99<=limits.safepoint_latency_p99_ms&&max<=limits.safepoint_latency_max_ms,'safepoint latency exceeded predeclared limits');
  return report;
}
