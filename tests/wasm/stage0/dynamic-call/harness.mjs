import assert from 'node:assert/strict';
import {Worker} from 'node:worker_threads';
import {planMemory,validateMap} from '../runtime-boundary/runtime.mjs';

class Actor {
  constructor(owner,id) {
    this.owner=owner;this.id=id;this.inbox=[];this.waiters=[];this.busy=false;this.closed=false;
    this.worker=new Worker(new URL('./actor.mjs',import.meta.url),{workerData:owner.data});
    this.worker.on('error',e=>owner.fail(e));
    this.worker.on('exit',code=>{if(!this.closed)owner.fail(Error('unexpected ABI Worker exit '+code));});
    this.worker.on('message',m=>{
      if(m.kind==='failure'){owner.failureRecord=m;owner.fail(Error(m.error));return;}
      if(m.kind==='done')this.busy=false;
      const i=this.waiters.findIndex(w=>w.match(m));
      if(i>=0){const w=this.waiters.splice(i,1)[0];clearTimeout(w.timer);w.resolve(m);}else this.inbox.push(m);
    });
  }
  next(match) {
    if(this.owner.failure)return Promise.reject(this.owner.failure);
    const i=this.inbox.findIndex(match);if(i>=0)return Promise.resolve(this.inbox.splice(i,1)[0]);
    const p=new Promise((resolve,reject)=>{const w={match,resolve,reject};w.timer=setTimeout(()=>this.owner.fail(Error('ABI supervisor deadline')),10000);this.waiters.push(w);});p.catch(()=>{});return p;
  }
  async configure() {
    const done=this.next(m=>m.kind==='configured');this.worker.postMessage({kind:'configure',memory:this.owner.memory,plan:this.owner.map.workers[this.id],control:new SharedArrayBuffer(4)});await done;
  }
  command(kind,args=[]) {assert.equal(this.busy,false);this.busy=true;this.worker.postMessage({kind,args});}
  async simple(kind,args=[]) {this.command(kind,args);return this.next(m=>m.kind==='done');}
  async close(error=Error('closed')) {this.closed=true;for(const w of this.waiters.splice(0)){clearTimeout(w.timer);w.reject(error);}await this.worker.terminate();}
}

export class ABIHarness {
  constructor(build,name,options={}) {
    this.build=build;this.candidate=build.candidates[name];this.options=options;this.name=name;this.actors=[];this.failure=null;
    this.data={runtime:build.runtime,schema:build.schema,kernel:build.kernel,emitted:build.emitted,slots:build.slots,candidate:this.candidate,options};
    this.f={...build.runtime.tcr,...build.schema.tcr};this.q=build.runtime.request;
  }
  fail(error) {if(this.failure)return;this.failure=error;this.stopping=Promise.all(this.actors.map(a=>a.close(error)));}
  async close() {await (this.stopping||Promise.all(this.actors.map(a=>a.close())));}
  word(p) {return Atomics.load(this.words,p/4)>>>0;}
  put(p,v) {Atomics.store(this.words,p/4,v);}
  global(n) {return this.build.metadata.exportedGlobals[n].value;}
  field(id,n) {return this.word(this.map.workers[id].tcr.start+this.f[n]);}
  setField(id,n,v) {this.put(this.map.workers[id].tcr.start+this.f[n],v);}
  async reset() {
    this.memory=new WebAssembly.Memory({initial:16,maximum:16,shared:true});this.words=new Int32Array(this.memory.buffer);this.pairs=new BigUint64Array(this.memory.buffer);
    const map=planMemory(this.build.metadata,this.build.runtime,4);let next=(map.usedEnd+15)&-16;
    const allocate=(name,bytes)=>{const r={name,start:next,end:next+bytes,alignment:16};next+=bytes;map.regions.push(r);return r;};
    map.heaps=[allocate('heap-0',4096),allocate('heap-1',4096)];
    for(const w of map.workers) {
      w.requests=allocate(`requests-${w.id}`,512);w.state=allocate(`abi-state-${w.id}`,128);
      w.input=allocate(`input-${w.id}`,160);w.anchors=allocate(`anchors-${w.id}`,48);w.output=allocate(`output-${w.id}`,48);
      w.abi=allocate(`ABI-stack-${w.id}`,16384);w.replies=allocate(`ABI-replies-${w.id}`,8192*16);
    }
    map.usedEnd=next;
    if(this.options.mapOverlap)map.regions[1].start=map.regions[0].start;
    if(this.options.undersizedStack){const r=map.workers[0].stack;r.end=r.start+8;}
    validateMap(map,this.memory.buffer.byteLength);this.map=map;
    const emitted=new WebAssembly.Instance(new WebAssembly.Module(this.build.emitted));
    const table=new WebAssembly.Table({initial:this.build.slots.minimum,element:'anyfunc'});
    this.main=new WebAssembly.Instance(new WebAssembly.Module(this.build.kernel),{env:{memory:this.memory,__indirect_function_table:table},emitted:emitted.exports,
      bridge:{park(){throw Error('initializer park');}},schedule:{point(){throw Error('initializer protocol');}},
      host:{request(){throw Error('initializer request');},callback(){throw Error('initializer callback');},install(){throw Error('initializer installation');}}}).exports;
    this.main.initialize(map.heaps[0].start,map.heaps[1].start,0);
    const templates=this.build.schema.entries.map((e,i)=>{const p=this.main.seed_graph(e.code);this.put(this.word(p-1)+3,(500+i*11)*4);return p;});
    for(const w of map.workers) {
      this.main.initialize_thread(w.tcr.start,w.id,w.requests.start,w.lisp.start+512,w.lisp.start,templates[0]);
      this.put(w.anchors.start,0);this.put(w.anchors.start+4,8);templates.forEach((v,i)=>this.put(w.anchors.start+8+i*4,v));
      this.put(w.output.start,w.anchors.start);this.put(w.output.start+4,0);
      for(let i=0;i<6;i++)this.put(w.output.start+8+i*4,65);
      this.setField(w.id,'root_head',w.output.start);this.setField(w.id,'root_slot',w.anchors.start+8);
      this.setField(w.id,'mv_base',w.output.start+8);this.setField(w.id,'mv_owner_top',w.output.start+32);this.setField(w.id,'vsp',w.abi.start);
      if(w.id<2)this.main.publish_initial(w.tcr.start);
    }
    this.put(this.global('data_sentinel'),0x55667788);this.put(this.global('bss_sentinel'),0x99aabbcc);
    this.actors=[new Actor(this,0),new Actor(this,1)];await Promise.all(this.actors.map(a=>a.configure()));
    this.initializeState(0);this.initializeState(1);
    this.packets=[];this.io=[];this.collections=[];
  }
  initializeState(id) {
    const w=this.map.workers[id],s=this.build.schema.state;
    for(const [name,v] of Object.entries({input:w.input.start,anchors:w.anchors.start+8,output:w.output.start+8,value_count:6,policy:3}))this.put(w.state.start+s[name],v);
  }
  allocate(car,cdr=65) {
    assert.ok(this.actors.every(a=>!a.busy),'fixture input construction requires parked Workers');
    const used=this.word(this.global('heap_used')),active=this.word(this.global('heap_active'));
    assert.ok(used+8<=4096);const p=this.map.heaps[active].start+used;
    this.put(p,cdr);this.put(p+4,car);this.put(this.global('heap_used'),used+8);return p+1;
  }
  tagged(value,cache=new Map()) {
    if(value===null)return 65;
    if(typeof value==='number')return (value*4)>>>0;
    if(cache.has(value))return cache.get(value);
    const p=this.allocate(value.car*4,65);cache.set(value,p);return p;
  }
  inputAddress(id,i) {return this.map.workers[id].input.start+Math.floor(i/8)*40+8+(i%8)*4;}
  prepare(args,{id=0,count=args.length,values=6,mode=0,policy=3,apply,fillHeap=false}={}) {
    const w=this.map.workers[id],cache=new Map();let head=w.output.start;
    const supplied=args.map(v=>this.tagged(v,cache));
    for(let i=0;i<32;i++)this.put(this.inputAddress(id,i),supplied[i]??65);
    if(apply) {
      let tail=apply.improper===undefined?65:this.tagged(apply.improper,cache);
      const list=apply.values.map(v=>this.tagged(v,cache));let last=0;
      for(const value of list.toReversed()){tail=this.allocate(value,tail);if(!last)last=tail;}
      if(apply.cycle&&last)this.put(last-1,tail);
      this.put(this.inputAddress(id,31),tail);
    }
    const blocks=Math.ceil((apply?32:Math.min(count,32))/8);
    for(let i=0;i<blocks;i++) {const p=w.input.start+i*40;this.put(p,head);this.put(p+4,8);head=p;}
    this.setField(id,'root_head',head);this.setField(id,'nvalues',0);
    this.put(w.output.start+4,0); // The TCR descriptor alone scans the active output region.
    for(let i=0;i<6;i++)this.put(w.output.start+8+i*4,65);
    const s=this.build.schema.state;for(const [name,v] of Object.entries({value_count:values,suspend:mode,policy}))this.put(w.state.start+s[name],v);
    if(fillHeap){const used=this.word(this.global('heap_used')),base=this.map.heaps[this.word(this.global('heap_active'))].start;for(let off=used;off<4096;off+=8){this.put(base+off,65);this.put(base+off+4,0);}this.put(this.global('heap_used'),4096);}
    this.baseline={vsp:this.field(id,'vsp'),root_head:head,roots:2+blocks,tsp:this.field(id,'tsp'),csp:this.field(id,'csp'),binding_depth:this.field(id,'binding_depth'),binding_cookie:this.field(id,'binding_cookie'),handler_cookie:this.field(id,'handler_cookie'),active_request:0};
    return supplied;
  }
  async late() {
    assert.ok(this.actors.every(a=>!a.busy));const w=this.map.workers[2];
    for(let i=0;i<8;i++)this.put(w.anchors.start+8+i*4,this.word(this.map.workers[0].anchors.start+8+i*4));
    this.main.publish_initial(w.tcr.start);const actor=new Actor(this,2);this.actors.push(actor);await actor.configure();this.initializeState(2);
    assert.equal(this.word(this.global('data_sentinel')),0x55667788);assert.equal(this.word(this.global('bss_sentinel')),0x99aabbcc);
  }
  readPacket(address) {
    assert.equal(this.word(address),0x41424931);const length=this.word(address+4);assert.ok(length>=32&&length<=8192&&length%4===0);
    const bytes=Buffer.from(new Uint8Array(this.memory.buffer,address,length)),v=Array.from(new Uint32Array(bytes.buffer,bytes.byteOffset,length/4));
    const p={address,bytes:bytes.toString('hex'),phase:v[2],collections:v[3],vsp:v[4],roots:v[5],frames:[]};let at=8;
    for(let i=0;i<v[6];i++) {
      const address=v[at++],header=v.slice(at,at+16);at+=16;const unavailable=v[at++],args=[],values=[];
      for(let n=0;n<header[12]+1;n++){args.push(v.slice(at,at+3));at+=3;}
      for(let n=0;n<header[13];n++){values.push(v.slice(at,at+3));at+=3;}
      assert.equal(header[0],1);assert.equal(header[1],512);assert.equal(header[11],136);assert.equal(header[14],address+112);
      assert.equal(header[10],header[4]>>>2);assert.equal(header[15],0);assert.ok(header[3]>0);assert.equal(unavailable,header[7]===1?1:0);
      const descriptor=this.candidate.debug.descriptors[header[4]>>>2];
      assert.ok(descriptor,'unknown logical code');assert.equal(header[5],descriptor.version);
      assert.ok(descriptor.source_sites[header[6]],'unknown debug source site');
      assert.equal(descriptor.bindings[0].offset,136);
      p.frames.push({address,header,args,values,unavailable,source:descriptor.source_sites[header[6]]});
    }
    assert.equal(at,v.length,'incomplete ABI inspection packet');this.packets.push(p);return p;
  }
  complete(ticket,{cancel=false,bytes}={}) {
    const q=this.q,p=ticket.address;
    assert.equal(this.word(p+q.generation),ticket.generation);assert.equal(this.word(p+q.outcome),0);
    if(bytes){assert.ok(bytes.length<=192);new Uint8Array(this.memory.buffer,p+q.payload,bytes.length).set(bytes);this.put(p+q.length,bytes.length);}
    this.put(p+q.outcome,cancel?2:1);this.put(p+q.result,37);
    const index=(p+q.wake)/8;const previous=Atomics.load(this.pairs,index);assert.equal(Number(previous>>32n),ticket.generation);
    assert.equal(Atomics.compareExchange(this.pairs,index,previous,(previous&0xffffffff00000000n)|2n),previous);Atomics.notify(this.words,(p+q.wake)/4);
  }
  interrupt(ticket,id) {
    const pending=this.map.workers[id].tcr.start+this.f.pending;Atomics.or(this.words,pending/4,2);
    const i=(ticket.address+this.q.wake)/8,old=Atomics.load(this.pairs,i);assert.equal(Number(old>>32n),ticket.generation);
    assert.equal(Atomics.compareExchange(this.pairs,i,old,(old&0xffffffff00000000n)|1n),old);Atomics.notify(this.words,(ticket.address+this.q.wake)/4);
  }
  async collect() {const done=await this.actors[1].simple('collect');this.collections.push(done);return done;}
  async run(anchor,count,{id=0,path=0,nested=false,nonlocal=false,collect=true}={}) {
    const a=this.actors[id],w=this.map.workers[id];this.setField(id,'mode',nonlocal?2:nested?1:0);
    a.command('start',[anchor,count,path]);let outer=null;
    for(;;) {
      const m=await a.next(m=>m.kind==='request'||m.kind==='done');
      if(m.kind==='done') {
        if(outer){this.complete(outer,{cancel:true});outer=null;}
        assert.equal(m.snapshot.tcr.state,1,'idle Worker did not park');assert.equal(m.snapshot.tcr.admitted,0);
        for(const [key,value] of Object.entries(this.baseline))if(key!=='roots')assert.equal(m.snapshot.tcr[key],value,'restoration '+key);
        assert.equal(m.snapshot.c_sp,w.stack.end,'C stack restoration');
        if(nonlocal)await this.collect();
        for(const p of this.packets)assert.equal(Buffer.from(new Uint8Array(this.memory.buffer,p.address,p.bytes.length/2)).toString('hex'),p.bytes,'inspection reply reused');
        return {...m,values:Array.from({length:m.snapshot.tcr.nvalues},(_,i)=>this.word(w.output.start+8+i*4))};
      }
      if(m.address>=w.replies.start&&m.address<w.replies.end){this.readPacket(m.address);continue;}
      assert.ok(m.address>=w.requests.start&&m.address<w.requests.end,'unknown request region');
      const t={address:m.address,generation:this.word(m.address+this.q.generation),opcode:this.word(m.address+this.q.opcode),code:m.lazy_code};this.io.push(t);
      if(collect)await this.collect();
      if((nested||nonlocal)&&!outer){outer=t;this.interrupt(t,id);continue;}
      if(t.opcode===2){const record=this.candidate.modules.find(e=>e.code===t.code);assert.ok(record);const bytes=Buffer.alloc(36);bytes.writeUInt32LE(t.code);Buffer.from(record.sha256,'hex').copy(bytes,4);this.complete(t,{bytes});}
      else this.complete(t);
      if(outer&&!nonlocal){this.complete(outer);outer=null;nested=false;}
    }
  }
  describe(v) {return v===65?'NIL':!(v&3)?(v|0)>>2:{car:(this.word(v+3)|0)>>2};}
  list(v) {const result=[],seen=new Set();while(v!==65){assert.ok((v&7)===1&&!seen.has(v),'invalid returned list');seen.add(v);result.push(this.describe(this.word(v+3)));v=this.word(v-1);assert.ok(result.length<=32);}return result;}
  evidence(done) {return {candidate:this.name,result:done,packets:this.packets,io:this.io,collections:this.collections,ownership:this.map};}
}
