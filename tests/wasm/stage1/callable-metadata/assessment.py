"""Publication completeness independently checked from the executed records."""
import copy,hashlib,json
from pathlib import Path

def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def need(x,why):
 if not x:raise ValueError(why)
def decode_native(g):
 nodes={r['id']:r['value'] for r in g['objects']}
 def d(v):
  if 'symbol' in v:return v
  if 'ref' in v:
   n=nodes[v['ref']]
   return ''.join(map(chr,n['value'])) if n['kind']=='string' else list(map(d,n['elements']))
  if v['kind']=='integer':return int(v['value'])
  need(v['kind']=='singleton','native scalar');return None if v['value']=='nil' else True
 return list(map(d,g['roots']))
NAMES=['plain','keyword','factory','factory_inner_1','twins','twins_inner_1','twins_inner_2','separate','separate_inner_1','multi','multi_inner_1','empty_keys','aliases','driver','get','set_y']
REFUSALS=['truncated-header','missing-arity','missing-debug','wrong-pool']
def assess(d):
 x=d['execution'];need(x['status']=='PASS','execution');need(d['modules']==NAMES,'exact module population')
 rows=[x['origin']]+x['restored'];need([r['base'] for r in rows]==[1048576,2097152,2147483648],'fresh Worker placements')
 native=decode_native(d['native']);need(len(native)==11,'native signatures')
 for i,r in enumerate(rows):
  need(r['status']=='PASS' and r['modules']==16 and r['restoredClosures']==bool(i),'Worker scope')
  need(r['refusals']==REFUSALS,'function extent and metadata refusals')
  need(r['installed']==16 and r['installations']==[dict(slot=j+1,event='INSTALLED',sha256=d['binaries'][n]) for j,n in enumerate(NAMES)],'actual installed binaries')
  meta={a['name']:a for a in r['metadataRecords']};need(list(meta)==NAMES,'metadata records')
  for n,a in meta.items():
   need(a['debug'][0:2]==[1,n] and a['arity'][0]==1,'debug and arity schema')
   captures=a['debug'][2];need([x[0] for x in captures]==list(range(len(captures))),'debug slot indices')
   expected=['LEFT','RIGHT'] if n=='multi_inner_1' else ['X'] if '_inner_' in n else []
   need(sorted(x[1][1] for x in captures)==expected and all(x[1][0]=='WASM32-COMPILER' for x in captures),'source capture names')
  for name,args,keys in native:
   n=name+'_inner_1' if name in ['factory','twins','separate','multi'] else name
   need(meta[n]['arity']==[1,args[0],args[1],args[2],args[3] is not None or None,args[4],keys],'native arity and key-vector identity')
  obs=r['observations'];need(len(obs)==(13 if i==0 else 8),'executed closure population')
  need([(o['name'],o['values']) for o in obs[:4]]==[('plain',[12,28]),('keyword',[12,36,44]),('aliases',[36,8]),('empty_keys',[68])],'direct callable values')
  if not i:need([o['values'][0]//4 for o in obs[8:12]]==decode_native(d['behavior'])[0][:4],'native shared and distinct closure values')
  else:need([(o['name'],o['values']) for o in obs[4:7]]==[('get',[124]),('driver',[148]),('get',[124])],'restored independent mutable state')
  need(obs[-1]['name']=='multi_inner_1' and obs[-1]['values']==[68,116,68,116],'captured defaults')
 need(len(d['mutants'])==7 and all(r['status']=='REJECTED' for r in d['mutants']) and len({r['oracle'] for r in d['mutants']})==7,'discriminating compiler faults')
 need(len(d['runtime'])==2 and all(r['status']=='REJECTED' for r in d['runtime']),'runtime semantic faults')
 need(len(d['snapshot'])==6 and all(r['status']=='REJECTED' for r in d['snapshot']),'snapshot refusals')
 need(d['compatibility']['status']=='PASS' and d['compatibility']['files']==256,'default mode byte identity')
 return dict(status='PASS',modules=16,worker_placements=3,metadata_records=48,native_signature_comparisons=33,generated_invocations=29,function_refusals=12,compiler_mutants=7,runtime_mutants=2,snapshot_refusals=6,default_identical_files=d['compatibility']['files'])
def run(x,out):
 d=dict(execution=read(x/'execution.json'),modules=[r['name'] for r in read(x/'compiled/modules.json')],native=read(x/'compiled/native-metadata.json'),behavior=read(x/'compiled/native-behavior.json'),binaries={n:hashlib.sha256((x/'compiled'/(n+'.wasm')).read_bytes()).hexdigest() for n in NAMES},mutants=read(x/'mutants/controls.json'),runtime=read(x/'runtime-mutants/controls.json'),snapshot=read(x/'snapshot-controls.json'),compatibility=read(x/'compatibility/default-compatibility.json'))
 result=assess(d);controls=[]
 for name,edit in [('missing-module',lambda d:d['modules'].pop()),('missing-high-placement',lambda d:d['execution']['restored'].pop()),('lost-key-alias',lambda d:d['execution']['origin']['metadataRecords'][12]['arity'][6].pop()),('lost-debug-name',lambda d:d['execution']['origin']['metadataRecords'][3]['debug'].__setitem__(1,'wrong')),('changed-installed-binary',lambda d:d['execution']['origin']['installations'][0].update(sha256='0'*64)),('lost-restored-mutation',lambda d:d['execution']['restored'][0]['observations'][5].update(values=[0])),('omitted-refusal',lambda d:d['execution']['origin']['refusals'].pop()),('omitted-compiler-fault',lambda d:d['mutants'].pop()),('omitted-runtime-fault',lambda d:d['runtime'].pop()),('omitted-snapshot-refusal',lambda d:d['snapshot'].pop()),('changed-default',lambda d:d['compatibility'].update(files=0))]:
  bad=copy.deepcopy(d);edit(bad)
  try:assess(bad)
  except ValueError as ex:controls.append(dict(name=name,status='REJECTED',diagnostic=str(ex)))
  else:raise ValueError(name+' escaped')
 out.mkdir();save(out/'assessment.json',result);save(out/'controls.json',controls);return result
