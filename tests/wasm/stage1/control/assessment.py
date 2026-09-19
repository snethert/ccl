"""Independent publication checks over executed observations, not emitter metadata."""
import copy,json
from pathlib import Path

def read(p):return json.loads(p.read_text())
def require(ok,why):
 if not ok:raise ValueError(why)

def assess(data):
 native=data['native'];cases=data['cases'];execution=data['execution']
 require(len(native)==46 and len(cases)==46,'native corpus membership')
 require(len({c['id'] for c in cases})==46,'unique native cases')
 require(native==[dict(id=c['id'],**c['expected']) for c in cases],'native literal expectations')
 require(execution['status']=='PASS' and execution['comparisons']==184,'four target executions per native case')
 require(execution['public_dispatches']==0,'internal dispatch preserved')
 fatal=execution['fatal_diagnostics']
 require(len(fatal)==4,'early diagnostic count')
 for row in fatal:
  require(row==dict(version=1,stage='bootstrap',function='e_early',kind='type-error',datum=28,check=1,transport='wasm-tag',recoverable=False),'structured early diagnostic')
 for name,values,car in [('r_many_error',list(range(130)),257),('r_zero_error',[],263)]:
  row=next(c for c in cases if c['function']==name)
  require(row['expected']['values']==values and row['expected']['nodes']==[[car,5]],'restart values and cleanup effect')
 row=next(c for c in cases if c['function']=='o_nested')
 require(row['expected']['values']==[3,5] and row['expected']['nodes']==[[13,5]],'nested cleanup and no post-exit effect')
 row=next(c for c in cases if c['function']=='o_replace')
 require(row['expected']['values']==[19] and row['expected']['nodes']==[[19,5]],'cleanup replaces pending exception')
 require(data['resources']['status']=='PASS' and data['resources']['comparisons']==32,'stack and interrupt cases')
 require(len(data['controls'])==13 and all(r['status']=='REJECTED' and r['diagnostic'].startswith('AssertionError') for r in data['controls']),'semantic mutant rejection')
 require(data['refusals']==[dict(name=n,status='REJECTED') for n in ('anonymous-restart','case-options','bind-options','condition-association','user-case')],'declared language refusals')
 return {'status':'PASS','native_cases':46,'comparisons':184,'resource_comparisons':32,'compiler_mutants':13,'source_refusals':5,'early_fatal_diagnostics':4}

def run(execution,out):
 data={name:read(execution/path) for name,path in {
  'native':'positive/compiled/native.json','cases':'positive/compiled/cases.json',
  'execution':'positive/execution.json','resources':'resources/observations.json',
  'controls':'controls.json','refusals':'positive/compiled/refusals.json'}.items()}
 summary=assess(data);controls=[]
 def omission(x):x['execution']['fatal_diagnostics'].pop()
 def relabel(x):x['execution']['fatal_diagnostics'][0]['stage']='ordinary-error-service'
 def engine_trap(x):x['execution']['fatal_diagnostics'][0]['transport']='engine-trap'
 def status_only(x):del x['execution']['fatal_diagnostics'][0]['datum']
 def lose_value(x):next(c for c in x['native'] if c['id'].startswith('r_many_error-'))['values'].pop()
 def missed_refusal(x):x['refusals'].pop()
 for mutate in (omission,relabel,engine_trap,status_only,lose_value,missed_refusal):
  damaged=copy.deepcopy(data);mutate(damaged)
  try:assess(damaged)
  except ValueError as e:controls.append(dict(name=mutate.__name__,status='REJECTED',reason=str(e)))
  else:raise ValueError('publication control escaped '+mutate.__name__)
 out.mkdir(parents=True,exist_ok=False)
 for name,x in [('assessment.json',summary),('controls.json',controls)]:
  (out/name).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
 return summary
