"""Independent result inventory and literal effect oracle, outside the scheduler."""
import copy
NAMES=['seed_map','seed_fatal','seed_install','define_one','define_two','define_three','define_four','activate','workload']
REFUSALS=['omitted required module','duplicate module','missing initializer','unknown prerequisite','forward phase','cyclic initializers','duplicate initializer','completion alias','effect completion alias','unbacked state','unaligned state','unbacked assertion','ready aliases effects','invalid phase','no loader phase','changed module digest','wrong planned digest','wrong export role','duplicate prerequisite','wrong plan identity','dirty completion','dirty ready count','wrong prerequisite state','no-load path','invalid installation result','asynchronous initializer','prewritten completion','state changed during installation','wrong_completion','no_completion','no_effect','clobber_previous','raises','reentrant initialization','reentrant same owner']
def check(x):
 assert x['status']=='PASS' and [r['base'] for r in x['rows']]==[4194304,2147483648,4194304,2147483648],'fresh placements'
 expected=[dict(values=[i,100+i],state=i,mode=0 if i==1 else 1 if i<8 else 2,output=[9,2] if i==9 else [0,0]) for i in range(1,10)]
 events=[dict(id=n,phase=0 if i<3 else 1 if i<7 else 2,event=e) for i,n in enumerate(NAMES) for e in ['installed','entered','completed']]
 for r in x['rows']:
  p=r['positive'];assert p['answers']==expected,'generated effects'
  assert p['events']==events,'completion order'
  assert p['installed']==NAMES,'actual installations'
  assert [m['name'] for m in p['loader'] if m['state']=='READY']==NAMES,'ready modules'
  installed=[m for m in p['load_events'] if m['event']=='INSTALLED']
  assert [m['slot'] for m in installed]==list(range(1,10)) and all(len(m['sha256'])==64 for m in installed),'installed digests'
  assert [v['name'] for v in r['refusals']]==REFUSALS,'refusal inventory'
  assert r['topological_reordering'] and r['invocations']==43,'executed cases'
 return dict(status='PASS',workers=4,initializers=9,native_comparisons=36,refusals=140,generated_invocations=172)
def controls(out,read,save):
 source=read(out/'execution.json');result=[];folder=out/'publication-controls';folder.mkdir()
 for name,edit,why in [
  ('omit-worker',lambda x:x['rows'].pop(),'fresh placements'),
  ('omit-completion',lambda x:x['rows'][0]['positive']['events'].pop(),'completion order'),
  ('wrong-effect',lambda x:x['rows'][0]['positive']['answers'][-1]['output'].__setitem__(0,0),'generated effects'),
  ('no-load',lambda x:x['rows'][0]['positive'].__setitem__('installed',[]),'actual installations'),
  ('missing-physical-install',lambda x:x['rows'][0]['positive'].__setitem__('load_events',[]),'installed digests'),
  ('drop-refusal',lambda x:x['rows'][0]['refusals'].pop(),'refusal inventory'),
  ('no-execution',lambda x:x['rows'][0].__setitem__('invocations',0),'executed cases'),
 ]:
  bad=copy.deepcopy(source);edit(bad);save(folder/(name+'.json'),bad)
  try:check(bad)
  except AssertionError as e:assert str(e)==why,(name,str(e))
  else:raise AssertionError(name+' escaped')
  result.append(dict(name=name,status='REJECTED',diagnostic=why))
 return result
