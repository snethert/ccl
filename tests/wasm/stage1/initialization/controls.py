"""Faults edit the owner, then execute the same real Workers and refusals."""
import shutil,subprocess
FAULTS=[
 ('overlap',"need(regions[i-1].start+regions[i-1].size<=r.start,'REGION_OVERLAP');",'', 'overlap'),
 ('minimum',"r.size>=r.minimum","true",'undersized-stack'),
 ('tcr-size',"t.size>=256","true",'undersized-tcr'),
 ('write-authority',"row.owner===r.owner","true",'shared-write'),
 ('module-validation','validate(bytes,m.record);','', 'data'),
 ('reserved-slot',"!l.reservedSlots.includes(r.slot)","true",'reserved-slot'),
 ('late-shared-zero',"try{this.#initialize(id);run();", "try{this.#initialize('process');this.#initialize(id);run();",'late Worker preserves all foreign regions'),
 ('private-setup',"try{this.#initialize(id);run();", "try{run();",'checked 2 worker_init'),
 ('ready-identity',"if(Atomics.load(state,0)===2){this.#identity();return false;}","if(Atomics.load(state,0)===2){return false;}",'Missing expected exception'),
 ('repeat-process',"if(Atomics.load(state,0)===2){this.#identity();return false;}","if(Atomics.load(state,0)===2){this.#initialize('process');return false;}",'late generated heap read'),
]
def run(out,command,read,save):
 rows=[]
 for name,old,new,why in FAULTS:
  m=out/'faults'/name;m.mkdir(parents=True)
  for p in out.iterdir():
   if p.is_file() and p.suffix in ['.mjs','.json','.wasm']:shutil.copy(p,m/p.name)
  shutil.copytree(out/'compiled',m/'compiled',ignore=shutil.ignore_patterns('source','proposal','driver'))
  shutil.copytree(out/'malformed',m/'malformed')
  p=m/'owner.mjs';s=p.read_text();assert s.count(old)==1,(name,s.count(old));p.write_text(s.replace(old,new))
  try:command(['/usr/local/bin/node',m/'check.mjs',m,m/'execution.json'],m/'execution.log')
  except subprocess.CalledProcessError:assert why in (m/'execution.log').read_text(),(name,(m/'execution.log').read_text()[-2500:])
  else:raise AssertionError('escaped '+name)
  rows.append(dict(name=name,status='REJECTED',diagnostic=why))
 save(out/'controls.json',rows)
