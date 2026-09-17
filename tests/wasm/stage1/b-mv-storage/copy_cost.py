"""Count executed memory.copy operations in a labelled observation derivative.

Production binaries remain unchanged. Each Wasm memory.copy is wrapped by an
observer which performs that same instruction after reporting its three operands.
This derivative is never offered to the production loader or used as gate evidence.
"""
import subprocess
from pathlib import Path
from support import HERE,require,read,save

def run(positive,out):
 require(not out.exists(),'NO_OVERWRITE');out.mkdir(parents=True);(out/'installed').mkdir()
 for name in ('modules.json','cases.json','root-contracts.json'):(out/name).write_bytes((positive/name).read_bytes())
 for p in (positive/'installed').glob('*.wasm'):
  if p.stem.startswith('observe_'):(out/'installed'/p.name).write_bytes(p.read_bytes());continue
  wat=(positive/(p.stem+'.wat')).read_text()
  require(wat.count('(import "env" "memory"')==1,'COPY_IMPORT_SITE')
  wat=wat.replace('(memory.copy ', '(call $copy_observed ')
  wat=wat.replace('(import "env" "memory"','(import "copyprobe" "event" (func $copy_event (param i32 i32 i32))) (import "env" "memory"')
  end=wat.rfind(')');wat=wat[:end]+'''(func $copy_observed (param $d i32) (param $s i32) (param $n i32)
   (call $copy_event (local.get $d) (local.get $s) (local.get $n))
   (memory.copy (local.get $d) (local.get $s) (local.get $n)))'''+wat[end:]
  source=out/(p.stem+'.wat');source.write_text(wat)
  subprocess.run(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',str(source),'-o',str(out/'installed'/p.name)],check=True,capture_output=True)
 script=(HERE/'execute.mjs').read_text()
 script=script.replace('const observations=[];', 'let copyEvents=[];const copyRows=[];const observations=[];')
 script=script.replace('{env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},symbols,keywords,codes}', '{copyprobe:{event:(dst,src,bytes)=>{if(bytes)copyEvents.push({module:m.name,dst:u32(dst),src:u32(src),bytes:u32(bytes)});}},env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},symbols,keywords,codes}')
 require('copyprobe:{event:' in script,'COPY_HARNESS_IMPORT')
 script=script.replace('for(const c of cases){', 'for(const c of cases.filter(c=>["rv_small","rv_inline","rv_large_dynamic","rv_ordered"].includes(c.id))){copyEvents=[];')
 script=script.replace("inspect('returned '+c.id);", "inspect('returned '+c.id);const large=copyEvents.filter(e=>e.bytes===520);assert.equal(large.length,c.id==='rv_inline'?2:3,c.id+': no intermediate result copy');assert(!copyEvents.some(e=>e.dst===e.src),c.id+': no identity copy');copyRows.push({id:c.id,start,observed,copies:copyEvents});")
 script=script.replace('  // Host-turn escape:', '  continue;\n  // Host-turn escape:')
 script=script.replace("parentPort.postMessage({status:'PASS',", "parentPort.postMessage({status:'PASS',copyRows,")
 (out/'observe.mjs').write_text(script)
 argv=['/usr/local/bin/node',str(out/'observe.mjs'),str(out),str(out/'observations.json')];save(out/'command.json',argv)
 with (out/'execution.log').open('w')as log:result=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=120)
 require(result.returncode==0,'COPY_COST '+str(out/'execution.log'))
 rows=read(out/'observations.json')['copyRows'];require(len(rows)==16,'COPY_CASES')
 summary={'status':'PASS','cases':len(rows),'expected_520_byte_copies':{'rv_small':3,'rv_inline':2,'rv_large_dynamic':3,'rv_ordered':3},'scope':'Counts include VALUES operand staging and the legitimate tail argument transfer; no intermediate return-area or identity copy. Explicit observation derivative, not a loader-qualified binary.'}
 save(out/'summary.json',summary);return summary
