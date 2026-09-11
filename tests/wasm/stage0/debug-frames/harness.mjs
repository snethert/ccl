import assert from 'node:assert/strict';
import {Harness} from '../integrated-runtime/harness.mjs';
import {validateMap} from '../runtime-boundary/runtime.mjs';
import {sha} from './build.mjs';

export class FrameHarness extends Harness {
  constructor(build,options={}) {
    super({...build,program:options.programMutant?build.programMutants[options.programMutant]:build.program},options);
    this.frameSchema=build.frameSchema;this.sourceMap=build.sourceMap;
    assert.equal(sha(Buffer.from(build.sourceLines.join('\n'))),build.sourceMap.source_sha256);
    assert.equal(build.sourceMap.build_id,build.buildId);
    for(const site of Object.values(build.sourceMap.sites))
      assert.equal(build.sourceLines[site.line-1].trim(),site.text);
    this.buildId=options.mutant?build.mutants[options.mutant].buildId:build.buildId;
  }
  async reset() {
    await super.reset();this.replies=[];this.expected=null;
    let next=Math.ceil(this.map.usedEnd/16)*16;
    const allocate=(name,bytes)=>{const r={name,start:next,end:next+bytes,alignment:16};next=r.end;this.map.regions.push(r);return r;};
    for(const w of this.map.workers) {
      w.frames=allocate(`worker-${w.id}-logical-frames`,this.frameSchema.frame_capacity*160);
      w.replies=allocate(`worker-${w.id}-inspection-replies`,this.frameSchema.reply_capacity*4096);
    }
    this.map.usedEnd=next;validateMap(this.map,this.memory.buffer.byteLength);
    for(const w of this.map.workers)
      await this.actors[w.id].run('debug_setup',[w.frames.start,w.frames.end,w.replies.start,w.replies.end]);
    // Initial fixture handoff while every Worker is parked: captured cell moves
    // from worker 2 to worker 0, survives the frames, and remains observable later.
    this.put(this.field(0,'root_slot')+4,this.childRoot);
    this.put(this.field(2,'root_slot'),65);this.put(this.field(2,'root_slot')+4,65);
  }
  readReply(message) {
    const range=this.map.workers[message.id].replies,p=message.address;
    assert.ok(p>=range.start&&p+4096<=range.end,'inspection reply outside stable owned storage');
    const length=this.word(p+4); // Acquire the C publisher's final atomic length store.
    assert.equal(this.word(p),0x44424731,'reply magic');assert.ok(length>=48&&length<=4096&&length%4===0);
    const bytes=Buffer.from(new Uint8Array(this.memory.buffer,p,length));
    const words=Array.from(new Uint32Array(bytes.buffer,bytes.byteOffset,length/4));
    assert.equal(words.slice(4,12).map(w=>w.toString(16).padStart(8,'0')).join(''),this.buildId,'inspection build identity mismatch');
    const reply={address:p,bytes:bytes.toString('hex'),sha256:sha(bytes),kind:words[2],phase:words[3],expected:{...this.expected},frames:[]};
    if(reply.kind===2||reply.kind===3) {
      assert.equal(length,60);reply.valid=words[3];reply.handle={address:words[12],generation:words[13],lifetime:words[14]};
    } else {
      assert.equal(reply.kind,1);reply.nvalues=words[12];reply.head=words[13];reply.gc=words[15];
      let at=16;reply.values=[];
      for(let i=0;i<reply.nvalues;i++){reply.values.push(words.slice(at,at+3));at+=3;}
      for(let i=0;i<words[14];i++) {
        const [address,generation,code_id,version,site,policy,previous,binding_checkpoint,handler_checkpoint,argc,nvalues,nslots]=words.slice(at,at+12);at+=12;
        const slots=[];for(let j=0;j<nslots;j++){const [lexical_id,availability,storage,...value]=words.slice(at,at+6);at+=6;slots.push({lexical_id,availability,storage,value});}
        reply.frames.push({address,generation,code_id,version,site,policy,previous,binding_checkpoint,handler_checkpoint,argc,nvalues,slots});
      }
      assert.equal(at,words.length,'truncated or trailing inspection data');
    }
    this.replies.push(reply);return reply;
  }
  async ioRequest(id=0) {
    for(;;) {
      const m=await this.actors[id].next(m=>m.kind==='request');
      const range=this.map.workers[id].replies;
      if(m.address>=range.start&&m.address<range.end) {this.readReply(m);continue;}
      const requests=this.map.requests[id];
      assert.ok(m.address>=requests.start&&m.address<requests.end,'unknown host request storage');
      this.actors[id].inbox.unshift(m);return this.request(id);
    }
  }
  drainReplies(id=0) {
    const actor=this.actors[id];
    const messages=actor.inbox.filter(m=>m.kind==='request');actor.inbox=actor.inbox.filter(m=>m.kind!=='request');
    for(const m of messages)this.readReply(m);
  }
  immutableReplies() {
    for(const r of this.replies)
      assert.equal(Buffer.from(new Uint8Array(this.memory.buffer,r.address,r.bytes.length/2)).toString('hex'),r.bytes,'published inspection reply changed');
  }
  frameHeaderOracle(expectedCodes) {
    // Deliberately literal offsets and expected bytes: independent of the schema writer and C reader.
    const frames=[];let address=this.field(0,'frame_head');
    for(const code of expectedCodes) {
      const range=this.map.workers[0].frames;assert.ok(address>=range.start&&address+160<=range.end);
      const w=Array.from(new Uint32Array(this.memory.buffer,address,40));
      assert.equal(w[0],1);assert.equal(w[1],160);assert.equal(w[4],code*4);
      assert.equal(w[10],code);assert.equal(w[11],72);assert.equal(w[12],2);
      assert.equal(w[13],this.expected.count);assert.equal(w[14],this.map.workers[0].tcr.start+44);assert.equal(w[15],0);
      assert.equal(w[17],6);assert.equal(w[19],code===43?(-28>>>0):44);assert.equal(w[25],0xdeadbeef);
      const depth=expectedCodes.length-frames.length-1;
      assert.equal(w[8],this.expected.tsp+depth*4,'wrong binding checkpoint');
      assert.equal(w[9],this.expected.csp+depth*4,'wrong handler checkpoint');
      const x=code===41?440+this.expected.version*4:code===42?888:1332;
      assert.equal(this.word(w[8]),x,'binding record not materialized');
      assert.equal(this.word(w[9]),code,'handler record not materialized');
      assert.equal(w[23],w[18]); // hidden root aliases self; debug availability cannot erase it.
      frames.push({address,header_words:w.slice(0,16),payload_words:w.slice(16,26)});address=w[2];
    }
    assert.equal(address,0,'extra logical frame');return frames;
  }
  verifyReplies() {
    const births=new Map();
    for(const reply of this.replies) {
      if(reply.kind===3) {assert.equal(reply.valid,1,'live frame handle was rejected');continue;}
      if(reply.kind===2) {assert.equal(reply.valid,0,'stale frame handle was accepted after storage reuse');continue;}
      const e=reply.expected;
      const ids=reply.frames.map(f=>f.code_id/4);
      const wanted=({1:[42,41],2:[42,41],3:[43,42,41],4:[43,42,41],5:[41],6:[],7:[],8:Array(8).fill(41),9:Array(8).fill(41)})[reply.phase];
      assert.deepEqual(ids,wanted,'frame order or frame head was not restored');
      assert.equal(reply.nvalues,e.count,'lost complete multiple-value count');
      assert.equal(reply.values.length,e.count);
      if(e.count) {
        assert.deepEqual(reply.values.map(v=>[v[1],v[2]]),[[1,4],[1,-28>>>0],[2,400],[2,404],[1,0],[1,2147483644]],'complete inspection values changed');
      }
      for(const [i,f] of reply.frames.entries()) {
        const code=f.code_id/4,version=code===41?e.version:1;
        assert.equal(f.version,version,'live code/debug version mismatch');
        const meta=this.frameSchema.codes.find(c=>c.id===code&&c.version===version);
        assert.ok(meta&&meta.sites[f.site],'source-site metadata mismatch');
        const source=this.sourceMap.sites[f.site];assert.ok(source,'missing build-bound source site');
        assert.equal(source.function,reply.phase>=8?'deep_run':code===41?'run':code===42?'inner':'debugger');
        assert.ok(source.text.includes(source.operation==='recursive-call'?'(call $deep_run':source.operation==='inner-call'?'(call $inner':source.operation==='resumed-inspection'?'(call $inspect':'(call $suspend'));
        const depth=reply.frames.length-i-1;
        assert.equal(f.binding_checkpoint,e.tsp+depth*4,'wrong serialized binding checkpoint');
        assert.equal(f.handler_checkpoint,e.csp+depth*4,'wrong serialized handler checkpoint');
        const site=reply.phase>=8?(i===0?(reply.phase===8?4142:4143):4141):code===41?(version===1?((reply.phase===5||reply.phase===9&&i===0)?4102:4101):(reply.phase===5?4112:4111)):
          code===42?(reply.phase===2?4202:4201):(reply.phase===4?4302:4301);
        assert.equal(f.site,site,'caller did not publish the actual suspended call site');
        assert.equal(f.policy,e.policy);assert.equal(f.argc,2);assert.equal(f.nvalues,e.count);
        assert.equal(f.previous,reply.frames[i+1]?.address||0);
        assert.ok(f.generation>0);assert.equal(f.slots.length,8);
        const x=code===41?440+version*4:code===42?888:1332;
        for(const [j,s] of f.slots.entries()) {
          const binding=meta.bindings[j];
          assert.equal(s.lexical_id,binding.lexical_id,'shadowed lexical identity changed');
          assert.equal(binding.display_name,this.frameSchema.slot_order[j]);
          assert.equal(this.frameSchema.availability[binding.availability_by_policy[e.policy]],s.availability,'unavailable value was fabricated');
          const unavailable=j===7?2:(e.policy===1&&j===3?1:(e.policy===1&&j===5?3:0));
          assert.equal(s.availability,unavailable,'unavailable value was fabricated');
          assert.equal(s.storage,j===7?0:j===6?2:1);
          if(unavailable) {assert.deepEqual(s.value,[0,0,0],'unavailable slot leaked a stale/fabricated value');continue;}
          if(j===6) {assert.equal(s.value[1],3);continue;}
          const kind=j===1||j===3?1:2, payload=j===1?(code===43?(-28>>>0):44):j===3?x:j===4?800:400;
          assert.deepEqual(s.value.slice(1),[kind,payload],'inspected lexical value changed');
        }
        const key=f.address+':'+f.generation;
        if(!births.has(key))births.set(key,f.slots[6].value[0]);
        assert.equal(f.slots[6].value[0],births.get(key),'raw non-root slot was relocated');
      }
    }
    this.immutableReplies();
  }
  evidence(extra={}) {return super.evidence({...extra,inspection_replies:this.replies,ownership:this.map});}
}
