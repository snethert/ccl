from pathlib import Path

def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def derive(source):
 s=source
 s=replace(s,"assert.equal(all.length,7)","assert.equal(all.length,20)")
 s=replace(s," const destinations=[[],[0],[1],[2],[3,4,5],[6,7,8],[]];", """ const resets=read(dir,'resets.json');assert.equal(resets.length,13);
 assert.equal(resets[0].name,'CCL::*CPU-COUNT*');assert.equal(resets[0].module,'reset_5568');
 const resetIndex=j=>j===0?8:j+8;
 const sequence=['preflight',...resets.map(r=>r.module),...names.slice(1)];
 const destinations=[[],[0],[1],[2],[3,4,5],[6,7,8],[]];
 const stateAll=()=>Array.from({length:21},(_,j)=>decode(get(symbol(j)+2)));
 const membership=p=>assert.deepEqual(p.initializers.map(r=>r.id).slice().sort(),sequence.slice().sort(),'SELECTED_MEMBERSHIP');
 let resetAnswers=[],splitCache=false;""")
 s=replace(s,"sentinel===37?'nil':cfg.cpuCount===1?2:1];","cfg.cpuCount===1?2:1,...Array(12).fill(sentinel)];")
 s=replace(s,'for(let i=0;i<7;i++){put(S+8*i,NIL);','for(let i=0;i<20;i++){put(S+8*i,NIL);')
 s=replace(s,'answers=[];workload=null;preflight=null;return initial;','answers=[];resetAnswers=[];workload=null;preflight=null;return initial;')
 start=s.index(' function plan(initial){');end=s.index(' function invoke(entry,row){',start)
 s=s[:start]+''' function plan(initial){
  const state=initial.slice(),steps=[];
  const updates=[[],[[0,cfg.pageSize]],[[1,cfg.ticks]],[[2,cfg.period]],cfg.active?[[3,cfg.stackSize],[4,cfg.stackSize],[5,cfg.half]]:[],[[6,cfg.cpuCount===1?1:1024],[7,0],[8,cfg.cpuCount]],[]];
  sequence.forEach((name,at)=>{
   const i=names.indexOf(name),j=resets.findIndex(r=>r.module===name);
   const before=state.map((value,j)=>({address:symbol(j)+2,value:encode(value)}));
   if(j>=0)state[resetIndex(j)]=resets[j].value;
   else for(const [k,value]of updates[i])state[k]=value;
   steps.push({id:name,module:name,sha256:all.find(m=>m.name===name).record.sha256,
    phase:name==='preflight'?0:name==='workload'?2:1,
    prerequisites:at?[sequence[at-1]]:[],completion:{address:S+8*at+4,value:4*(j>=0?201+j:100+i)},before,
    after:state.map((value,j)=>({address:symbol(j)+2,value:encode(value)}))});
  });
  return {version:1,state:{start:base+1024,size:S+160-(base+1024)},ready:READY,initializers:steps};
 }
''' +s[end:]
 s=replace(s,"const i=names.indexOf(row.id),index=all.findIndex(m=>m.name===row.module),done=S+8*i+1;", "const i=names.indexOf(row.id),j=resets.findIndex(r=>r.module===row.id),index=all.findIndex(m=>m.name===row.module),done=row.completion.address-3;")
 s=replace(s,'symbol(8),done]:','symbol(splitCache?9:8),done]:')
 s=replace(s,'const args=i===0||i===6?', 'const args=j>=0?[symbol(resetIndex(j)),done]:i===0||i===6?')
 s=replace(s,'for(const j of destinations[i])','for(const j of (i<0?[resetIndex(resets.findIndex(r=>r.module===row.id))]:destinations[i]))')
 s=replace(s,"if(i===0)preflight=values;else if(i===6)workload=values;else answers.push({values,globals:globals()});", "if(j>=0)resetAnswers.push({name:row.id,values,globals:resets.map((_,k)=>decode(get(symbol(resetIndex(k))+2)))});else if(i===0)preflight=values;else if(i===6)workload=values;else answers.push({values,globals:globals()});")
 s=replace(s,'for(let i=0;i<9;i++){const p=symbol(i);','for(let i=0;i<21;i++){const p=symbol(i);')
 start=s.index(' const rows=[];')
 s=s[:start]+''' const rows=[],nativeResets=read(dir,'native-resets.json');
 for(const [ci,c]of cases.entries())for(const [ri,sentinel]of [37,91].entries()){
  const initial=reset(c.input,sentinel),p=plan(initial),a=adapter();membership(p);
  const owner=new BootstrapSchedule({memory,plan:p,digest:sha(JSON.stringify(p)),modules:all});
  const events=owner.run(a.install);
  // CPU is deliberately warm before reset, then the actual generated reset
  // clears the SAME cell consumed by config_5566. No host fixup between calls.
  assert.deepEqual(preflight,initial.slice(0,9));
  assert.equal(resetAnswers[0].values[0],'nil','native reset return');
  for(let j=0;j<13;j++){
   assert.deepEqual(resetAnswers[j].values,nativeResets[ri][j].values,'native reset values');
   assert.deepEqual(resetAnswers[j].globals,nativeResets[ri][j].globals,'native reset globals');
  }
  const wanted=structuredClone(native[ci][0]);
  // Reused native cold-cache formulas started with sentinel 37. Other globals
  // retain the dirty state's sentinel until their own initializer writes them.
  const prior=[sentinel,sentinel,sentinel,...c.input.defaults,sentinel,sentinel,'nil'];
  for(let step=0;step<5;step++){
   for(const k of destinations[step+1])prior[k]=wanted[step].globals[k];
   wanted[step].globals=prior.slice();
  }
  assert.deepEqual(answers,wanted,'joined native configuration effects');
  assert.deepEqual(workload,wanted[4].globals,'generated readback');
  assert.deepEqual(stateAll().slice(9),resets.slice(1).map(r=>r.value),'reset effects survive configuration');
  assert.equal(get(READY),1);assert.equal(get(READY+4),20);assert.equal(owner.state,'READY');
  assert.deepEqual(a.installed().map(r=>r.name),sequence);
  for(const r of a.installed())assert.equal(r.sha256,all.find(m=>m.name===r.name).record.sha256);
  rows.push({name:c.name,sentinel,initial,resetAnswers:structuredClone(resetAnswers),answers:structuredClone(answers),workload,events,installed:a.installed()});
 }
 const refusals=[];
 const fresh=()=>{const initial=reset(cases[0].input,37);return plan(initial);};
 for(const name of sequence){
  const p=fresh();assert.throws(()=>new BootstrapSchedule({memory,plan:p,digest:sha(JSON.stringify(p)),modules:all.filter(m=>m.name!==name)}),/MODULE_SET/);
  assert.equal(get(READY),0);refusals.push({name:'module omission '+name,reason:'MODULE_SET'});
  const q=fresh();q.initializers=q.initializers.filter(r=>r.id!==name);
  assert.throws(()=>membership(q),/SELECTED_MEMBERSHIP/);assert.equal(get(READY),0);refusals.push({name:'matching plan omission '+name,reason:'SELECTED_MEMBERSHIP'});
 }
 for(const [name,target,action,reason]of [
  ['skip CPU reset','reset_5568','skip','COMPLETION_MISSING'],
  ['forge CPU completion','reset_5568','forge','POSTCONDITION'],
  ['separate CPU cell','config_5566','split','POSTCONDITION'],
  ['missing spin completion','config_5566','completion','COMPLETION_MISSING'],
  ['late reset corrupts cache','config_5566','cache','POSTCONDITION'],
 ]){
  const p=fresh(),a=adapter(),owner=new BootstrapSchedule({memory,plan:p,digest:sha(JSON.stringify(p)),modules:all});
  assert.throws(()=>owner.run((m,r)=>{
   const fn=a.install(m,r);
   if(r.id!==target)return fn;
   if(action==='skip')return()=>{};
   if(action==='forge')return()=>put(r.completion.address,r.completion.value);
   // A cache alias error in the owner is caught before invoking spin.
   if(action==='split')return()=>{splitCache=true;try{fn();}finally{splitCache=false;}};
   return()=>{fn();if(action==='completion')put(r.completion.address,0);else put(symbol(8)+2,NIL);};
  }),new RegExp(reason));assert.equal(owner.state,'FAILED');assert.equal(get(READY),0);
  refusals.push({name,reason});
 }
 return {base,rows,refusals,invocations,foreignChecks};
}
'''
 # Reset native history starts with all dirty cells, except the CPU cell which
 # is reset first; its post-state then matches the retained sequence exactly.
 return s
