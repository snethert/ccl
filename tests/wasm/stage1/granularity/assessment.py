"""Independent publication checks against pinned compiler inventory and bytes."""
import copy,gzip,hashlib,json,statistics,re
from pathlib import Path
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def assess(out,base,document=None):
 b=copy.deepcopy(document or read(out/'bundle.json'));original=read(base/'execution/templates/modules.json');names=[x['name'] for x in original]+['plain_g2','plain_g3','plain_g4']
 assert [m['name'] for m in b['modules']]==names,'complete inventory'
 assert b['packaging']=='one-generated-function-per-module-v1','packaging'
 assert b['abi']==read(out/'versions.json')['abi'] and b['layout']==read(out/'versions.json')['layout'],'versions'
 retained=[]
 for i,m in enumerate(b['modules']):
  assert m['code_id']==i+1 and m['slot']==i+1,'mapping'
  assert m['generation']==(1 if i<16 else i-14),'generation'
  assert m['abi']==b['abi'] and m['layout']==b['layout'],'module versions'
  raw=out/'full'/(m['name']+'.wasm');template=out/'templates'/(m['name']+'.wasm');record=m['d2']['outputs']['full']
  assert record['binary_sha256']==sha(raw) and m['d2']['template']['template_sha256']==sha(template),'binary identity'
  a,z=template.read_bytes(),raw.read_bytes();diff=[j for j,(x,y) in enumerate(zip(a,z)) if x!=y]
  assert len(a)==len(z) and diff==[record['offset']] and a[diff[0]]==1 and z[diff[0]]==3,'materialization'
  assert [x['role'] for x in m['entries']]==['entry','tail_entry'],'roles'
  for row,n in zip(m['entries'],[2,3]):
   assert row['signature']==dict(params=['i32']*n,results=['i32']*2),'signature'
   assert row['export']==row['role'] and row['table']==('public' if n==2 else 'tail'),'entry role'
   assert 0<=row['range']['start']<row['range']['end']<=len(z),'extent'
  retained.append(dict(name=m['name'],bytes=len(z),gzip_bytes=len(gzip.compress(z,mtime=0))))
 assert retained==read(out/'sizes.json'),'sizes'
 execution=read(out/'execution.json');observations=[]
 for worker in [execution['origin'],*execution['restored']]:
  assert worker['installed']==19,'installation completeness'
  assert [r['generation'] for r in worker['revisionObservations']]==[2,3,4],'revisions'
  for row,value in zip(worker['revisionObservations'],[99,101,103]):
   assert row['old']==[12,28] and row['current']==[12,value*4],'old and new answers'
  observations.extend(worker['revisionObservations'])
 return dict(status='PASS',modules=19,entries=38,workers=3,redefinitions=len(observations),bytes=sum(x['bytes'] for x in retained),packaging=b['packaging'])
def controls(out,base):
 b=read(out/'bundle.json');rows=[]
 edits=[('omit',lambda x:x['modules'].pop(),'complete inventory'),('slot',lambda x:x['modules'][0].update(slot=3),'mapping'),('generation',lambda x:x['modules'][-1].update(generation=3),'generation'),('layout',lambda x:x['modules'][0].update(layout={}),'module versions'),('hash',lambda x:x['modules'][0]['d2']['outputs']['full'].update(binary_sha256='0'*64),'binary identity'),('role',lambda x:x['modules'][0]['entries'][0].update(table='tail'),'entry role'),('signature',lambda x:x['modules'][0]['entries'][0]['signature']['params'].pop(),'signature')]
 for name,edit,reason in edits:
  bad=copy.deepcopy(b);edit(bad)
  try:assess(out,base,bad)
  except AssertionError as e:assert str(e)==reason;(rows.append(dict(name=name,status='REJECTED',reason=reason)))
  else:raise AssertionError('escaped '+name)
 return rows
def timing(out):
 cold=read(out/'cold.json');warm=read(out/'warm.json');assert len(cold)==30
 for trial in cold:
  assert len(trial['rows'])==19 and trial['retained_modules']==19
  assert all(row[k]>=0 for row in trial['rows'] for k in ['compile_ms','instantiate_ms','publish_ms'])
 for metric in ['instantiate','validated_install']:
  rows=[r for r in warm['rows'] if r['metric']==metric];assert [r['trial'] for r in rows]==list(range(30))
  assert all(r['count']>0 and r['elapsed_ms']>=250 and r['ms_per_bundle']==r['elapsed_ms']/r['count'] for r in rows)
 retained=read(out/'retention.json');assert len(retained)==8
 for tier in ['default','eager_liftoff']:
  rows=[r for r in retained if r['tier']==tier];assert [r['generation'] for r in rows]==[1,2,3,4]
  assert [r['modules'] for r in rows]==[16,17,18,19]
  assert all(a['native_module_offheap_bytes']<b['native_module_offheap_bytes'] for a,b in zip(rows,rows[1:]))
 summary=read(out/'timing-summary.json')['metrics']
 for key in ['compile_ms','instantiate_ms','publish_ms']:
  assert summary[key]['median_ms']==statistics.median(sum(r[key] for r in t['rows']) for t in cold),'cold summary'
 for metric in ['instantiate','validated_install']:
  assert summary['warm_'+metric]['median_ms']==statistics.median(r['ms_per_bundle'] for r in warm['rows'] if r['metric']==metric),'warm summary'
 for row in retained:
  log=(out/f"retention-{row['tier']}-{row['generation']}.log").read_text()
  native=[int(n) for n in re.findall(r'Off-heap memory size of NativeModule: (\d+)',log)]
  assert sum(native)==row['native_module_offheap_bytes'] and len(native)==row['unique_binaries'],'retention raw join'
 return dict(status='PASS',cold_trials=30,warm_trials=60,retained_generations=8,selection='Engineering choice, no candidate ranking or confidence-bound claim.')
