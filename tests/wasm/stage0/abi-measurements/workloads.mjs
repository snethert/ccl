import assert from 'node:assert/strict';
export const workloads=['direct calls','unknown indirect callees','closures','optional/rest/keyword binding','APPLY',
  'multiple values','cross-arity tail chains','allocation with forced collection'];
export const mix=(h,v)=>Math.imul(h^v,16777619)>>>0;
export function rng(seed) { let x=seed>>>0||1;return ()=>{x^=x<<13;x^=x>>>17;x^=x<<5;return x>>>0;}; }
export function shuffle(values,random) { const a=[...values];for(let i=a.length-1;i>0;i--){const j=random()%(i+1);[a[i],a[j]]=[a[j],a[i]];}return a; }
const cell=(car,cdr=null)=>({car,cdr});
function anchor(i) {const a=cell([10,11,12,20,21,30,31,40][i]),env=cell(500+i*11,a);a.cdr=env;return a;}
const payload=v=>v===null?0:typeof v==='number'?v:v.car;
function fold(args,self,count) {
  const start=(self.car===11?2000:1000)+self.cdr.car;
  const sum=args.reduce((h,v,i)=>(h+Math.imul(payload(v),i+1))|0,start);
  return [((sum*4)|0)>>2,self,args[0]??null,args.at(-1)??null,self.cdr,args.length].slice(0,count);
}
function results(r) {
  let args=r.args.map((v,i)=>r.heap_argument&&i===0?cell(v):v),self=anchor(r.anchor);
  if(r.mode&16)self=cell(self.car,self.cdr);
  if(r.anchor===3) {
    let rest=null;for(const v of args.slice(4).toReversed())rest=cell(v,rest);
    return [args[0],args[1],args.length>2?args[2]:99,args.length>3?args[3]:77,rest,
      (args.length>2?1:0)+(args.length>3?2:0)].slice(0,r.values);
  }
  if(r.anchor===4) {
    const keys=new Map();for(let i=0;i<args.length;i+=2)if(!keys.has(args[i]))keys.set(args[i],args[i+1]);
    return [keys.get(1000)??99,keys.get(1001)??77,keys.has(1000)?1:null,keys.has(1001)?1:null,
      keys.has(1002)&&keys.get(1002)!==null?1:null,args.length].slice(0,r.values);
  }
  if(r.anchor===7) return [...fold(args,anchor(0),6).slice(0,3),...fold(args,anchor(1),6).slice(0,3)];
  if(r.anchor===5) args=[0,2]; // All declared chains have an even 2,000 transfers.
  return fold(args,self,r.values);
}
export function digest(value) {
  const queue=[];let h=2166136261,head=0,items=[value];
  for(;;) {
    for(const v of items) {
      if(v===null)h=mix(h,0);
      else if(typeof v==='number'){h=mix(h,1);h=mix(h,(v*4)>>>0);}
      else {let i=queue.indexOf(v);if(i<0){i=queue.length;queue.push(v);}assert.ok(queue.length<=64);h=mix(h,2);h=mix(h,i);}
    }
    if(head===queue.length)return h;
    const v=queue[head++];items=[v.car,v.cdr];
  }
}
export function observation(r) {
  const values=results(r);let h=mix(2166136261,values.length);h=mix(h,digest(values[0]??null));
  for(const v of values)h=mix(h,digest(v));return h;
}
export function schedule(workload,seed) {
  assert.ok(Number.isInteger(workload)&&workload>=0&&workload<8);const random=rng(seed);
  return Array.from({length:32},(_,i)=>{
    let n=[0,2,3,4,6,32][i%6];
    const r={anchor:0,args:[],prefix:null,values:6,mode:0,apply:false,heap_argument:false,indirect:workload===1,force_gc:workload===7};
    if(workload===1){r.anchor=random()%2;n=[2,3,4,6][i%4];}
    if(workload===2){r.anchor=random()%2;r.mode=16;n=[0,2,3,4,6][i%5];}
    if(workload===3){r.anchor=i%2?4:3;n=[2,3,4,6,32][Math.floor(i/2)%5];}
    if(workload===4){r.apply=true;r.prefix=i%2?2:0;n=[6,8,32][i%3];}
    if(workload===5){r.anchor=i%4===3?7:0;r.values=[0,1,6,6][i%4];r.force_gc=r.anchor===7;n=6;}
    if(workload===6){r.anchor=5;r.values=[0,1,6][i%3];n=2;}
    if(workload===7){r.anchor=3;r.heap_argument=true;n=32;}
    r.args=Array.from({length:n},()=>((random()%101)-50));
    if(r.anchor===4)r.args=i%4===1?[1001,17,1000,19,1000,23]:[1003,77,1002,1,1000,31];
    if(workload===6)r.args=[2000,2];
    r.prefix??=r.args.length;r.expected_observation=observation(r);return r;
  });
}
export function installSchedule(h,records) {
  assert.equal(records.length,32);h.prepare(Array(32).fill(null),{policy:1});
  const w=h.map.workers[0];h.put(w.state.start+72,w.schedule.start);
  for(const key of ['entry_count','tail_count','peak_vsp','peak_roots','cleanup_count','effects'])h.put(w.state.start+h.build.schema.state[key],0);
  records.forEach((r,i)=>{
    const p=w.schedule.start+i*256;
    [r.anchor,r.prefix,r.values,r.mode,r.apply?r.args.length:0,+r.heap_argument,+r.indirect,+r.force_gc].forEach((v,j)=>h.put(p+j*4,v));
    for(let j=0;j<32;j++)h.put(p+32+j*4,j<r.args.length?r.args[j]*4:65);
  });
}
export function expectedBatch(records,iterations,offset=0) {
  let h=2166136261;for(let i=0;i<iterations;i++)h=mix(h,records[(i+offset)&31].expected_observation);return h;
}
export async function batch(h,records,iterations,offset=0) {
  const before=h.word(h.global('world_completed')),state=h.map.workers[0].state.start,s=h.build.schema.state;
  const cleanupBefore=h.word(state+s.cleanup_count),tailBefore=h.word(state+s.tail_count);
  const r=await h.actors[0].simple('batch',[iterations,offset]);
  assert.deepEqual(r.result.map(v=>v>>>0),[expectedBatch(records,iterations,offset),iterations],'BATCH_COMPLETE_RESULT_ORACLE');
  assert.equal(r.snapshot.state.error,0);assert.equal(r.snapshot.tcr.state,1);assert.equal(r.snapshot.tcr.admitted,0);
  for(const [key,value] of Object.entries(h.baseline))if(key!=='roots')assert.equal(r.snapshot.tcr[key],value,'batch restoration '+key);
  assert.equal(r.snapshot.c_sp,h.map.workers[0].stack.end);
  assert.equal((r.snapshot.state.cleanup_count-cleanupBefore)>>>0,iterations,'batch cleanup count');
  const tails=Array.from({length:iterations},(_,i)=>records[(i+offset)&31]).reduce((n,r)=>n+(r.anchor===5?r.args[0]:0),0);
  assert.equal((r.snapshot.state.tail_count-tailBefore)>>>0,tails,'batch tail count');
  assert.ok(r.snapshot.state.peak_vsp-h.baseline.vsp<=1088,'batch explicit stack grew');
  assert.ok(r.snapshot.state.peak_roots<=13,'batch root chain grew');
  const collections=h.word(h.global('world_completed'))-before;
  const forced=Array.from({length:iterations},(_,i)=>+records[(i+offset)&31].force_gc).reduce((a,b)=>a+b,0);
  assert.ok(collections>=forced,'forced collection did not execute');
  assert.ok(r.elapsed_ms>0&&Number.isFinite(r.elapsed_ms));
  return {iterations,offset,elapsed_ms:r.elapsed_ms,hash:r.result[0]>>>0,collections,
    entries:r.snapshot.state.entry_count,tails:r.snapshot.state.tail_count,cleanup:r.snapshot.state.cleanup_count,
    peak_stack_bytes:r.snapshot.state.peak_vsp-h.baseline.vsp,peak_root_records:r.snapshot.state.peak_roots,
    c_sp:r.snapshot.c_sp};
}
