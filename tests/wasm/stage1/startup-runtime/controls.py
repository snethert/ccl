import copy,shutil
from classify import classify,validate

def controls(out,command,save):
 rows=[]
 for name,file,a,b,reason in [
  ('round-down','statistics.mjs',"r>500n||(r===500n&&(q&1n))","false",'native time conversion'),
  ('full-slot','statistics.mjs','[n,n,0n,0n,0n]','[n,0n,0n,0n,0n]','native time conversion'),
  ('generation-slot','statistics.mjs','[n,n,0n,0n,0n]','[n,n,n,0n,0n]','native time conversion'),
  ('replace-total','statistics.mjs','this.#microseconds+=end-start','this.#microseconds=end-start','exact five native values'),
  ('missed-reclaimed','statistics.mjs','this.#freed+=BigInt(reclaimed)','this.#freed+=0n','bytesFreed'),
  ('omit-result-count','service.mjs','[base+6,NIL,1,0].forEach','[base+6,NIL].forEach','publication'),
  ('snapshot-after-assurance','service.mjs','Number(values[i])*4','Number(owner.gctime(units)[i])*4','snapshot before collecting assurance'),
 ]:
  d=out/'faults'/name;d.mkdir(parents=True)
  for n in ['check.mjs','owner.mjs','statistics.mjs','service.mjs','sha256.mjs','bytes.mjs','collector.wasm','adapter.wasm']:shutil.copy(out/n,d/n)
  shutil.copytree(out/'compiled',d/'compiled')
  s=(d/file).read_text();assert s.count(a)==1,(name,a);(d/file).write_text(s.replace(a,b))
  command(['/usr/local/bin/node',d/'check.mjs',d,d/'execution.json'],d/'rejected.log',reason)
  rows.append(dict(name=name,status='REJECTED',diagnostic=reason))
 m=classify();assert validate(m)['accepted_effects']==18
 for name,edit in [('omitted-callback',lambda x:x['callbacks'].pop()),('forged-closure',lambda x:x['callbacks'][27].update(closure='CLOSED')),('provider-drift',lambda x:x['callbacks'][0]['providers'].update(node='ACCEPTED_EFFECT')),('selection-identity',lambda x:x['selection'].update(sha256='0'*64))]:
  damaged=copy.deepcopy(m);edit(damaged)
  try:validate(damaged)
  except ValueError:rows.append(dict(name=name,status='REJECTED',diagnostic='classification identity or omitted callback'))
  else:raise AssertionError(name)
 save(out/'controls.json',rows)
