"""Publication check independent of Wasm probing and image builder."""
import copy,hashlib,json
from corpus import trace
BASES=[4194304,8388608,2147483648]
FAULTS=['unqualified-package','nil-symbol-pointer','inherited-external','keyword-self','prelookup-hash','rebuild-copy','exact-name','combined-allocation','loaded-value-tag','adapter-status','adapter-descriptor','adapter-count']
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(ok,why):
 if not ok:raise ValueError(why)
def oracle(rows,keywords):
 nil=('canonical','NIL');true=('canonical','T');ids={nil:0,true:1};pkgs={p:{} for p in ['CL','A','B','USER','KEYWORD']};pkgs['CL']={'NIL':(nil,2),'T':(true,2),'EXPORTED':(('CL','EXPORTED'),2),'HIDDEN':(('CL','HIDDEN'),1)}
 pkgs['KEYWORD']={n:(('KEYWORD',n),2) for n in keywords};answers=[]
 for i,(op,name,pkg) in enumerate(rows):
  value,status=pkgs[pkg].get(name,(nil,0))
  if not status and pkg=='USER' and name in pkgs['CL'] and pkgs['CL'][name][1]==2:value,status=pkgs['CL'][name][0],3
  if op==1 and not status:
   value=(pkg,name);pkgs[pkg][name]=(value,2 if pkg=='KEYWORD' else 1)
  if op==2:value,status=('uninterned',i),0
  if value not in ids:ids[value]=len(ids)
  answers.append([ids[value],status])
 return answers
NAMES=['trace','native','initial-keywords','execution','controls']
def data(out):return {n:read(out/(n+'.json')) for n in NAMES}
def check(out,d=None):
 d=data(out) if d is None else d;need(d['trace']==trace(),'complete trace');expected=oracle(d['trace'],d['initial-keywords']);need(d['native']==expected,'independent symbol semantics')
 rows=d['execution']['rows'];need(d['execution']['status']=='PASS','execution status');need([(r['base'],r['generated']) for r in rows]==[(b,g) for b in BASES for g in [False,True]],'placements and paths')
 for r in rows:
  need(r['observations']==expected and r['nativeComparisons']==len(expected),'complete native comparisons')
  need(r['restored'] and len(r['loads'])==1,'image load evidence');l=r['loads'][0];need(l['from']==r['base'] and l['to']!=l['from'] and l['bytes']>0 and l['symbolAfter']-l['symbolBefore']==l['to']-l['from'],'actual symbol relocation')
  need(len(r['refusals'])==12 and len(set(r['refusals']))==12,'refusal population')
  if r['generated']:
   g=r['delivery'];need(g['modules']==13 and r['bindingComparisons']==46,'generated membership and bindings')
   need(all(g['variants'].get(n,0)>0 for n in ['symbol_call','symbol_values','symbol_apply','symbol_preserve','symbol_dynamic','symbol_indirect','symbol_eq','symbol_read','symbol_write','symbol_bind','symbol_repeat_bind','symbol_bind_pair']),'generated forms')
   for key in ['fixed_calls','dynamic_calls','direct_calls']:need(sum(x[key] for x in g['delivery'])>0,'delivery modes')
   need(sum(x['dynamic_calls'] for x in g['delivery'])>sum(x['direct_calls'] for x in g['delivery']),'indirect delivery')
 modules=read(out/'compiled/modules.json');need(len(modules)==13,'module count')
 for m in modules:need(sha(out/'compiled'/(m['name']+'.wasm'))==sha(out/'installed'/(m['name']+'.wasm')),'installed bytes')
 need([x['name'] for x in d['controls']]==FAULTS and all(x['status']=='REJECTED' for x in d['controls']),'fault population')
 return dict(status='PASS',native_independent_equal=len(expected),modules=len(modules),runtime_faults=len(FAULTS))
def controls(out):
 original=data(out);results=[]
 for name,edit,why in [
 ('short-trace',lambda d:d['trace'].pop(),'complete trace'),
 ('biased-native',lambda d:d['native'][0].__setitem__(0,99),'independent symbol semantics'),
 ('short-comparisons',lambda d:d['execution']['rows'][0]['observations'].pop(),'complete native comparisons'),
 ('missing-placement',lambda d:d['execution']['rows'].pop(),'placements and paths'),
 ('fake-load',lambda d:d['execution']['rows'][0]['loads'][0].__setitem__('symbolAfter',0),'actual symbol relocation'),
 ('missing-refusal',lambda d:d['execution']['rows'][0]['refusals'].pop(),'refusal population'),
 ('missing-binding',lambda d:d['execution']['rows'][1].__setitem__('bindingComparisons',0),'generated membership and bindings'),
 ('missing-fault',lambda d:d['controls'].pop(),'fault population')]:
  d=copy.deepcopy(original);edit(d)
  try:check(out,d)
  except ValueError as e:need(str(e)==why,(name,str(e)));results.append(dict(name=name,status='REJECTED',diagnostic=why))
  else:raise AssertionError(name+' escaped')
 return results
