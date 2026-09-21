from pathlib import Path
PARENT=Path(__file__).resolve().parent.parent/'startup-runtime'
def replace(s,a,b,count=1):
 assert s.count(a)==count,(a,s.count(a));return s.replace(a,b)
def service():
 s=(PARENT/'service.mjs').read_text()
 return replace(s,'  const values=owner.gctime(units);', '''  // An unavailable clock is data at the host boundary. Generated Lisp turns
  // this NIL snapshot into the owner's SIMPLE-ERROR condition.
  if(!owner.statistics.timingValid){[NIL,NIL,1,0].forEach((w,i)=>v.setUint32(pub+4*i,w,true));return 0;}
  const values=owner.gctime(units);''')
def compile_source():
 s=(PARENT/'compile.lisp').read_text()
 s=replace(s,'0 1 499 500 501','0 1 2147483647 2147483648 3000000000 4294967295 9223372036854775808 3000000000000 499 500 501')
 values='(values (svref v 0) (svref v 1) (svref v 2) (svref v 3) (svref v 4))'
 s=replace(s,values,'(locally (declare (special statistics_error)) (if v '+values+' (error statistics_error)))',2)
 s=replace(s,'                )))', '''                ("gctime_caught" (lambda (fn snapshot owner done) (handler-case (unwind-protect (funcall fn snapshot owner) (rplaca done 611)) (simple-error (c) (values 701 (car done))) (error (c) 702))))
                ("gctime_named_caught" (lambda (done) (handler-case (unwind-protect (gctime) (rplaca done 611)) (simple-error (c) (values 701 (car done))) (error (c) 702))))
                )))''')
 return s

def check():
 s=(PARENT/'check.mjs').read_text()
 s=replace(s,"import {sha256} from './sha256.mjs';", "import {sha256} from './sha256.mjs';\nimport {installConditions} from './conditions.mjs';")
 s=replace(s,'comparisons=0,collections=0;', 'comparisons=0,collections=0;let clockBroken=false;')
 s=replace(s,"['image',800000,800016],", "['image',800000,800016],") # assertion of parent anchor
 s=replace(s,"  const layout={version:1,", "  const conditionData=installConditions(put,N);regions.push({name:'condition-image',role:'image',start:810000,end:conditionData.end});\n  const layout={version:1,")
 # The new image is materialized before admission, after the generic zero fill.
 s=replace(s,'  put(N-1,N);', '  installConditions(put,N);\n  put(N-1,N);')
 s=replace(s,'[104,BINDINGS],[108,0]', '[104,BINDINGS],[108,4]')
 s=replace(s,'  clock=0n;step=0n;', '  for(let i=0;i<4;i++)put(BINDINGS+4*i,243);\n  clockBroken=false;clock=0n;step=0n;')
 s=replace(s,'const n=clock;clock+=step;return n;', 'if(clockBroken)throw Error("unavailable clock");const n=clock;clock+=step;return n;')
 s=replace(s,"return [i.name,symbolNames.get(i.name)];", "return [i.name,i.name==='condition_registry'?conditionData.registry:i.name==='error_message'?conditionData.message:symbolNames.get(i.name)];")
 s=replace(s,"   if(name==='gctime_snapshot')", "   if(name==='condition_handlers')put(p+22,4);\n   if(name==='statistics_error')put(p+2,conditionData.condition);\n   if(name==='gctime_snapshot')")
 s=replace(s,'return n;}\n function call', '''if(get(p-2+4*((h>>>8)-1))&0x80000000)n-=1n<<BigInt(32*(h>>>8));return n;}
 function call''')
 needle=' // Bad clocks cannot turn a committed collection into an apparent refusal.'
 s=replace(s,needle,''' // Each runtime admission predicate must alone decide its directed refusal.
 const directed=[];
 for(const [name,change] of [
  ['table',a=>a[0]+=8],['end',a=>a[1]+=8],['operation',a=>a[2]=4],
  ['first operand',a=>a[3]=T],['second operand',a=>a[4]=T],
  ['publication',a=>a[7]+=32],['header',()=>put(DESC-6,506)],
 ]){
  const leaf=setup(),args=[DESC,DESC+2,5,N,N,0,0,RESULT];change(args);
  const areas=[[TCR,256],[DESC-6,64],[RESULT,64],[base,128],[base+32768,128]];
  const before=areas.map(([p,n])=>new Uint8Array(memory.buffer,p,n).slice());
  const status=leaf(...args);assert.equal(status,4,'admission '+name);
  areas.forEach(([p,n],i)=>assert.deepEqual(new Uint8Array(memory.buffer,p,n),before[i],'admission preservation '+name));directed.push(name);
 }
 // Exercise both backwards and throwing clocks through generated handlers.
 // Native GCTIME has no clock-failure case: this is an explicit owner-error
 // path, whose Lisp SIMPLE-ERROR/cleanup semantics are the compatibility claim.
 const failures=[];
 for(const mode of ['backwards','throws'])for(const named of [false,true]){
  setup(4096);clockBroken=mode==='throws';step=mode==='backwards'?-1n:0n;clock=100n;
  owner.atSafepoint(o=>o.collect());assert.equal(owner.statistics.timingValid,false);
  const f=compiled.find(m=>m.name==='gctime_port').id;
  assert.deepEqual(named?call('gctime_named_caught',[DONE]):call('gctime_caught',[object(f),object(1),DESC,DONE]),[701n,611n],'timing failure Lisp condition');
  assert.equal(get(DONE+3),611*4);assert.equal(t(112),0);assert.equal(get(BINDINGS+4),243);failures.push({mode,named,condition:'SIMPLE-ERROR',cleanup:611});
 }
'''+needle)
 s=replace(s,'rows,checks:8}', 'rows,checks:8,directed,failures}')
 return s
