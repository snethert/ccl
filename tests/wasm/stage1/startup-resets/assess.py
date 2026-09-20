"""Fixed reset inventory and effects, independent of producer/selection derivation."""
import copy,hashlib
IDS=[5568,5548,6146,6189,6171,6170,6716,7626,7661,7660,13226,13364,15376]
VALUES=['nil',0,'nil','nil','t','nil','nil','nil','nil','nil','nil','nil','nil']
NAMES=['preflight']+['reset_'+str(n) for n in IDS]+['workload']
REFUSALS=['missing reset_'+str(n) for n in IDS]+['non-global destination','readonly destination','bad symbol header','no load','skip effect forge completion','omit completion','mutated installed bytes','different digest same behaviour']
def check(x,compiled):
 assert x['status']=='PASS' and [r['base'] for r in x['rows']]==[4194304,2147483648],'placements'
 hashes={n:hashlib.sha256((compiled/(n+'.wasm')).read_bytes()).hexdigest() for n in NAMES}
 events=[dict(id=n,phase=0 if i==0 else 2 if i==14 else 1,event=e) for i,n in enumerate(NAMES) for e in ['installed','entered','completed']]
 for r in x['rows']:
  assert [p['sentinel'] for p in r['rows']]==[37,91],'dirty starts'
  for p in r['rows']:
   expected=[dict(values=[v],globals=VALUES[:i+1]+[p['sentinel']]*(12-i)) for i,v in enumerate(VALUES)]
   assert p['answers']==expected,'native reset effects'
   assert p['preflight']==[p['sentinel']] and p['workload']==VALUES,'generated workload'
   assert p['events']==events,'completion order'
   assert [(m['name'],m['sha256']) for m in p['installed']]==[(n,hashes[n]) for n in NAMES],'installed bytes'
  assert [v['name'] for v in r['refusals']]==REFUSALS,'refusal inventory'
  assert r['invocations']==46 and r['private_catalog'],'execution inventory'
 return dict(status='PASS',workers=2,selected_callbacks=13,open_callbacks=22,native_callback_comparisons=52,generated_invocations=92,refusals=42,installed_digest_checks=60)
def controls(out,read,save):
 rows=[];source=read(out/'execution.json');folder=out/'publication-controls';folder.mkdir()
 for name,edit,why in [
  ('omit-worker',lambda x:x['rows'].pop(),'placements'),
  ('omit-dirty-start',lambda x:x['rows'][0]['rows'].pop(),'dirty starts'),
  ('omit-reset',lambda x:x['rows'][0]['rows'][0]['answers'].pop(),'native reset effects'),
  ('wrong-return',lambda x:x['rows'][0]['rows'][0]['answers'][0]['values'].__setitem__(0,0),'native reset effects'),
  ('wrong-global',lambda x:x['rows'][0]['rows'][0]['answers'][0]['globals'].__setitem__(1,0),'native reset effects'),
  ('omit-workload',lambda x:x['rows'][0]['rows'][0].__setitem__('workload',[]),'generated workload'),
  ('omit-completion',lambda x:x['rows'][0]['rows'][0]['events'].pop(),'completion order'),
  ('wrong-installed-digest',lambda x:x['rows'][0]['rows'][0]['installed'][0].__setitem__('sha256','0'*64),'installed bytes'),
  ('omit-refusal',lambda x:x['rows'][0]['refusals'].pop(),'refusal inventory')
 ]:
  bad=copy.deepcopy(source);edit(bad);save(folder/(name+'.json'),bad)
  try:check(bad,out/'compiled')
  except AssertionError as e:assert str(e)==why,(name,str(e))
  else:raise AssertionError(name+' escaped')
  rows.append(dict(name=name,status='REJECTED',diagnostic=why))
 return rows
