#!/usr/bin/env python3
import argparse,importlib.util,json,shutil,subprocess,sys,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
def run(e,out):
 out.mkdir(parents=True,exist_ok=False)
 sys.path.insert(0,str(HERE.parent/'symbols'))
 import generated
 generated.HERE=HERE
 # The inherited compiler driver also assembles an adapter; retain the accepted
 # one unchanged, though this qualification never instantiates it.
 generated.run(e,out,command)
 for n in ['owner.mjs','check.mjs']:shutil.copy(HERE/n,out/n)
 for p in (ROOT/'runtime/wasm32').glob('*.mjs'):shutil.copy(p,out/p.name)
 # owner.mjs is the only runtime proposal; all production dependencies unchanged.
 shutil.copy(HERE/'owner.mjs',out/'owner.mjs')
 shutil.copy(ROOT/'doc/WASM/contracts/tcr.v2.json',out/'tcr.json')
 schema=read(ROOT/'doc/WASM/contracts/tcr.v2.json');fields={f['name']:f['offset'] for f in schema['fields']}
 used={'tcr_index':0,'worker_id':4,'lifetime_generation':8,'tcr_address':20,'alloc_pointer':48,'alloc_limit':52,'alloc_base':56,'vsp':64,'vsp_base':68,'vsp_limit':72,'tsp':76,'tsp_base':80,'tsp_limit':84,'csp':88,'csp_base':92,'csp_limit':96,'tlb_pointer':104,'tlb_limit':108,'mv_base':120,'mv_owner_top':124,'root_head':128,'next_method_context':188,'fp_control':200}
 assert schema['size_bytes']==256 and schema['alignment']==16 and all(fields[k]==v for k,v in used.items())
 save(out/'range-derivation.json',dict(tcr_schema_sha256=sha(ROOT/'doc/WASM/contracts/tcr.v2.json'),tcr_size=256,tcr_alignment=16,fields=used,function_bytes=32,cons_bytes=8,registry_header_bytes=8,registry_row_bytes=16,module_count=len(read(out/'compiled/modules.json')),pool_bytes=len(bytes.fromhex(read(out/'compiled/materialized.json')['image'])),stack_minima=dict(vsp=8192,tsp=4096,csp=256),scope='TCR from schema; object widths from integrated D1; code rows from generated modules. Stack minima are the explicit owner bootstrap budget, not inferred compiler maximum depth. No C runtime or C static/BSS/stack in this execution; generated modules import all memory and tables and have no defined globals or initialization segments.'))

 command(['/usr/local/bin/wat2wasm','--enable-tail-call',ROOT/'runtime/wasm32/stub.wat','-o',out/'stub.wasm'],out/'stub.log')
 malformed=out/'malformed';malformed.mkdir()
 text=(out/'compiled/read_cell.wat').read_text();pos=text.rfind(')')
 for name,extra in [('data','(data (i32.const 77824) "bad")'),('bss-start','(func $badstart (i32.store (i32.const 77824) (i32.const 0))) (start $badstart)'),('element','(elem (i32.const 1) func 0)')]:
  p=malformed/(name+'.wat');p.write_text(text[:pos]+extra+text[pos:]);command(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',p,'-o',p.with_suffix('.wasm')],p.with_suffix('.log'))
 command(['/usr/local/bin/node',out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 spec=importlib.util.spec_from_file_location('init_controls',HERE/'controls.py');controls=importlib.util.module_from_spec(spec);spec.loader.exec_module(controls)
 controls.run(out,command,read,save)
 spec=importlib.util.spec_from_file_location('init_assess',HERE/'assess.py');assess=importlib.util.module_from_spec(spec);spec.loader.exec_module(assess)
 save(out/'assessment.json',assess.check(out));save(out/'publication-controls.json',assess.controls(out))
 summary=read(out/'assessment.json');summary['mutants']=len(read(out/'controls.json'));summary['publication_controls']=len(read(out/'publication-controls.json'));save(out/'summary.json',summary)
 print(json.dumps(read(out/'summary.json'),indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--output',type=Path,required=True);v=a.parse_args();run(v.evidence.resolve(),v.output.resolve())
