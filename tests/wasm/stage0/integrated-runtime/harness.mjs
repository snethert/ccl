import assert from 'node:assert/strict';
import { Worker } from 'node:worker_threads';
import { planMemory, validateMap } from '../runtime-boundary/runtime.mjs';

const now=()=>Number(process.hrtime.bigint())/1e6;
class Actor {
  constructor(owner,data) {
    this.owner=owner; this.inbox=[]; this.waiters=[]; this.busy=false; this.closed=false;
    this.worker=new Worker(new URL('./actor.mjs',import.meta.url),{workerData:data});
    this.worker.on('message',m=>this.message(m));
    this.worker.on('error',e=>owner.fail(e));
    this.worker.on('exit',code=>{if(!this.closed) owner.fail(Error(`unexpected Worker exit ${code}`));});
  }
  message(m) {
    if(m.kind==='automatic') {this.owner.schedule(this,m.event);return;}
    if(m.kind==='failure') {
      this.owner.records.push(m); this.owner.fail(Error(m.error)); return;
    }
    if(m.kind==='done') { this.busy=false; this.owner.records.push(m); }
    const index=this.waiters.findIndex(w=>w.predicate(m));
    if(index<0) this.inbox.push(m);
    else { const w=this.waiters.splice(index,1)[0]; clearTimeout(w.timer); w.resolve(m); }
  }
  next(predicate,timeout=5000) {
    if(this.owner.failure) return Promise.reject(this.owner.failure);
    const index=this.inbox.findIndex(predicate);
    if(index>=0) return Promise.resolve(this.inbox.splice(index,1)[0]);
    const p=new Promise((resolve,reject)=>{
      const w={predicate,resolve,reject};
      w.timer=setTimeout(()=>this.owner.fail(Error('supervisor schedule deadline')),timeout);
      this.waiters.push(w);
    });
    p.catch(()=>{}); return p;
  }
  async configure(memory,plan) {
    assert.equal(this.busy,false);
    this.inbox=[]; this.control=new Int32Array(new SharedArrayBuffer(4));
    const done=this.next(m=>m.kind==='configured');
    this.worker.postMessage({kind:'configure',memory,plan,control:this.control.buffer});
    await done;
  }
  run(method,args=[],pauses=[],module='kernel') {
    assert.equal(this.busy,false,'one live command per Worker'); this.busy=true;
    const done=this.next(m=>m.kind==='done');
    this.worker.postMessage({kind:'run',method,args,pauses,module,automatic:!!this.owner.scheduler}); return done;
  }
  at(code,occurrence=1) { return this.next(m=>m.kind==='point'&&m.event.code===code&&m.event.occurrence===occurrence); }
  resume() { Atomics.store(this.control,0,1); Atomics.notify(this.control,0); }
  async stop(error) {
    this.closed=true;
    for(const w of this.waiters.splice(0)) { clearTimeout(w.timer); w.reject(error||Error('harness stopped')); }
    await this.worker.terminate();
  }
}

export class Harness {
  constructor(build,{mutant,staleWasm=false,omitExceptionPark=false}={}) {
    this.build=build; this.schema=build.schema; this.failure=null; this.records=[]; this.hostEvents=[];
    const variant=mutant?build.mutants[mutant]:{bytes:build.kernel,metadata:build.metadata};
    this.kernelBytes=variant.bytes; this.metadata=variant.metadata;
    this.actorData={schema:build.schema,kernel:variant.bytes,metadata:variant.metadata,emitted:build.emitted,
      program:omitExceptionPark?build.omitExceptionPark:staleWasm?build.staleWasm:build.program,manifest:build.manifest};
    this.actors=[new Actor(this,this.actorData),new Actor(this,this.actorData),new Actor(this,this.actorData),null];
  }
  fail(error) {
    if(this.failure) return;
    this.failure=error; this.failureSnapshot=this.snapshot(); this.scheduler=null;
    this.stopping=Promise.all(this.actors.filter(Boolean).map(a=>a.stop(error)));
  }
  async close() { await (this.stopping||Promise.all(this.actors.filter(Boolean).map(a=>a.stop()))); }
  global(name) { return this.metadata.exportedGlobals[name].value; }
  word(address) { return Atomics.load(this.words,address/4)>>>0; }
  put(address,value) { Atomics.store(this.words,address/4,value); }
  field(id,name) { return this.word(this.map.workers[id].tcr.start+this.schema.tcr[name]); }
  setField(id,name,value) { this.put(this.map.workers[id].tcr.start+this.schema.tcr[name],value); }
  state(id) { return this.field(id,'state'); }
  async reset({generation=0,lateChild=false}={}) {
    assert.equal(this.failure,null);
    this.records=[]; this.hostEvents=[]; this.scheduler=null; this.scheduleDecisions=[];
    this.memory=new WebAssembly.Memory({initial:8,maximum:16,shared:true});
    this.words=new Int32Array(this.memory.buffer);
    this.wakePairs=new BigUint64Array(this.memory.buffer);
    const base=planMemory(this.metadata,this.schema,4);
    let next=Math.ceil(base.usedEnd/16)*16;
    const allocate=(name,bytes)=>{const r={name,start:next,end:next+bytes,alignment:16};next+=bytes;base.regions.push(r);return r;};
    base.requests=base.workers.map(w=>allocate(`worker-${w.id}-requests`,512));
    base.heaps=[allocate('semispace-0',4096),allocate('semispace-1',4096)];
    base.usedEnd=next; validateMap(base,this.memory.buffer.byteLength); this.map=base;
    const emitted=new WebAssembly.Instance(new WebAssembly.Module(this.build.emitted));
    const table=new WebAssembly.Table({initial:this.build.manifest.slot+1,element:'anyfunc'});
    this.main=new WebAssembly.Instance(new WebAssembly.Module(this.kernelBytes),{
      env:{memory:this.memory,__indirect_function_table:table},bridge:{park(){throw Error('initialization cannot park');}},
      emitted:{raise:emitted.exports.raise},schedule:{point(){throw Error('initialization cannot run thread protocol');}},
      host:{request(){throw Error('initialization cannot issue host requests');},callback(){throw Error('unexpected callback');},install(){throw Error('unexpected install');}}
    }).exports;
    this.main.initialize(base.heaps[0].start,base.heaps[1].start,generation);
    this.initialRoot=this.main.seed_graph(100); this.childRoot=this.main.seed_graph(200);
    for(const w of base.workers) {
      this.main.initialize_thread(w.tcr.start,w.id,base.requests[w.id].start,w.lisp.start+512,w.lisp.start,w.id===0?this.initialRoot:w.id===2?this.childRoot:65);
      if(w.id!==3) this.main.publish_initial(w.tcr.start);
    }
    this.put(this.global('data_sentinel'),0x55667788); this.put(this.global('bss_sentinel'),0x99aabbcc);
    if(!lateChild && !this.actors[3]) this.actors[3]=new Actor(this,this.actorData);
    await Promise.all(this.actors.slice(0,lateChild?3:4).map((a,i)=>a.configure(this.memory,base.workers[i])));
    this.checkSentinels();
  }
  async configureChild() {
    if(!this.actors[3]) this.actors[3]=new Actor(this,this.actorData);
    await this.actors[3].configure(this.memory,this.map.workers[3]); this.checkSentinels();
  }
  checkSentinels() {
    assert.equal(this.word(this.global('data_sentinel')),0x55667788,'late instance replayed .data');
    assert.equal(this.word(this.global('bss_sentinel')),0x99aabbcc,'late instance replayed BSS');
  }
  prepareValues(id,count=6) {
    const root=this.word(this.field(id,'root_slot')), tail=root===65?65:this.word(root-1);
    const values=[4,-28,root,tail,0,2147483644];
    values.forEach((v,i)=>this.put(this.field(id,'mv_base')+i*4,v));
    this.setField(id,'nvalues',count);
    return {root,tail,values:values.slice(0,count).map(x=>x>>>0),snapshot:this.threadSnapshot(id)};
  }
  async request(id=0) {
    const m=await this.actors[id].next(m=>m.kind==='request');
    const q=this.schema.request;
    const ticket={id,address:m.address,memory:this.memory,generation:this.word(m.address+q.generation),owner_lifetime:this.word(m.address+q.owner_lifetime),opcode:this.word(m.address+q.opcode)};
    this.hostEvents.push({kind:'request',...this.ticketRecord(ticket),at_ms:m.at_ms}); return ticket;
  }
  ticketRecord(t) { return {id:t.id,address:t.address,generation:t.generation,owner_lifetime:t.owner_lifetime,opcode:t.opcode}; }
  complete(ticket,{cancel=false,bytes,result=37}={}) {
    this.beginComplete(ticket,{cancel,bytes,result}); return this.finishComplete(ticket,{cancel});
  }
  beginComplete(ticket,{cancel=false,bytes,result=37}={}) {
    const q=this.schema.request,p=ticket.address;
    if(ticket.memory!==this.memory||this.word(p+q.generation)!==ticket.generation||this.word(p+q.owner_lifetime)!==ticket.owner_lifetime||this.word(p+q.active)!==1)
      throw Error('STALE_REQUEST_GENERATION: host write rejected');
    if(this.word(p+q.outcome)!==0) throw Error('duplicate terminal host outcome');
    if(bytes) {
      assert.ok(bytes.length<=this.schema.payload_capacity);
      new Uint8Array(this.memory.buffer,p+q.payload,bytes.length).set(bytes); this.put(p+q.length,bytes.length);
    }
    this.put(p+q.result,result);
    this.put(p+q.outcome,cancel?2:1);
  }
  setWake(ticket,value) {
    const index=(ticket.address+this.schema.request.wake)/8;
    if(ticket.memory!==this.memory) return false;
    for(;;) {
      const previous=Atomics.load(this.wakePairs,index);
      if(Number(previous>>32n)!==ticket.generation) return false;
      const next=(previous&0xffffffff00000000n)|BigInt(value);
      if(Atomics.compareExchange(this.wakePairs,index,previous,next)===previous) return true;
    }
  }
  finishComplete(ticket,{cancel=false,unprotected=false}={}) {
    const p=ticket.address,q=this.schema.request;
    if(unprotected) this.put(p+q.wake,2);
    else if(!this.setWake(ticket,2)) {
      this.hostEvents.push({kind:'stale-final-wake-rejected',...this.ticketRecord(ticket),at_ms:now()}); return 0;
    }
    const notified=Atomics.notify(this.words,(p+q.wake)/4);
    this.hostEvents.push({kind:cancel?'cancel-ack':'complete',...this.ticketRecord(ticket),notified,at_ms:now()});
    return notified;
  }
  interrupt(ticket,{pendingOnly=false,omitNotify=false,loseOutcome=false,wrongDescriptor=false}={}) {
    if(ticket.memory!==this.memory||this.field(ticket.id,'lifetime')!==ticket.owner_lifetime) throw Error('stale interrupt thread lifetime');
    const pending=this.map.workers[ticket.id].tcr.start+this.schema.tcr.pending,q=this.schema.request;
    const active=this.field(ticket.id,'active_request');
    const p=wrongDescriptor?ticket.address:active;
    const target={...ticket,address:p,generation:p?this.word(p+q.generation):0};
    Atomics.or(this.words,pending/4,2);
    if(!p) {this.hostEvents.push({kind:'running-thread-interrupt',id:ticket.id,at_ms:now()});return 0;}
    if(!pendingOnly && !this.setWake(target,1)) throw Error('stale interrupt request generation');
    if(loseOutcome) this.put(p+q.outcome,0);
    const notified=pendingOnly||omitNotify?0:Atomics.notify(this.words,(p+q.wake)/4);
    this.hostEvents.push({kind:'interrupt',...this.ticketRecord(target),requested_address:ticket.address,pendingOnly,omitNotify,loseOutcome,wrongDescriptor,notified,at_ms:now()});
    return notified;
  }
  requestSnapshot(ticket) {
    const p=ticket.address,q=this.schema.request;
    return { ...Object.fromEntries(Object.entries(q).filter(([name])=>name!=='payload').map(([name,offset])=>[name,this.word(p+offset)])),
      payload:Array.from(new Uint8Array(this.memory.buffer,p+q.payload,Math.min(192,this.word(p+q.length)))) };
  }
  threadSnapshot(id) {
    if(!this.map) return null;
    const t=this.map.workers[id].tcr.start;
    return Object.fromEntries(Object.entries(this.schema.tcr).map(([name,off])=>[name,this.word(t+off)]));
  }
  roots(id) {
    const frames=[],plan=this.map.workers[id]; let address=this.field(id,'root_head');
    while(address) {
      assert.ok(frames.length<16,'root chain cycle');
      const count=this.word(address+4);
      assert.ok(count<=8);
      const owner=[plan.stack,plan.lisp].find(r=>address>=r.start&&address+8+count*4<=r.end);
      assert.ok(owner,'published root frame outside owned stacks');
      frames.push({address,owner:owner.name,previous:this.word(address),values:Array.from({length:count},(_,i)=>this.word(address+8+i*4))});
      address=this.word(address);
    }
    return frames;
  }
  snapshot() {
    if(!this.words||!this.map) return {};
    return {globals:Object.fromEntries(['world_gen','world_owner','world_completed','collecting','heap_active','heap_used','failure_code'].map(name=>[name,this.word(this.global(name))])),
      threads:this.map.workers.map((_,i)=>this.threadSnapshot(i)),sentinels:[this.word(this.global('data_sentinel')),this.word(this.global('bss_sentinel'))]};
  }
  enableScheduler(seed) {this.scheduler={state:seed>>>0,queue:[],pending:false};}
  schedule(actor,event) {
    const s=this.scheduler; if(!s||this.failure) return;
    s.queue.push({actor,event});
    const release=()=>{
      if(this.scheduler!==s||this.failure) return;
      if(!s.queue.length) {s.pending=false;return;}
      let x=s.state; x^=x<<13;x^=x>>>17;x^=x<<5;s.state=x>>>0;
      const index=s.state%s.queue.length;
      this.scheduleDecisions.push({available:s.queue.map(p=>({id:p.event.id,code:p.event.code,occurrence:p.event.occurrence})),chosen:index});
      s.queue.splice(index,1)[0].actor.resume(); setImmediate(release);
    };
    if(!s.pending) {s.pending=true;setImmediate(release);}
  }
  evidence(extra={}) { return { ...extra,snapshot:this.snapshot(),host_events:this.hostEvents,scheduler_decisions:this.scheduleDecisions,commands:this.records }; }
  verifyResume(before,done,{count=6,installed=false}={}) {
    const after=done.snapshot, root=after.root, tail=this.word(root-1);
    assert.notEqual(root,before.root,'root did not move');
    assert.equal(this.word(before.root-1),0xdeadbeef,'from-space was not poisoned');
    assert.equal(this.word(root+3),400,'relocated root car'); assert.equal(this.word(tail+3),404,'relocated tail car');
    assert.equal(this.word(tail-1),root,'cycle/alias not preserved');
    assert.equal(after.observed_raw,root-1,'raw interior pointer was not re-derived');
    assert.deepEqual(done.result,[count?4:65,count],'continuation returned wrong first value/count');
    const expected=[4,(-28)>>>0,root,tail,0,2147483644].slice(0,count);
    assert.deepEqual(after.values,expected,'complete ordered multiple values changed');
    for(const key of ['root_head','binding_depth','vsp','tsp','csp','mv_base','mv_owner_top','continuation','handler_cookie','binding_cookie','active_request'])
      assert.equal(after[key],before.snapshot[key],`lost ${key}`);
    assert.equal(after.cleanup,0,'suspension ran unwind cleanup');
    assert.equal(after.c_sp,this.map.workers[0].stack.end,'C SP not restored');
    if(installed) {assert.equal(done.installed,this.build.manifest.sha256);assert.equal(after.progress,468,'new code did not execute on moved object');}
    this.checkSentinels();
    return {old_root:before.root,new_root:root,new_tail:tail,values:after.values,old_space_poison:this.word(before.root-1)};
  }
}
