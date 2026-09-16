"""Logical cons oracle: ordered (car, cdr) pairs, never physical offsets."""
import copy,json
FORMS={
 'car':['car','x'],'cdr':['cdr','x'],
 'rplaca':['rplaca','x','y'],'rplacd':['rplacd','x','y'],
 'caar':['car',['car','x']],'cadr':['car',['cdr','x']],
 'cdar':['cdr',['car','x']],'cddr':['cdr',['cdr','x']],
 'read-car-after-write':['car',['rplaca','x','y']],
 'read-cdr-after-write':['cdr',['rplacd','x','y']],
 'operand-order':['rplaca',['rplacd','x','y'],['cdr','x']],
 'nested-temporaries':['rplaca','x',['car',['rplacd','y','z']]],
 'mutate-shared':['car',['rplaca',['cdr','x'],'y']],
 'branch':['if','x',['car','x'],'nil'],
 'nil-literal':['car','nil'], 'true-literal':['if','x','t','nil'],
 'minimum':-536870912,'maximum':536870911,
 # Value-form effects happen even if the pair subsequently fails its type check.
 'error-order':['rplaca','x',['car',['rplaca','y','z']]],
}
GRAPHS={
 'dotted':[[13,-7]], 'proper':[[13,'n1'],[29,'nil']],
 'nested':[['n1','n2'],[17,-9],[31,'nil']],
 'shared':[['n1','n1'],[101,'nil']], 'self-cycle':[[11,'n0']],
 'two-cycle':[['n1','n1'],[23,'n0']],
 'boundary-payloads':[[-536870912,536870911]],
}
def lisp(x):
 if isinstance(x,list):return '('+' '.join(map(lisp,x))+')'
 return str(x)
def source(name):return '(lambda (x y z) '+lisp(FORMS[name])+')'
class TypeFailure(Exception):
 def __init__(self,datum,kind):self.datum=datum;self.kind=kind

def expected(case):
 nodes=copy.deepcopy(case['nodes']);env=dict(zip(('x','y','z'),case['args']))
 def pair(x,kind):
  if isinstance(x,str) and x.startswith('n') and x[1:].isdigit() and int(x[1:])<len(nodes):return nodes[int(x[1:])]
  raise TypeFailure(x,kind)
 def evaluate(f):
  if isinstance(f,int) or (isinstance(f,str) and f in ('nil','t')):return f
  if isinstance(f,str):return env[f]
  op=f[0]
  if op=='if':return evaluate(f[2] if evaluate(f[1])!='nil' else f[3])
  a=evaluate(f[1])
  if op in ('car','cdr'):return 'nil' if a=='nil' else pair(a,1)[0 if op=='car' else 1]
  b=evaluate(f[2]);pair(a,2)[0 if op=='rplaca' else 1]=b;return a
 try:result={'status':'RETURN','value':evaluate(FORMS[case['function']])}
 except TypeFailure as e:result={'status':'TYPE_ERROR','datum':e.datum,'expected_kind':e.kind}
 return dict(result,nodes=nodes)
def cases():
 result=[]
 for graph,nodes in GRAPHS.items():
  for name in FORMS:
   result.append({'id':graph+'/'+name,'function':name,'nodes':nodes,'args':['n0','n1' if len(nodes)>1 else 101,-33]})
 for datum in ('nil','t',0,-1):
  for name in ('car','cdr','rplaca','rplacd','error-order'):
   result.append({'id':'noncons-'+str(datum)+'/'+name,'function':name,'nodes':[[37,-19]],'args':[datum,'n0',113]})
 for c in result:c['expected']=expected(c)
 return result
if __name__=='__main__':print(json.dumps({'sources':{n:source(n) for n in FORMS},'cases':cases()},indent=2))
