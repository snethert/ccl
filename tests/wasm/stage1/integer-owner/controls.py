"""Runtime faults tested against the independent composition/admission assertions."""
import json,shutil,subprocess
from pathlib import Path
from derive import replace

def run(e,out,driver):
 faults=[
  ('no-allocation-assurance','numeric-capabilities.mjs','ensure=allocationService(owner,callError)','ensure=()=>{}','n_capture'),
  ('wrong-numeric-operation','numeric-capabilities.mjs','const calculate=integerService(options)','const real=integerService(options),calculate=(op,root)=>real(op===0?2:op,root)','n_add'),
  ('factory-tcr','numeric-capabilities.mjs','owner.tcr!==tcr||','', 'wrong-tcr'),
  ('admission-tcr','numeric-capabilities.mjs','o.tcr!==tcr||','', 'wrong-bundle-tcr'),
  ('admission-tag','numeric-capabilities.mjs','o.callError!==call_error||','', 'foreign-error-tag'),
  ('integer-function-identity','loader.mjs','&&clean.integer?.calculate===bundle.calculate','', 'wrapped-integer'),
  ('owner-function-identity','loader.mjs','clean.owner?.ensure===bundle.ensure&&','', 'wrapped-owner'),
  ('module-digest','loader.mjs',"need(sha(bytes)===record.sha256,'BINARY_DIGEST');",'', 'bad-digest'),
  ('integer-signature','loader.mjs',"&&same(i.signature,{params:['i32','i32'],results:['i32']})",'', 'integer-signature'),
  ('forged-bundle','numeric-capabilities.mjs','owners.set(bundle,','owners.set(bundle.ensure,','forged-bundle'),
 ]
 rows=[]
 for name,file,old,new,why in faults:
  path=out/'faults'/name;path.mkdir(parents=True)
  (path/'compiled').symlink_to(out/'compiled',target_is_directory=True)
  shutil.copy(out/'native.json',path/'native.json');driver.prepare(path)
  target=path/file;s=replace(target.read_text(),old,new)
  if name=='forged-bundle':s=replace(s,'const o=owners.get(bundle);','const o=owners.get(bundle.ensure);')
  target.write_text(s)
  if name=='no-allocation-assurance':
   f=path/'execute.mjs';f.write_text(replace(f.read_text(),'{high:false,collect:false},{high:false,collect:true}', '{high:false,collect:true}'))
  try:driver.command(['/usr/local/bin/node',path/'execute.mjs',path,e/'2026-09-19-stage1-collector-qualification-r1/collector.wasm',e/'2026-09-19-stage1-integer-core-r1/execution/integer.wasm',path/'execution.json','eager'],path/'execution.log')
  except subprocess.CalledProcessError:
   text=(path/'execution.log').read_text();assert why in text,(name,why,text[-2000:]);rows.append(dict(name=name,file=file,status='REJECTED',oracle=why))
  else:raise AssertionError('escaped '+name)
 driver.save(out/'controls.json',dict(status='PASS',rows=rows))
