import json
# Explicit small AST also drives an independent logical evaluator. Source is
# rendered normally and the native oracle compiles it independently.
FORMS={}
for n in (0,1,2,3,4,5,6,16,32,64):
 vs=[f'a{i}' for i in range(n)];FORMS[f'v{n}']=(vs,['values',*vs]);FORMS[f'call{n}']=(vs,[f'v{n}',*vs])
FORMS.update({
 'nested':(['a','b'],['v2',['v1','a'],['v1','b']]),
 'scalar_zero':([],['values',['v0'],['v1',7],['v6',1,2,3,4,5,6]]),
 'side_order':(['p'],['v2',['progn',['rplaca','p',1],['car','p']],['progn',['rplaca','p',2],['car','p']]]),
 'mutate':(['p','v'],['values',['rplaca','p','v'],['car','p'],['cdr','p']]),
 'mutation_call':(['p'],['mutate','p',['progn',['rplacd','p',99],['v1',42]]]),
 'keep_many':(['p'],['multiple-value-prog1',['v6',1,2,3,4,5,6],['rplaca','p',17],['v2',91,92]]),
 'keep_zero':(['p'],['multiple-value-prog1',['v0'],['rplaca','p',17],['v2',91,92]]),
 'keep_one':(['p'],['prog1',['v6',1,2,3,4,5,6],['rplaca','p',17],['v0']]),
 'choose':(['p','a','b'],['if','p',['v2','a','b'],['v0']]),
 'dynamic2':(['f','a','b'],['funcall','f','a','b']),
 'dynamic0':(['f'],['funcall','f']),
 'nested_fail':(['p','f'],['v2',['progn',['rplaca','p',10],['car','p']],['funcall','f']]),
 'advance':(['p'],['v1',['rplaca','p',['cdr',['car','p']]]]),
 'type_fail':(['p'],['v1',['car',['v1','p']]]),
})
# The dictionaries are ordered with required callees before callers.
def render(x):return '('+' '.join(map(render,x))+')' if isinstance(x,list) else str(x)
def modules():return [dict(name=n,source=render(['lambda',vs,body]),arity=len(vs)) for n,(vs,body) in FORMS.items()]
class Condition(Exception):
 def __init__(self,kind):self.kind=kind

def evaluate(name,inputs,nodes):
 if name not in FORMS:raise Condition('DESIGNATOR')
 vs,body=FORMS[name]
 if len(vs)!=len(inputs):raise Condition('ARITY')
 env=dict(zip(vs,inputs))
 def single(expr):
  values=run(expr);return values[0] if values else 'nil'
 def run(expr):
  if not isinstance(expr,list):return [env.get(expr,expr)]
  op,*args=expr
  if op=='values':return [single(x) for x in args]
  if op=='if':return run(args[1] if single(args[0])!='nil' else args[2])
  if op=='progn':
   result=[]
   for x in args:result=run(x)
   return result
  if op in ('prog1','multiple-value-prog1'):
   result=run(args[0]);saved=([result[0] if result else 'nil'] if op=='prog1' else result[:])
   for x in args[1:]:run(x)
   return saved
  if op in ('car','cdr','rplaca','rplacd'):
   pair=single(args[0]);value=single(args[1]) if len(args)==2 else None
   if pair=='nil' and op in ('car','cdr'):return ['nil']
   if not isinstance(pair,str) or not (pair.startswith('n') and pair[1:].isdigit()):raise Condition('TYPE')
   i=int(pair[1:]);offset=0 if op in ('car','rplaca') else 1
   if len(args)==1:return [nodes[i][offset]]
   nodes[i][offset]=value;return [pair]
  if op=='funcall':
   designator=single(args[0]);actual=[single(x) for x in args[1:]]
   if not isinstance(designator,str) or not designator.startswith('f:'):raise Condition('DESIGNATOR')
   return evaluate(designator[2:],actual,nodes)
  return evaluate(op,[single(x) for x in args],nodes)
 return run(body)
def cases():
 out=[]
 def add(name,args,nodes=None):
  before=[p[:] for p in (nodes or [])];after=[p[:] for p in before]
  try:expected={'status':'RETURN','values':evaluate(name,args,after),'nodes':after}
  except Condition as e:expected={'status':e.kind,'values':[],'nodes':after}
  out.append(dict(id=f'{name}-{len(out):03}',function=name,args=args,nodes=before,expected=expected))
 for n in (0,1,2,3,4,5,6,16,32,64):
  args=[(-1 if i%2 else 1)*(i+1) for i in range(n)]
  for name in (f'v{n}',f'call{n}'):add(name,args);add(name,['nil','t','n0',-536870912,536870911,7][:n]+args[6:] if n>=6 else ['n0']*n,[[19,'nil']])
  add(f'v{n}',args+[9])
 for name in ('side_order','mutation_call','keep_many','keep_zero','keep_one'):
  add(name,['n0'],[[13,29]]);add(name,['nil']);add(name,[5])
 add('advance',['n0'],[['n1','nil'],[7,'n2'],[8,'nil']])
 add('nested',[71,93]);add('nested',['n0','n1'],[[2,'n1'],[3,'nil']]);add('scalar_zero',[])
 for p in ('nil','t','n0'):add('choose',[p,7,9],[[11,'nil']])
 for f in ('f:v2','f:mutate',5,'nil','f:v1'):add('dynamic2',[f,'n0',17],[[3,5]])
 for p in ('nil',5):add('dynamic2',['f:mutate',p,17])
 for f in ('f:v0','f:v2',3):add('dynamic0',[f])
 for f in ('f:v0','f:v2',3):add('nested_fail',['n0',f],[[8,9]])
 for p in ('n0','nil',7):add('type_fail',[p],[[4,6]])
 return out

def lisp_input():
 def lit(x):
  if isinstance(x,list):return '('+' '.join(map(lit,x))+')'
  return json.dumps(x) if isinstance(x,str) else str(x)
 return '(in-package "CL-USER")\n(defparameter *call-sources* \''+lit([[m['name'],m['source']] for m in modules()])+')\n(defparameter *call-cases* \''+lit([[c['id'],c['function'],c['nodes'],c['args']] for c in cases()])+')\n'
REFUSALS=[('host-macro','(lambda (p) (typep p \'fixnum))'),('optional','(lambda (&optional p) p)'),('rest','(lambda (&rest p) p)'),('apply','(lambda (p) (apply p nil))'),('lambda-value','(lambda (p) (lambda () p))'),('unknown','(lambda (p) (unlinked p))'),('empty-prog1','(lambda () (prog1))'),('heap-constant','(lambda () \'(1 2))'),('cycle','(lambda (p) #1=(progn . #1#))'),('dotted','(lambda (p) (v1 . p))'),('extra-form','(lambda (p) p) 2'),('too-many-values','(lambda () (values '+' '.join('1' for _ in range(65))+'))')]
old_input=lisp_input
def lisp_input():return old_input()+'(defparameter *call-refusals* \''+'('+' '.join('('+json.dumps(n)+' '+json.dumps(s)+')' for n,s in REFUSALS)+'))\n'
