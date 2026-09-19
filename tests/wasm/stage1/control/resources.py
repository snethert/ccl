"""Owner-imposed stack limits: target resource tests, not native byte budgets."""
import json,shutil,subprocess
from pathlib import Path

def run(compiled,harness,out,focus=None):
 out.mkdir()
 for p in compiled.iterdir():
  if p.name in ('installed','modules.json','root-contracts.json','native-condition-classes.json'):
   if p.is_dir():shutil.copytree(p,out/p.name)
   else:shutil.copy(p,out/p.name)
 nodes=[[i,'n'+str(i+1) if i<39 else 'nil'] for i in range(40)]
 cases=[]
 for stack,size in [('vsp',12000),('csp',256),('tsp',256)]:
  for repeat in ([False,True] if stack!='tsp' else [False]):
   name='rr_temp' if stack=='tsp' else 'rr_twice' if repeat else 'rr_value'
   cases.append(dict(id='soft-'+stack+('-twice' if repeat else ''),function=name,args=[] if stack=='tsp' else ['n0'],nodes=[] if stack=='tsp' else nodes,bindings={},capacity=16,resources={stack:size,'reserve':8192},expected=dict(status='RETURN',values=[191] if stack=='tsp' else [181,181] if repeat else [181],nodes=[] if stack=='tsp' else nodes,specials=[101,103,'unbound'])))
 cases.append(dict(id='recursive-reserve-exhaustion',function='rr_nested',args=['n0'],nodes=nodes,bindings={},capacity=16,resources={'vsp':12000,'reserve':4096},expected=dict(status='STACK',values=[],nodes=nodes,specials=[101,103,'unbound'])))
 for name,values,after in [('irq_nested',[197,103,227],[[197,5]]),('irq_unwind',[223],[[211,5]])]:
  cases.append(dict(id='pending-'+name,function=name,args=['n0'],nodes=[[3,5]],bindings={},capacity=16,pending=7,pendingAfter=5,expected=dict(status='RETURN',values=values,nodes=after,specials=[227,229,'unbound'])))
 if focus:cases=[c for c in cases if c['id']==focus]
 (out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
 cmd=['/usr/local/bin/node',str(harness),str(out),str(out/'observations.json')]
 (out/'command.json').write_text(json.dumps(cmd)+'\n')
 with (out/'execution.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=120)
 if r.returncode:raise ValueError('resource controls: '+str(out/'execution.log'))
 return json.loads((out/'observations.json').read_text())
