"""Check independent literal/native answers and keep the auxiliary scope explicit."""
import copy,json
from pathlib import Path
def read(p):return json.loads(p.read_text())
def need(x,why):
 if not x:raise ValueError(why)
def assess(d):
 cases=d['cases'];expected={r['id']:r['expected'] for r in cases};x=d['execution']
 need(len(cases)==len(expected)==30,'full transfer and branch corpus')
 need(d['native']==[dict(id=r['id'],**r['expected']) for r in cases],'native answers')
 seen=[]
 for row in x['conditions']:
  need(row['id'] in expected and {k:row[k] for k in ['status','values','nodes','specials']}==expected[row['id']],'transfer results and effects')
  seen.append((row['id'],row['observed'],row['start']))
 wanted={(n,o,s) for n in expected for o in [False,True] for s in [65536,2147483648]}
 need(len(seen)==len(wanted) and set(seen)==wanted,'placement and observer matrix')
 need(x['comparisons']==120 and x['public_dispatches']==0,'internal entry comparisons')
 need(len(x['moved_vectors'])==130 and x['control_inspections']>0 and x['binding_inspections']>0 and x['ownership_inspections']>0,'moving roots and live extents')
 need(d['inherited']['comparisons']==120 and len(d['inherited']['moved_vectors'])==300,'inherited temporary matrix')
 need(len(d['shape'])==9 and all(r['control_pushes']==0 and r['exit_throws']==0 for r in d['shape'][:4]),'ordinary loops have no control overhead')
 need(d['compatibility']['files']==40 and d['compatibility']['functions']==20,'unchanged nonloop binaries')
 need(len(d['mutants'])==7 and len({r['name'] for r in d['mutants']})==7 and all(r['status']=='REJECTED' for r in d['mutants']),'seven compiled faults')
 need(len(d['refusals'])==6 and all(r['status']=='REJECTED' for r in d['refusals']),'remaining source refusals')
 return dict(status='PASS',inventory_credit=False,native_cases=30,comparisons=120,collections=130,inherited_comparisons=120,inherited_collections=300,shape_checks=9,unchanged_nonloop_files=40,compiler_mutants=7,source_refusals=6)
def run(x,out):
 d={k:read(x/p) for k,p in {'cases':'generated/compiled/cases.json','native':'generated/compiled/native.json','execution':'generated/execution.json','inherited':'inherited/execution.json','shape':'shape.json','compatibility':'compatibility.json','mutants':'mutants/controls.json','refusals':'refusals/refusals.json'}.items()}
 result=assess(d);controls=[]
 for name,edit in [('missing-closed-case',lambda v:v['cases'].pop(1)),('wrong-target',lambda v:v['execution']['conditions'][0]['values'].append(999)),('missing-placement',lambda v:v['execution']['conditions'].pop()),('missing-movement',lambda v:v['execution']['moved_vectors'].pop()),('unnecessary-unwind',lambda v:v['shape'][0].update(control_pushes=1)),('old-language-changed',lambda v:v['compatibility'].update(files=0)),('missing-mutant',lambda v:v['mutants'].pop()),('missing-refusal',lambda v:v['refusals'].pop())]:
  bad=copy.deepcopy(d);edit(bad)
  try:assess(bad)
  except ValueError as ex:controls.append(dict(name=name,status='REJECTED',diagnostic=str(ex)))
  else:raise ValueError(name+' escaped')
 out.mkdir();(out/'assessment.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');(out/'controls.json').write_text(json.dumps(controls,indent=2,sort_keys=True)+'\n');return result
