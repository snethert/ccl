import os,shutil,subprocess
FAULTS=[
 ('module-omission',"need(modules.length===names.size,'MODULE_SET');",'', 'omitted required module'),
 ('dependency-cycle',"need(next,'INITIALIZER_CYCLE');ordered.push(next)","if(!next)break;ordered.push(next)", 'cyclic initializers'),
 ('completion-alias',"&&!cells.has(r.completion.address)",'', 'completion alias'),
 ('module-hash',"validate(bytes,record);",'', 'changed module digest'),
 ('no-load',"const result=invoke();","const result=undefined;",'COMPLETION_MISSING'),
 ('missing-completion-check',"need(get(r.completion.address)===r.completion.value,'COMPLETION_MISSING');",'', 'no-load path'),
 ('forged-completion-no-load',"const result=invoke();","for(const x of [...r.after,r.completion])new DataView(this.#memory.buffer).setUint32(x.address,x.value,true);const result=undefined;",'generated phase effects'),
 ('precondition',"assertWords(r.before,'PRECONDITION');",'', 'wrong prerequisite state'),
 ('freshness',"need(p.initializers.every(r=>get(r.completion.address)===0)&&[0,4,8].every(o=>get(p.ready+o)===0),'NOT_FRESH');",'', 'dirty completion'),
 ('clobber',"for(const r of completed)need(get(r.completion.address)===r.completion.value,'COMPLETION_CLOBBER');",'', 'clobber_previous'),
 ('failure-retry',"this.#state='FAILED';", "this.#state='NEW';",'terminal'),
 ('ready-count',"view.setUint32(p.ready+4,completed.length,true);", "view.setUint32(p.ready+4,0,true);",'0 !== 9'),
]
def run(out,command,read,save):
 rows=[]
 for name,old,new,why in FAULTS:
  d=out/'faults'/name;d.mkdir(parents=True)
  for f in out.iterdir():
   if f.is_file() and (f.suffix in ['.mjs','.wasm'] or f.name in ['expected.json','tcr.json']):shutil.copy(f,d/f.name)
  # Keep immutable compiled inputs shared on disk, without copying a U1 tree.
  (d/'compiled').symlink_to(out/'compiled',target_is_directory=True)
  p=d/'schedule.mjs';text=p.read_text();assert text.count(old)==(2 if name=='precondition' else 1),(name,text.count(old));p.write_text(text.replace(old,new))
  command(['/usr/local/bin/node','--check',p],d/'syntax.log')
  args=['/usr/local/bin/node',d/'check.mjs',d,d/'execution.json'];save(d/'command.json',dict(argv=list(map(str,args)),environment={'SCHEDULE_CONTROL':'1'}))
  with (d/'fault.log').open('w') as log:r=subprocess.run(list(map(str,args)),stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'SCHEDULE_CONTROL':'1'},timeout=120)
  assert r.returncode!=0,name+' escaped'
  assert why in (d/'fault.log').read_text(),(name,(d/'fault.log').read_text()[-2500:])
  rows.append(dict(name=name,status='REJECTED',diagnostic=why))
 save(out/'controls.json',rows)
