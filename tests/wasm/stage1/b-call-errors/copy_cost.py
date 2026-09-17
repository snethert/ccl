"""Count executed memory.copy operations in a labelled observation derivative.

Production binaries remain unchanged. Each Wasm memory.copy is wrapped by an
observer which performs that same instruction after reporting its three operands.
This derivative is never offered to the production loader or used as gate evidence.
"""
import subprocess,re
from pathlib import Path
from support import HERE,require,read,save

def run(positive,out):
 require(not out.exists(),'NO_OVERWRITE');out.mkdir(parents=True);(out/'installed').mkdir()
 for name in ('modules.json','cases.json','root-contracts.json'):(out/name).write_bytes((positive/name).read_bytes())
 for p in (positive/'installed').glob('*.wasm'):
  if p.stem.startswith('observe_'):(out/'installed'/p.name).write_bytes(p.read_bytes());continue
  wat=(positive/(p.stem+'.wat')).read_text()
  require(wat.count('(import "env" "memory"')==1,'COPY_IMPORT_SITE')
  # Observe the direct result handoff before and after the destructive copy.
  # The expected surviving descriptor comes from recipient metadata, not root_head.
  a=wat.index('(func $rv_deliver ');b=wat.index('(func $rv_release ',a)
  fragment=wat[a:b];copy='(memory.copy (local.get $dst) (local.get $src) (i32.mul (local.get $n) (i32.const 4)))'
  before='(call $handoff_event (local.get $d) (local.get $dst) (local.get $n) (i32.const 0))'
  after='(call $handoff_event (local.get $d) (local.get $dst) (local.get $n) (i32.const 1))'
  require(copy in fragment,'HANDOFF_SITE');fragment=fragment.replace(copy,before+copy+after,1);wat=wat[:a]+fragment+wat[b:]
  wat=wat.replace('(memory.copy ', '(call $copy_observed ')
  wat=wat.replace('(import "env" "memory"','(import "copyprobe" "handoff" (func $handoff_event (param i32 i32 i32 i32))) (import "copyprobe" "event" (func $copy_event (param i32 i32 i32))) (import "env" "memory"')
  end=wat.rfind(')');wat=wat[:end]+'''(func $copy_observed (param $d i32) (param $s i32) (param $n i32)
   (call $copy_event (local.get $d) (local.get $s) (local.get $n))
   (memory.copy (local.get $d) (local.get $s) (local.get $n)))'''+wat[end:]
  source=out/(p.stem+'.wat');source.write_text(wat)
  subprocess.run(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',str(source),'-o',str(out/'installed'/p.name)],check=True,capture_output=True)
 script=(HERE/'execute.mjs').read_text()
 script=script.replace('const observations=[];', 'let copyEvents=[];const copyRows=[];const handoffs=[];let handoffBefore=null;const observations=[];')
 script=script.replace('{env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},symbols,keywords,codes}', '{copyprobe:{event:(dst,src,bytes)=>{if(bytes)copyEvents.push({module:m.name,dst:u32(dst),src:u32(src),bytes:u32(bytes)});},handoff:(d,dst,n,stage)=>{const root=load(u32(d)+24);assert.equal(get(128),root,"handoff surviving root");assert(root+48<=u32(dst),"handoff descriptor outside arguments");inspect("handoff "+stage);const words=Array.from({length:12},(_,i)=>load(root+4*i));if(!stage)handoffBefore=words;else {assert.deepEqual(words,handoffBefore,"handoff descriptor preserved");handoffs.push({module:m.name,root,dst:u32(dst),count:u32(n)});}}},env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},symbols,keywords,codes}')
 require('copyprobe:{event:' in script,'COPY_HARNESS_IMPORT')
 script=script.replace('for(const c of cases){', 'for(const c of cases.filter(c=>["rv_small","rv_inline","rv_large_dynamic","rv_ordered"].includes(c.id))){copyEvents=[];')
 script=script.replace("inspect('returned '+c.id);", "inspect('returned '+c.id);const large=copyEvents.filter(e=>e.bytes===520);assert.equal(large.length,c.id==='rv_inline'?2:3,c.id+': no intermediate result copy');assert(!copyEvents.some(e=>e.dst===e.src),c.id+': no identity copy');copyRows.push({id:c.id,start,observed,copies:copyEvents});")
 script=script.replace('  // Host-turn escape:', '  continue;\n  // Host-turn escape:')
 script=script.replace("parentPort.postMessage({status:'PASS',", "parentPort.postMessage({status:'PASS',copyRows,handoffs,")
 (out/'observe.mjs').write_text(script)
 argv=['/usr/local/bin/node',str(out/'observe.mjs'),str(out),str(out/'observations.json')];save(out/'command.json',argv)
 with (out/'execution.log').open('w')as log:result=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=120)
 require(result.returncode==0,'COPY_COST '+str(out/'execution.log'))
 observations=read(out/'observations.json');rows=observations['copyRows'];require(len(rows)==16,'COPY_CASES');require(len(observations['handoffs'])==8,'HANDOFF_CASES')
 summary={'status':'PASS','cases':len(rows),'handoffs':len(observations['handoffs']),'expected_520_byte_copies':{'rv_small':3,'rv_inline':2,'rv_large_dynamic':3,'rv_ordered':3},'scope':'Counts include VALUES operand staging and the legitimate tail argument transfer; no intermediate return-area or identity copy. Explicit observation derivative, not a loader-qualified binary.'}
 save(out/'summary.json',summary);return summary
