import copy,hashlib,json
from pathlib import Path
NAMES=['preflight','config_5564','config_6151','config_6150','config_6127','config_5566','workload']
def check(x,out):
 read=lambda p:json.loads(p.read_text());cases=read(out/'cases.json');native=read(out/'compiled/native.json')
 assert len(cases)==36 and cases[-1]['name']=='browser-observed','case population'
 assert cases[-1]['input']==read(out/'browser-input.json')['input'],'browser input'
 assert x['status']=='PASS' and [r['base'] for r in x['rows']]==[4194304,2147483648],'placements'
 hashes={n:hashlib.sha256((out/'compiled'/(n+'.wasm')).read_bytes()).hexdigest() for n in NAMES}
 events=[dict(id=n,phase=0 if i==0 else 2 if i==6 else 1,event=e) for i,n in enumerate(NAMES) for e in ['installed','entered','completed']]
 for r in x['rows']:
  assert len(r['rows'])==72,'dirty starts'
  for i,row in enumerate(r['rows']):
   ci,ri=divmod(i,2);assert (row['name'],row['sentinel'])==(cases[ci]['name'],[37,91][ri]),'case order'
   assert row['answers']==native[ci][ri],'native source effects'
   assert row['preflight']==[row['sentinel']]*3+cases[ci]['input']['defaults']+[row['sentinel']]*2,'preflight'
   assert row['workload']==native[ci][ri][-1]['globals'],'readback'
   assert row['events']==events,'completion order'
   assert [(m['name'],m['sha256']) for m in row['installed']]==[(n,hashes[n]) for n in NAMES],'installed bytes'
  assert len(r['refusals'])==30 and len({v['name'] for v in r['refusals']})==30,'refusal inventory'
  assert r['invocations']==508 and r['foreignChecks']==1524,'execution inventory'
 browser=read(out/'browser.json');assert browser==x,'browser execution'
 assert read(out/'browser-environment.json')['crossOriginIsolated'] is True,'isolation'
 return dict(status='PASS',modules=7,cases=36,workers=4,native_source_comparisons=1440,generated_invocations=2032,refusals=120,installed_digest_checks=2016,foreign_region_checks=6096,additional_callbacks=5,prior_literal_callbacks=13,open_callbacks=17,browser_node_equal=True)
def controls(out,read,save):
 rows=[];source=read(out/'execution.json');folder=out/'publication-controls';folder.mkdir()
 for name,edit,why in [
 ('omit-worker',lambda x:x['rows'].pop(),'placements'),
 ('omit-case',lambda x:x['rows'][0]['rows'].pop(),'dirty starts'),
 ('wrong-case',lambda x:x['rows'][0]['rows'][0].__setitem__('name','other'),'case order'),
 ('wrong-return',lambda x:x['rows'][0]['rows'][0]['answers'][4].__setitem__('values',[0]),'native source effects'),
 ('wrong-globals',lambda x:x['rows'][0]['rows'][0]['answers'][0]['globals'].__setitem__(0,1),'native source effects'),
 ('omit-workload',lambda x:x['rows'][0]['rows'][0].__setitem__('workload',[]),'readback'),
 ('omit-completion',lambda x:x['rows'][0]['rows'][0]['events'].pop(),'completion order'),
 ('wrong-digest',lambda x:x['rows'][0]['rows'][0]['installed'][0].__setitem__('sha256','0'*64),'installed bytes'),
 ('omit-refusal',lambda x:x['rows'][0]['refusals'].pop(),'refusal inventory'),
 ('omit-foreign-checks',lambda x:x['rows'][0].__setitem__('foreignChecks',0),'execution inventory')]:
  bad=copy.deepcopy(source);edit(bad);save(folder/(name+'.json'),bad)
  try:check(bad,out)
  except AssertionError as e:assert str(e)==why,(name,str(e))
  else:raise AssertionError(name+' escaped')
  rows.append(dict(name=name,status='REJECTED',diagnostic=why))
 return rows
