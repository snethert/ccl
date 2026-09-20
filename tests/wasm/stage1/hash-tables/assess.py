"""Independent publication checks: identity map semantics, membership and binds."""
import copy,hashlib,json
from pathlib import Path
from corpus import trace
BASES=[262144,2147483648]
FAULTS=['moved-key-notification','value-parity','rehash-notification','cache-on-rehash','cached-value-replacement','cache-on-deletion','duplicate-count','cached-key-scanner','cached-value-scanner','adapter-presence','adapter-dynamic-displacement','adapter-value-count']
def need(ok,why):
 if not ok:raise ValueError(why)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def oracle(rows):
 table={};answers=[]
 for row in rows:
  op=row[0]
  if op=='set':table[row[1]]=row[2];answer=[row[2]]
  elif op=='get':answer=[table.get(row[1],row[2]),int(row[1] in table)]
  elif op=='del':answer=[int(row[1] in table)];table.pop(row[1],None)
  elif op=='count':answer=[len(table)]
  else:need(op=='gc','trace opcode');answer=[-1]
  answers.append(answer)
 return answers
def check(out,data=None):
 d=data or {n:read(out/(n+'.json')) for n in ['trace','native','execution','generated','controls']}
 need(d['trace']==trace(),'complete trace')
 expected=oracle(d['trace']);need(d['native']==expected,'native identity semantics')
 for kind in ['execution','generated']:
  need(d[kind]['status']=='PASS','execution status');rows=d[kind]['rows'];need([r['base'] for r in rows]==BASES,'placements')
  for row in rows:
   need(row['observations']==expected,'complete operation observations')
   need(row['nativeComparisons']==len(expected),'comparison count')
   need(len(row['moves'])==21,'movement population')
   for m in row['moves']:
    need(m['from']!=m['to'] and m['before'][0]!=m['after'][0],'actual table relocation')
    need(len(m['before'])==len(m['after']),'root population')
    for a,b in zip(m['before'],m['after']):
     if m['from']<=a<m['from']+32768:need(m['to']<=b<m['to']+32768 and b!=a,'actual root relocation')
   need(len(row['refusals'])==13 and len(set(x['name'] for x in row['refusals']))==13,'refusal population')
   if kind=='generated':
    g=row['generated'];need(g['compilerUnmodified'] is True and g['modules']==9,'generated membership')
    need(len(g['moving'])==2 and [x['values'] for x in g['moving']]==read(out/'compiled/native-moving.json'),'moving native comparison')
    need(all(x['before']!=x['after'] for x in g['moving']),'generated collection')
    need(sum(x['dynamic_calls'] for x in g['delivery'])>sum(x['direct_calls'] for x in g['delivery'])>0,'both descriptor modes')
    need(sum(x['fixed_calls'] for x in g['delivery'])>0,'fixed delivery')
    names=[r['name'] for r in read(out/'compiled/modules.json')];need([x['name'] for x in g['installed']]==names,'installed membership')
    for x in g['installed']:
     need(x['sha256']==sha(out/'compiled'/(x['name']+'.wasm'))==sha(out/'installed'/(x['name']+'.wasm')),'installed bytes')
 need([x['name'] for x in d['controls']]==FAULTS and all(x['status']=='REJECTED' for x in d['controls']),'fault population')
 return dict(status='PASS',native_model_equal=len(expected),generated_modules=9,generated_comparisons=2*(len(expected)+2),runtime_faults=len(FAULTS),scope='S1-LL18-b:moved-keys')
def controls(out):
 original={n:read(out/(n+'.json')) for n in ['trace','native','execution','generated','controls']};results=[]
 for name,edit,reason in [
  ('short-trace',lambda d:d['trace'].pop(),'complete trace'),
  ('biased-native',lambda d:d['native'][0].__setitem__(0,0),'native identity semantics'),
  ('short-observations',lambda d:d['generated']['rows'][0]['observations'].pop(),'complete operation observations'),
  ('one-placement',lambda d:d['generated']['rows'].pop(),'placements'),
  ('fake-movement',lambda d:d['execution']['rows'][0]['moves'][0].__setitem__('to',262144),'actual table relocation'),
  ('missing-moving-case',lambda d:d['generated']['rows'][0]['generated']['moving'].pop(),'moving native comparison'),
  ('missing-fault',lambda d:d['controls'].pop(),'fault population'),
  ('wrong-installed',lambda d:d['generated']['rows'][0]['generated']['installed'][0].__setitem__('sha256','0'*64),'installed bytes'),
 ]:
  d=copy.deepcopy(original);edit(d)
  try:check(out,d)
  except ValueError as e:need(str(e)==reason,(name,str(e)));results.append(dict(name=name,status='REJECTED',diagnostic=reason))
  else:raise AssertionError('publication omission escaped '+name)
 return results
