"""Publication checks read execution records, generated files and native answers."""
import copy,json,hashlib
from pathlib import Path
def read(p):return json.loads(p.read_text())
def check(out,record=None):
 x=read(out/'execution.json') if record is None else record
 assert x['status']=='PASS' and x['modules']==5,'generated modules'
 modules=read(out/'compiled/modules.json');assert [m['name'] for m in modules]==['process_init','worker_init','read_cell','mutate','call_reader'],'module inventory'
 for m in modules:assert (out/'installed'/str(0)/(m['name']+'.wasm')).read_bytes()==(out/'compiled'/(m['name']+'.wasm')).read_bytes(),'installed identity'
 native=read(out/'compiled/native.json');assert native==[[7,9],[31,37],[31,37],[2,11]],'native answers';v=[[4*y for y in a] for a in native]
 assert [r['base'] for r in x['rows']]==[4194304,2147483648],'placements'
 for r in x['rows']:
  assert r['original_worker_rechecked'] and r['canaries']>0,'survival'
  assert [w['id'] for w in r['workers']]==[0,1,2],'late Workers'
  for w in r['workers']:
   assert w['observations']==([v[0],v[3],v[2]] if w['id']==0 else [v[3],v[2]]),'native generated observations'
   assert w['reserved'],'reserved slots'
   states={m['name']:m['state'] for m in w['published']}
   assert states['read_cell']==states['worker_init']==states['call_reader']=='READY','lazy installation'
   if w['id']!=0:assert states['process_init']==states['mutate']=='COLD','no process execution in late Worker'
   assert any(e['event']=='INSTALLED' for e in w['events']),'installation events'
 assert len(x['refusals'])==40 and all(x['refusals'].count(r)==1 for r in x['refusals']),'refusals'
 for base in [4194304,2147483648]:
  assert {r['name'] for r in x['refusals'] if r['base']==base}=={'overlap','undersized-stack','undersized-tcr','misalignment','unbacked-range','shared-write','other-worker-write','out-of-range-write','foreign-stack-pointer','missing-owned-region','reserved-slot','undersized-table','duplicate-slot','code-role','omitted-module','data','bss-start','element','foreign-layout-ready','failed-process-is-terminal'},'refusal inventory'
 return dict(status='PASS',modules=5,workers=6,native_comparisons=18,owner_refusals=40,placements=2)
def controls(out):
 source=read(out/'execution.json');rows=[]
 for name,edit,why in [
  ('omit-high',lambda x:x['rows'].pop(),'placements'),
  ('omit-worker',lambda x:x['rows'][0]['workers'].pop(),'late Workers'),
  ('wrong-values',lambda x:x['rows'][1]['workers'][2]['observations'][1].__setitem__(0,0),'native generated observations'),
  ('skip-recheck',lambda x:x['rows'][0].__setitem__('original_worker_rechecked',False),'survival'),
  ('drop-reservation',lambda x:x['rows'][0]['workers'][0].__setitem__('reserved',False),'reserved slots'),
  ('eager-process-in-late-worker',lambda x:x['rows'][0]['workers'][1]['published'][0].__setitem__('state','READY'),'no process execution in late Worker'),
  ('omit-refusal',lambda x:x['refusals'].pop(),'refusals')]:
  bad=copy.deepcopy(source);edit(bad)
  try:check(out,bad)
  except AssertionError as ex:assert str(ex)==why,(name,str(ex))
  else:raise AssertionError(name+' escaped')
  rows.append(dict(name=name,status='REJECTED',diagnostic=why))
 return rows
