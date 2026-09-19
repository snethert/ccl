"""Publication checks independent of compiler decisions and result counts."""
import copy,json
from pathlib import Path

def read(p):return json.loads(p.read_text())
def need(ok,why):
 if not ok:raise ValueError(why)
def assess(d):
 n=d['native'];cases=d['cases'];x=d['execution'];r=d['resources']
 need(len(cases)==40 and len({c['id'] for c in cases})==40,'native case membership')
 need(n==[dict(id=c['id'],**c['expected']) for c in cases],'native oracle equality')
 want={c['id']:c['expected'] for c in cases};seen={k:0 for k in want}
 for row in x['conditions']:
  need(row['id'] in want,'unknown target case')
  need({k:row[k] for k in ('status','values','nodes','specials')}==want[row['id']],'target versus native')
  seen[row['id']]+=1
 need(set(seen.values())=={4} and x['comparisons']==160,'four target runs per case')
 need(x['public_dispatches']==0,'internal entry preserved')
 need(x['suspensions']==2,'two actual Worker suspensions')
 need(x['moved_vectors']==[{'capacity':14,'liveBindings':0},{'capacity':32,'liveBindings':1},{'capacity':64,'liveBindings':2},{'capacity':32,'liveBindings':1}]*2,'before and after growth evacuation')
 need(len(d['resource_cases'])==24 and r['comparisons']==96,'owner boundary population')
 resource={c['id']:c['expected'] for c in d['resource_cases']};seen={k:0 for k in resource}
 for row in r['conditions']:
  need(row['id'] in resource and {k:row[k] for k in ('status','values','nodes','specials')}==resource[row['id']],'resource state and refusal')
  seen[row['id']]+=1
 need(set(seen.values())=={4},'resource multiplicity')
 need(len(d['controls'])==12 and len({r['name'] for r in d['controls']})==12 and all(r['status']=='REJECTED' and r['first_assertion'].startswith('AssertionError') for r in d['controls']),'compiler mutants')
 return dict(status='PASS',native_cases=40,comparisons=160,resource_cases=24,resource_comparisons=96,compiler_mutants=12,worker_suspensions=2,vector_evacuations=8)
def run(execution,out):
 d={k:read(execution/v) for k,v in {'native':'positive/compiled/native.json','cases':'positive/compiled/cases.json','execution':'positive/execution.json','resources':'resources/execution.json','resource_cases':'resources/compiled/cases.json','controls':'controls.json'}.items()}
 summary=assess(d);controls=[]
 mutations=[('missing-case',lambda x:x['cases'].pop()),('target-value',lambda x:x['execution']['conditions'][0]['values'].append(999)),('no-suspension',lambda x:x['execution'].update(suspensions=0)),('lost-live-root',lambda x:x['execution']['moved_vectors'][1].update(liveBindings=0)),('refusal-promoted',lambda x:next(r for r in x['resources']['conditions'] if r['status']=='HEAP').update(status='RETURN')),('omitted-mutant',lambda x:x['controls'].pop())]
 for name,edit in mutations:
  bad=copy.deepcopy(d);edit(bad)
  try:assess(bad)
  except ValueError as e:controls.append(dict(name=name,status='REJECTED',reason=str(e)))
  else:raise ValueError(name+' escaped')
 out.mkdir(parents=True,exist_ok=False)
 for name,x in [('assessment.json',summary),('controls.json',controls)]:
  (out/name).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
 return summary
