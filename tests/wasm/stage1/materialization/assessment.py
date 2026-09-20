"""Independent publication checks: actual retained bytes, not summary counters."""
import copy,hashlib,json
from pathlib import Path
def read(p):return json.loads(p.read_text())
def digest(b):return hashlib.sha256(b).hexdigest()
def need(x,s):
 if not x:raise ValueError(s)
def check(out,bundle=None):
 data=read(out/'materialization.json') if bundle is None else bundle
 expected=set(p.stem for p in (out/'templates').glob('*.wasm'))
 need(set(data['modules'])==expected and len(expected)==18,'MODULE_SET')
 need(data['policy']==read(out/'policy.json'),'ENGINE_POLICY')
 need(data['policy']['materializer']['sha256']==digest((out/'materializer.mjs').read_bytes()),'MATERIALIZER_BYTES')
 rows=[]
 for name,row in data['modules'].items():
  template=(out/'templates'/(name+'.wasm')).read_bytes();native=(out/'baseline'/(name+'.wasm')).read_bytes();t=row['template'];c=read(out/'classifications.json')[name]
  need(t['template_sha256']==digest(template),'TEMPLATE_BYTES')
  diffs=[i for i,(a,b) in enumerate(zip(template,native)) if a!=b]
  need(len(template)==len(native) and len(diffs)==1 and diffs==[t['offset']] and template[t['offset']]==1 and native[t['offset']]==3,'SINGLE_BYTE')
  need(t['minimum']==1 and t['maximum']==32769,'LIMITS')
  need(t['materializer']==data['policy']['materializer'] and t['engine_contract_sha256']==data['policy']['engine_contract_sha256'],'PROVENANCE')
  need(row['classification']==c and t['features']==c['features'] and c['binary_sha256']==digest(template) and not c['wait'] and not c['legacy'],'FEATURES')
  need(t['imports']==row['abi']['imports'] and t['exports']==row['abi']['exports'],'ABI')
  for profile,flag in [('full',3),('precompiled_callback',1)]:
   r=row['outputs'][profile];b=(out/profile/(name+'.wasm')).read_bytes()
   need(b==(native if flag==3 else template),'OUTPUT_BYTES')
   need(r['profile']==profile and r['shared']==(flag==3) and r['patched_byte']==flag,'PROFILE')
   need(r['binary_sha256']==digest(b) and r['template_sha256']==digest(template),'INSTALLED_IDENTITY')
   need(r['features']==c['features'] and r['materializer']==t['materializer'] and r['engine_contract_sha256']==t['engine_contract_sha256'],'INSTALLED_PROVENANCE')
   need(r['limits']==dict(minimum=1,maximum=32769),'INSTALLED_LIMITS')
   imports=copy.deepcopy(t['imports'])
   for i in imports:
    if i['kind']=='memory':i['flags']=flag
   need(r['imports']==imports and r['exports']==t['exports'],'INSTALLED_ABI')
  rows.append(dict(name=name,template_sha256=digest(template),shared_sha256=digest(native),offset=t['offset']))
 for profile in ['full','precompiled_callback']:
  x=read(out/(profile+'.json'));workers=[x['origin'],*x['restored']]
  need([r['base'] for r in workers]==[1048576,2097152,2147483648],'PLACEMENTS')
  for r in workers:
   need(r['status']=='PASS' and r['installed']==16 and len(r['installations'])==16 and len(r['observations'])>0,'EXECUTION')
   names=read(out/profile/'modules.json')
   need({m['name'] for m in names}==expected-{'leaf','primitive'},'INSTALLED_SET')
   for event in r['installations']:
    name=names[event['slot']-1]['name'];need(event['sha256']==data['modules'][name]['outputs'][profile]['binary_sha256'],'INSTALL_TRACE')
 return dict(status='PASS',modules=rows,workers=6)
def controls(out):
 tests=[('module',lambda d:d['modules'].pop(next(iter(d['modules']))),'MODULE_SET'),
        ('engine',lambda d:d['policy']['admission'].update(full=False),'ENGINE_POLICY')]
 for name,key,value,reason in [('template','template_sha256','0'*64,'TEMPLATE_BYTES'),('offset','offset',0,'SINGLE_BYTE'),('maximum','maximum',65536,'LIMITS'),('features','features',[],'FEATURES')]:
  tests.append((name,lambda d,k=key,v=value:d['modules']['aliases']['template'].__setitem__(k,v),reason))
 tests.append(('installed',lambda d:d['modules']['aliases']['outputs']['full'].__setitem__('binary_sha256','0'*64),'INSTALLED_IDENTITY'))
 rows=[]
 for name,mutate,reason in tests:
  d=read(out/'materialization.json');mutate(d)
  try:check(out,d)
  except ValueError as e:need(str(e)==reason,name);rows.append(dict(name=name,status='REJECTED',diagnostic=reason))
  else:raise AssertionError('publication fault escaped: '+name)
 return rows
