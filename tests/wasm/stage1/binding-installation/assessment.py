"""Independent publication joins and omission controls; no installer imports."""
import copy,hashlib,json
from pathlib import Path

def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def need(x,why):
 if not x:raise ValueError(why)
def native(g):
 nodes={o['id']:o['value'] for o in g['objects']}
 def d(v):
  if 'ref' in v:
   n=nodes[v['ref']];return ''.join(map(chr,n['value'])) if n['kind']=='string' else list(map(d,n['elements']))
  if 'symbol' in v:return v['symbol']
  if v['kind']=='integer':return int(v['value'])
  return None if v['value']=='nil' else True
 return list(map(d,g['roots']))
NAMES=['make','make_inner_1','one','two','replacement','call0','call1','keyword','call2']
REFUSALS=['missing-alias','duplicate-alias','case-lost','package-lost','wrong-generation','wrong-phase','missing-module','conflicting-module','unknown-function','duplicate-function','wrong-previous','reserved-slot','past-table','wrong-range-start','wrong-range-end','missing-entry-range','wrong-entry-index','wrong-arity','wrong-digest','wrong-profile','missing-global-import','late-global-import','conflicting-slot','short-function','wrong-function-code','missing-owner-arity','missing-owner-debug','unexpected-environment','invalid-pool','missing-shared-alias','stale-runtime-manifest','reuse-live-slot']
FAULTS=['missing-alias-admitted','partial-entry-range','wrong-arity-admitted','stale-manifest-admitted','lost-alias-publication','missing-rollback','old-code-overwritten']
def ranges(b):
 # Independent section walker: indices here count only defined functions, since
 # the admitted profile has no imported functions (engine/loader checked).
 p=8
 def u():
  nonlocal p
  value=0;shift=0
  while True:
   byte=b[p];p+=1;value|=(byte&127)<<shift
   if byte<128:return value
   shift+=7;need(shift<35,'binary integer')
 exports=[];bodies=[]
 while p<len(b):
  kind=b[p];p+=1;n=u();end=p+n
  if kind==7:
   for _ in range(u()):
    n=u();name=b[p:p+n].decode();p+=n;tag=b[p];p+=1;index=u();need(tag==0,'function export');exports.append((name,index))
  if kind==10:
   for index in range(u()):
    n=u();bodies.append(dict(index=index,start=p,end=p+n));p+=n
  p=end
 return [dict(role=name,**bodies[index]) for name,index in exports]
def assess(d):
 need(d['modules']==NAMES,'module population');x=d['execution'];need(x['status']=='PASS' and [r['base'] for r in x['rows']]==[1048576,2147483648],'Worker placements')
 behavior=native(d['behavior'])[0];signatures=native(d['native']);need(len(signatures)==8,'native signature population')
 for row in x['rows']:
  need(row['status']=='PASS' and row['modules']==9 and row['nativeSignatures']==8,'execution population')
  need(row['initial']==[7]*4 and [row[k] for k in ['before','mutate','replaced','after']]==behavior,'native redefinition and environment values')
  need(len(row['observations'])==24 and row['observations'][-2]['values']==[28] and row['observations'][-1]['values']==[172],'old code and keyword invocation')
  need(row['identicalCode']==[d['binaries']['one']]*2 and d['binaries']['one']==d['binaries']['two'],'identical code alias population')
  need([r['label'] for r in row['refusals']]==REFUSALS and all(r['reason'] for r in row['refusals']),'atomic refusal population')
  records={r['name']:r for r in row['signatureRecords']};need(list(records)==NAMES,'signature records')
  for name,args,keys in signatures:
   n='make_inner_1' if name=='make' else name
   need(records[n]['arity']==[args[0],args[1],bool(args[2]),args[3] is not None,bool(args[4]),keys],'native arity join')
  for name,r in records.items():need(r['ranges']==d['ranges'][name],'independent entry extents')
  need(records['make_inner_1']['captures']==1,'mutable captured environment')
  need(len(row['manifests'])==len(row['publications'])==4,'publication population');previous=None;allmodules=[]
  expected_names=[[['BINDING-A','F'],['BINDING-B','F'],['BINDING-A','ALIAS'],['BINDING-A','f']],[['BINDING-A','F'],['BINDING-B','F'],['BINDING-A','ALIAS']],[['BINDING-A','F']],[['BINDING-A','F']]]
  for i,(m,p) in enumerate(zip(row['manifests'],row['publications'])):
   need(m['generation']==p['generation']==i+1 and m['previous']==previous and m['phase']==('runtime' if i else 'boot'),'boot/runtime chain')
   need([b['name'] for b in m['bindings']]==expected_names[i] and p['bindings']==len(expected_names[i]),'package-qualified publication')
   digest=hashlib.sha256(json.dumps(m,separators=(',',':'),ensure_ascii=False).encode()).hexdigest();need(p['head']==digest,'manifest hash');previous=digest
   for r in m['modules']:need(r['sha256']==d['binaries'][r['name']] and r['ranges']==d['ranges'][r['name']] and r['slot']>=4,'manifest binary binding')
   need(p['installed']==[dict(slot=r['slot'],event='INSTALLED',sha256=r['sha256']) for r in m['modules']],'installed bytes')
   allmodules += [r['name'] for r in m['modules']];need(p['modules']==allmodules,'retained old modules')
  need(len(allmodules)==9 and len(set(allmodules))==9,'fresh code ownership')
 need([r['name'] for r in d['mutants']]==FAULTS and all(r['status']=='REJECTED' for r in d['mutants']) and len({r['oracle'] for r in d['mutants']})==7,'semantic controls')
 return dict(status='PASS',modules=9,worker_placements=2,native_signature_comparisons=16,generated_invocations=48,atomic_refusals=64,transactions=8,installed_modules=18,runtime_mutants=7)
def run(x,out):
 d=dict(execution=read(x/'execution.json'),modules=[r['name'] for r in read(x/'compiled/modules.json')],native=read(x/'compiled/native-metadata.json'),behavior=read(x/'compiled/native-behavior.json'),binaries={n:hashlib.sha256((x/'compiled'/(n+'.wasm')).read_bytes()).hexdigest() for n in NAMES},ranges={n:ranges((x/'compiled'/(n+'.wasm')).read_bytes()) for n in NAMES},mutants=read(x/'mutants/controls.json'))
 result=assess(d);controls=[]
 for name,edit in [('lost-module',lambda d:d['modules'].pop()),('lost-high-placement',lambda d:d['execution']['rows'].pop()),('lost-alias',lambda d:d['execution']['rows'][0]['manifests'][0]['bindings'].pop()),('lost-refusal',lambda d:d['execution']['rows'][0]['refusals'].pop()),('lost-old-code',lambda d:d['execution']['rows'][0]['observations'][-2].update(values=[92])),('lost-distinct-environment',lambda d:d['execution']['rows'][0]['after'].__setitem__(3,37)),('changed-arity',lambda d:d['execution']['rows'][0]['signatureRecords'][2]['arity'].__setitem__(0,1)),('changed-entry-range',lambda d:d['ranges']['one'][0].update(end=0)),('changed-installed-binary',lambda d:d['execution']['rows'][0]['publications'][0]['installed'][0].update(sha256='0'*64)),('lost-manifest-history',lambda d:d['execution']['rows'][0]['publications'].pop()),('lost-runtime-fault',lambda d:d['mutants'].pop())]:
  bad=copy.deepcopy(d);edit(bad)
  try:assess(bad)
  except ValueError as ex:controls.append(dict(name=name,status='REJECTED',diagnostic=str(ex)))
  else:raise ValueError(name+' escaped')
 out.mkdir();save(out/'inputs.json',d);save(out/'assessment.json',result);save(out/'controls.json',controls);return result
