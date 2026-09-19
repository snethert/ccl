"""The retained literal answers are checked natively before target compilation."""
import copy,json
from pathlib import Path
def read(p):return json.loads(p.read_text())
def need(x,why):
 if not x:raise ValueError(why)
def assess(d):
 cases=d['cases'];expected={c['id']:c['expected'] for c in cases};x=d['execution']
 need(len(cases)==len(expected)==30,'complete named matrix')
 need(d['native']==[dict(id=c['id'],**c['expected']) for c in cases],'independent native answers')
 wanted={(n,observed,start) for n in expected for observed in [False,True] for start in [65536,2147483648]};seen=[]
 for row in x['conditions']:
  need(row['id'] in expected and {k:row[k] for k in ['status','values','nodes','specials']}==expected[row['id']],'temporary lifetime and order')
  seen.append((row['id'],row['observed'],row['start']))
 need(len(seen)==len(wanted) and set(seen)==wanted,'two placements with and without collection')
 need(x['comparisons']==120 and x['public_dispatches']==0,'comparison and internal entry')
 need(len(x['moved_vectors'])==300 and {r['function'] for r in x['moved_vectors']}==set(expected)-{'empty_tagbody'},'collection populations')
 need(x['control_inspections']>0 and x['binding_inspections']>0 and x['ownership_inspections']>0,'observed live control and root state')
 need(len(x['fatal_diagnostics'])==4 and all(r['function']=='fatal_cleanup' for r in x['fatal_diagnostics']),'fatal path as well as handled exits')
 need(len(d['refusals'])==8 and all(r['status']=='REJECTED' for r in d['refusals']),'source admission boundary')
 need(len(d['mutants'])==8 and len({r['name'] for r in d['mutants']})==8 and all(r['status']=='REJECTED' for r in d['mutants']),'compiled runtime faults')
 need(d['summary']['inherited_identical']==152,'old language bytes')
 return dict(status='PASS',native_cases=30,comparisons=120,collections=300,compiler_mutants=8,source_refusals=8,inherited_identical=152)
def run(x,out):
 d={k:read(x/p) for k,p in {'cases':'generated/compiled/cases.json','native':'generated/compiled/native.json','execution':'generated/execution.json','refusals':'refusals/refusals.json','mutants':'mutants/controls.json','summary':'summary.json'}.items()}
 result=assess(d);controls=[]
 for name,edit in [('omitted-case',lambda v:v['cases'].pop()),('changed-temporary',lambda v:v['execution']['conditions'][0]['values'].append(999)),('lost-movement',lambda v:v['execution']['moved_vectors'].pop()),('lost-fatal-exit',lambda v:v['execution']['fatal_diagnostics'].clear()),('omitted-mutant',lambda v:v['mutants'].pop()),('old-language-changed',lambda v:v['summary'].update(inherited_identical=0))]:
  bad=copy.deepcopy(d);edit(bad)
  try:assess(bad)
  except ValueError as ex:controls.append(dict(name=name,status='REJECTED',diagnostic=str(ex)))
  else:raise ValueError(name+' escaped')
 out.mkdir();(out/'assessment.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');(out/'controls.json').write_text(json.dumps(controls,indent=2,sort_keys=True)+'\n');return result
