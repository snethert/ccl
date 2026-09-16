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
# Optional and keyword defaults are ordinary source forms, including calls.
FORMS.update({
 'opt':(['a','&optional',['b','a','bp'],['c','b','cp']],['values','a','b','bp','c','cp']),
 'opt_nil':(['&optional','a',['b',['v0'],'bp']],['values','a','b','bp']),
 'opt_effect':(['p','&optional',['a',['progn',['rplaca','p',11],['v2',7,8]],'ap'],['b',['progn',['rplacd','p',22],['v1','a']],'bp']],['values','a','ap','b','bp',['car','p'],['cdr','p']]),
 'opt_failure':(['p','f','&optional',['a',['progn',['rplaca','p',11],['funcall','f']]]],['values','a',['car','p']]),
 'opt_forward':(['p','&optional',['a',['v1',31]]],['opt','p','a']),
 'key':(['&key',['a',1,'ap'],['b','a','bp']],['values','a','ap','b','bp']),
 'key_alias':(['r','&key',[[":external",'a'],['v1','r'],'ap'],['b','ap','bp']],['values','r','a','ap','b','bp']),
 'key_effect':(['p','&key',['a',['progn',['rplaca','p',13],['v2',17,19]],'ap'],['b',['progn',['rplacd','p',23],['v1','a']],'bp']],['values','a','ap','b','bp',['car','p'],['cdr','p']]),
 'key_failure':(['p','f','&key',['a',['progn',['rplaca','p',11],['funcall','f']]]],['values','a',['car','p']]),
 'key_allow':(['&key',['a',1,'ap'],'&allow-other-keys'],['values','a','ap']),
 'key_empty':(['&key'],['values',7]),
 'key_empty_allow':(['&key','&allow-other-keys'],['values',9]),
 'key_bind_allow':(['&key',['allow-other-keys','nil','sp'],['a',1]],['values','allow-other-keys','sp','a']),
 'opt_key':(['r','&optional',['o',['v1','r'],'op'],'&key',['a','o','ap'],['b','ap','bp']],['values','r','o','op','a','ap','b','bp']),
 'key_caller':(['p'],['key_effect','p',':b',['progn',['rplaca','p',41],['v1',37]]]),
 'opt_key_caller':(['p'],['opt_key',':a','p',':b',['v2',43,47],':a',['car','p']]),
 'key_dynamic':(['f','p'],['funcall','f','p',':a',53,':b',59]),
})
FORMS.update({
 'rest_all':(['&rest','r'],'r'),
 'rest_parts':(['a','&optional',['b',9,'bp'],'&rest','r'],['values','a','b','bp','r']),
 'rest_key':(['&rest','r','&key',['a',3,'ap'],['b','a']],['values','r','a','ap','b']),
 'rest_default':(['p','&optional',['a',['rest_all',7,9]],'&rest','r'],['values','a','r',['car','p']]),
 'rest_copies':(['p'],['values',['rest_all',1,'p'],['rest_all',1,'p']]),
 'rest_escape':(['p'],['rplaca','p',['rest_all',11,13,17]]),
 'rest_mutate':(['&rest','r'],['values',['rplaca','r',71],'r']),
 'rest_key_fail':(['p','f','&rest','r','&key',['a',['progn',['rplaca','p','r'],['funcall','f']]]],['values','a','r']),
 'apply0':(['f','xs'],['apply','f','xs']),
 'apply2':(['f','a','b','xs'],['apply','f','a','b','xs']),
 'apply_effect':(['p','f','xs'],['apply',['progn',['rplaca','p',1],'f'],['progn',['rplaca','p',2],['car','p']],['progn',['rplacd','p',3],'xs']]),
 'apply_rest':(['f','&rest','r'],['apply','f','r']),
 'apply_nested':(['f','xs'],['values',['apply','f','xs'],['apply','f','xs']]),
 'apply_keep':(['f','xs'],['multiple-value-prog1',['apply','f','xs'],['v6',1,2,3,4,5,6]]),
 'apply_nil':(['f','a','b'],['apply','f','a','b','nil']),
 'apply_built_list':(['f','p'],['apply','f',['rest_all','p',37]]),
 'apply_type_fail':(['f','xs'],['car',['apply','f','xs']]),
 'call_long':([],['rest_all',*range(129)]),
 'required_long':([f'p{i}' for i in range(129)],['values','p0','p64','p128']),
 'call_required_long':([],['required_long',*range(129)]),
})
# Capacities are runtime inputs, independent of the number of source VALUES.
for n in (65,128,129,257,512,1024):
 vs=[f'a{i}' for i in range(n)];FORMS[f'v{n}']=(vs,['values',*vs])
 if n<=512:FORMS[f'call{n}']=(vs,[f'v{n}',*vs])
FORMS.update({
 'many':(['p'],['values',*(['p','nil','t',-536870912,536870911]*26)]),
 'keep_large':(['p'],['multiple-value-prog1',['many','p'],['v64',*range(64)],['rplaca','p',91],['many',7]]),
 'keep_large_nested':(['p'],['multiple-value-prog1',['keep_large','p'],['keep_large','p']]),
 'many_optional':(['p','&optional',['a',['many','p'],'ap']],['values',*(['a','ap','p']*43)]),
 'many_keyword':(['p','&key',['a',['many','p'],'ap']],['values',*(['a','ap','p']*43)]),
 'many_failure':(['p','f'],['multiple-value-prog1',['many','p'],['rplaca','p',71],['funcall','f']]),
 'many_if':(['p','flag'],['if','flag',['many','p'],['v0']]),
 'many_scalar':(['p'],['values',['many','p'],['car',['many','p']]]),
 'large_prog1':(['p'],['prog1',['many','p'],['many',19]]),
 'bound_after_full':(['p','&optional',['a',17]],['progn',['v128',*(['p']*128)],['values','a','p']]),
 'bound_after_many':(['p','&optional',['a',17]],['progn',['many','p'],['values','a','p']]),
 'discard_values':([],['progn',['values',*range(129)],7]),
 'large_effects':(['p'],['values',*([['rplaca','p',i] for i in range(129)])]),
})
FORMS.update({
 'alternate':(['x'],['values','x',99]),
 'dynamic_one':(['f','x'],['funcall','f','x']),
 'function_value':([],['function','v1']),
 'quoted_value':([],['quote','v1']),
 'quoted_call':(['x'],['funcall',['quote','v1'],'x']),
 'function_call':(['x'],['funcall',['function','v1'],'x']),
 'quoted_apply':(['xs'],['apply',['quote','v2'],'xs']),
 'function_apply':(['xs'],['apply',['function','v2'],'xs']),
 'walk_list':(['p'],['if','p',['walk_list',['cdr','p']],['values',71,73]]),
 'mutual_a':(['p'],['if','p',['mutual_b',['cdr','p']],['values',11,13]]),
 'mutual_b':(['p'],['if','p',['mutual_a',['cdr','p']],['values',17,19]]),
 'recursive_keep':(['p'],['if','p',['multiple-value-prog1',['v2',['car','p'],'p'],['recursive_keep',['cdr','p']]],['v0']]),
 'self_named':(['x'],['values',['function','self_named'],'x']),
})
# Factory calls return before their closures are invoked. All mutation is through
# source SETQ; no host-created environment is supplied to generated code.
FORMS.update({
 'factory':(['x'],['lambda',[], 'x']),
 'setter_factory':(['x'],['lambda',['v'],['setq','x','v']]),
 'cell_factory':(['x'],['lambda',['&optional',['v','nil','vp']],['if','vp',['setq','x','v'],'x']]),
 'pair_factory':(['x','p'],['progn',['rplaca','p',['lambda',[],'x']],['rplacd','p',['lambda',['v'],['setq','x','v']]],'p']),
 'nested_factory':(['x'],['lambda',[],['lambda',[],'x']]),
 'empty_factory':([],['lambda',[],17]),
 'closure_call':(['x'],['funcall',['factory','x']]),
 'closure_set':(['x','v'],['let',[['f',['cell_factory','x']]],['values',['funcall','f'],['funcall','f','v'],['funcall','f']]]),
 'closure_siblings':(['x','v','p'],['progn',['pair_factory','x','p'],['values',['funcall',['car','p']],['funcall',['cdr','p'],'v'],['funcall',['car','p']]]]),
 'closure_distinct':(['x','v'],['let',[['a',['cell_factory','x']],['b',['cell_factory','v']]],['values',['funcall','a',71],['funcall','a'],['funcall','b']]]),
 'closure_nested':(['x'],['funcall',['funcall',['nested_factory','x']]]),
 'closure_empty':([],['funcall',['empty_factory']]),
 'closure_shadow':(['x'],['let',[['f',['lambda',[],'x']]],['let',[['x',37]],['values','x',['funcall','f']]]]),
 'closure_parallel':(['x'],['let',[['x',31],['y',['lambda',[],'x']]],['values','x',['funcall','y']]]),
 'closure_sequential':(['x'],['let*',[['x',31],['y',['lambda',[],'x']]],['progn',['setq','x',43],['funcall','y']]]),
 'closure_parent_write':(['x'],['let',[['f',['lambda',[],'x']]],['progn',['setq','x',53],['funcall','f']]]),
 'closure_local_write':(['x'],['let',[['y','x']],['let',[['f',['lambda',[],'y']]],['progn',['setq','y',59],['funcall','f']]]]),
 'closure_default':(['x','&optional',['f',['lambda',[],'x']]],['progn',['setq','x',61],['funcall','f']]),
 'closure_optional_factory':(['&optional',['x',7,'xp']],['lambda',[],['values','x','xp']]),
 'closure_optional':([],['values',['funcall',['closure_optional_factory']],['funcall',['closure_optional_factory',19]]]),
 'closure_key_factory':(['&key',['x',11,'xp']],['lambda',[],['values','x','xp']]),
 'closure_key':([],['funcall',['closure_key_factory',':x',29]]),
 'closure_rest_factory':(['&rest','r'],['lambda',[],'r']),
 'closure_rest':([],['funcall',['closure_rest_factory',7,11,13]]),
 'closure_apply':(['x','xs'],['apply',['cell_factory','x'],'xs']),
 'closure_keep':(['x','v'],['let',[['f',['cell_factory','x']]],['multiple-value-prog1',['values',['funcall','f'],'f'],['funcall','f','v']]]),
 'closure_fail_escape':(['p','x','f'],['let',[['g',['cell_factory','x']]],['progn',['rplaca','p','g'],['funcall','f']]]),
 'closure_multiset':(['x','y'],['progn',['setq','x','y','y',17],['values','x','y']]),
 'closure_many_captures':(['x','y','z'],['let',[['f',['lambda',[],['values','x','y','z']]]],['funcall','f']]),
 'closure_nested_mutate':(['x','v'],['let',[['outer',['lambda',[],['lambda',['v'],['setq','x','v']]]]],['let',[['inner',['funcall','outer']]],['values',['funcall','inner','v'],'x']]]),
 'closure_same':(['x'],['let',[['f',['factory','x']]],['values','f','f']]),
})
FORMS.update({
 'closure_capture_closure':(['x'],['funcall',['funcall',['factory',['factory','x']]]]),
 'closure_function_syntax':(['x'],['let',[['f',['function',['lambda',[],'x']]]],['funcall','f']]),
 'closure_optional_empty':([],['funcall',['closure_optional_factory']]),
 'closure_optional_full':([],['funcall',['closure_optional_factory',23]]),
 'closure_key_empty':([],['funcall',['closure_key_factory']]),
 'closure_bad_default':(['x','f','&optional',['v',['funcall','f']]],['lambda',[],'x']),
 'closure_default_capture':(['x','&optional',['f',['lambda',[],'x']],['v',['funcall','f']]],['values','v',['funcall','f']]),
 'closure_three_levels':(['x'],['let',[['f',['lambda',[],['lambda',[],['lambda',[],'x']]]]],['funcall',['funcall',['funcall','f']]]]),
 'closure_let_order':(['p'],['let',[['a',['progn',['rplaca','p',17],['car','p']]],['b',['progn',['rplacd','p',19],['car','p']]]],['let',[['f',['lambda',[],['values','a','b',['car','p'],['cdr','p']]]]],['funcall','f']]]),
})
wide=[f'c{i}' for i in range(129)]
FORMS['closure_wide']=(wide,['let',[['f',['lambda',[],['values',*wide]]]],['funcall','f']])
# The dictionaries are ordered with required callees before callers.
def render(x):return '('+' '.join(map(render,x))+')' if isinstance(x,list) else str(x)
def bound_words(vs):
 mode='required';opt=[];keys=[];rest=0
 for v in vs:
  if v=='&optional':mode='optional'
  elif v=='&rest':mode='rest'
  elif mode=='rest':rest=1;mode='after-rest'
  elif v=='&key':mode='key'
  elif v=='&allow-other-keys':pass
  elif mode=='optional':opt.append(v if isinstance(v,list) else [v])
  elif mode=='key':keys.append(v)
 # U1 provides internal optional presence variables when a default is non-NIL
 # or any explicit supplied-p parameter exists; all keys have presence slots.
 hard=any(len(v)>2 or (len(v)>1 and v[1]!='nil') for v in opt)
 return len(opt)*(2 if hard else 1)+2*len(keys)+rest
def modules():return [dict(name=n,source=render(['lambda',vs,body]),bound_words=bound_words(vs)) for n,(vs,body) in FORMS.items()]
BINDINGS={}
class Condition(Exception):
 def __init__(self,kind):self.kind=kind

class Cell:
 def __init__(self,value):self.value=value
class Environment(dict):
 def get(self,key,default=None):return dict.get(self,key,Cell(default)).value
 def __setitem__(self,key,value):dict.__setitem__(self,key,Cell(value))
 def assign(self,key,value):dict.__getitem__(self,key).value=value
 def update(self,items):
  for k,v in items:self[k]=v
class Closure:
 def __init__(self,parameters,body,env):self.parameters=parameters;self.body=body;self.env=env.copy()
def evaluate(name,inputs,nodes):
 if isinstance(name,Closure):vs,body=name.parameters,name.body;env=Environment(name.env)
 else:
  if name not in FORMS:raise Condition('DESIGNATOR')
  vs,body=FORMS[name];env=Environment()
 def single(expr):
  values=run(expr);return values[0] if values else 'nil'
 def run(expr):
  if not isinstance(expr,list):return [env.get(expr,expr)]
  op,*args=expr
  if op=='lambda':return [Closure(args[0],args[1],env)]
  if op=='function' and isinstance(args[0],list):return run(args[0])
  if op in ('let','let*'):
   saved=env.copy()
   try:
    pending=[]
    for binding in args[0]:
     var,init=binding if isinstance(binding,list) else (binding,'nil')
     value=single(init)
     if op=='let*':env[var]=value
     else:pending.append((var,value))
    for var,value in pending:env[var]=value
    return run(args[1])
   finally:
    env.clear();dict.update(env,saved)
  if op=='setq':
   value='nil'
   for var,expr in zip(args[::2],args[1::2]):value=single(expr);env.assign(var,value)
   return [value]
  if op in ('quote','function'):return [('s:'+args[0] if op=='quote' else 'f:'+BINDINGS.get(args[0],args[0]))]
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
  if op=='apply':
   designator=single(args[0]);actual=[single(x) for x in args[1:-1]];tail=single(args[-1]);seen=set()
   while tail!='nil':
    if not isinstance(tail,str) or not(tail.startswith('n') and tail[1:].isdigit()):raise Condition('TYPE')
    if tail in seen:raise Condition('CIRCULAR')
    seen.add(tail);car,tail=nodes[int(tail[1:])];actual.append(car)
   if isinstance(designator,Closure):return evaluate(designator,actual,nodes)
   if not isinstance(designator,str) or not designator.startswith(('f:','s:')):raise Condition('DESIGNATOR')
   return evaluate(BINDINGS.get(designator[2:],designator[2:]) if designator.startswith('s:') else designator[2:],actual,nodes)
  if op=='funcall':
   designator=single(args[0]);actual=[single(x) for x in args[1:]]
   if isinstance(designator,Closure):return evaluate(designator,actual,nodes)
   if not isinstance(designator,str) or not designator.startswith(('f:','s:')):raise Condition('DESIGNATOR')
   return evaluate(BINDINGS.get(designator[2:],designator[2:]) if designator.startswith('s:') else designator[2:],actual,nodes)
  return evaluate(BINDINGS.get(op,op),[single(x) for x in args],nodes)
 # Parse this declared corpus independently of compiler IR. Bind in order.
 mode='required';required=[];optional=[];keywords=[];allow=False;has_keys=False;rest=None
 for x in vs:
  if x=='&optional':mode='optional';continue
  if x=='&rest':mode='rest';continue
  if mode=='rest':rest=x;mode='after-rest';continue
  if x=='&key':mode='key';has_keys=True;continue
  if x=='&allow-other-keys':allow=True;continue
  if mode=='required':required.append(x)
  else:
   spec=x if isinstance(x,list) else [x];var=spec[0];default=spec[1] if len(spec)>1 else 'nil';sp=spec[2] if len(spec)>2 else None
   if mode=='optional':optional.append((var,default,sp))
   else:
    key,var=(var[0],var[1]) if isinstance(var,list) else (':'+var,var)
    keywords.append((key,var,default,sp))
 if len(inputs)<len(required) or (not has_keys and rest is None and len(inputs)>len(required)+len(optional)):raise Condition('ARITY')
 env.update(zip(required,inputs));at=len(required)
 for var,default,sp in optional:
  present=at<len(inputs);env[var]=inputs[at] if present else single(default)
  if sp:env[sp]='t' if present else 'nil'
  at+=1
 if rest is not None:
  head='nil'
  for value in reversed(inputs[at:]):nodes.append([value,head]);head='n'+str(len(nodes)-1)
  env[rest]=head
 if has_keys:
  tail=inputs[at:]
  if len(tail)%2:raise Condition('ARITY')
  first={}
  for k,v in zip(tail[::2],tail[1::2]):first.setdefault(k,v)
  if not allow and first.get(':allow-other-keys','nil')=='nil' and any(k not in [x[0] for x in keywords]+[':allow-other-keys'] for k in first):raise Condition('ARITY')
  for key,var,default,sp in keywords:
   env[var]=first[key] if key in first else single(default)
   if sp:env[sp]='t' if key in first else 'nil'
 return run(body)
def normalize(values,nodes,original):
 # Preserve original graph identities; name new reachable cells by discovery,
 # so the three oracles need not allocate lists in the same physical order.
 order=list(range(original));names={i:i for i in order};closures={}
 def token(x):
  if isinstance(x,Closure):
   if x not in closures:closures[x]='c'+str(len(closures))
   return closures[x]
  if isinstance(x,str) and x.startswith('n') and x[1:].isdigit():
   i=int(x[1:])
   if i not in names:names[i]=len(order);order.append(i)
   return 'n'+str(names[i])
  return x
 result=[token(x) for x in values];pairs=[];i=0
 while i<len(order):pairs.append([token(x) for x in nodes[order[i]]]);i+=1
 return result,pairs

def cases():
 out=[]
 def add(name,args,nodes=None,capacity=64,bindings=None,closure_bytes=0):
  global BINDINGS
  BINDINGS=dict(bindings or {})
  before=[p[:] for p in (nodes or [])];after=[p[:] for p in before]
  try:expected={'status':'RETURN','values':evaluate(name,args,after),'nodes':after}
  except Condition as e:expected={'status':e.kind,'values':[],'nodes':after}
  values,visible=normalize(expected['values'],after,len(before));expected.update(values=values,nodes=visible)
  out.append(dict(id=f'{name}-{len(out):03}',function=name,args=args,capacity=capacity,bindings=BINDINGS,nodes=before,expected=expected,allocated_cells=len(after)-len(before),closure_bytes=closure_bytes))
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
 for args in ([],[1],[1,2],[1,2,3],[1,2,3,4],['nil'],['t','nil'],['n0','n1','n0']):add('opt',args,[[4,5],[6,7]])
 for args in ([],[7],[7,8],[7,8,9]):add('opt_nil',args)
 for args in (['n0'],['n0',3],['n0',3,5],['n0',3,5,7],['nil']):add('opt_effect',args,[[2,4]])
 for f in ('f:v0','f:v2',3):
  add('opt_failure',['n0',f],[[3,4]]);add('opt_failure',['n0',f,91],[[3,4]])
  add('key_failure',['n0',f],[[3,4]]);add('key_failure',['n0',f,':a',91],[[3,4]])
 for a in (['n0'],['n0',19]):add('opt_forward',a,[[7,9]])
 keyargs=[[],[':a',5],[':b',7],[':b',7,':a',5],[':a','nil'],[':a',5,':a',9],[':b','nil',':b',7],[':bad',7],[':a'],[':bad',7,':allow-other-keys','t'],[':allow-other-keys','t',':bad',7],[':allow-other-keys','nil',':bad',7,':allow-other-keys','t'],[':allow-other-keys','t',':bad',7,':allow-other-keys','nil'],[7,9],[7,9,':allow-other-keys','t'],[':allow-other-keys','nil'],[':a',':b'],[':a','n0',':b','n1']]
 for args in keyargs:
  for name in ('key','key_allow','key_empty','key_empty_allow','key_bind_allow'):add(name,args,[[3,4],[5,6]])
  add('key_effect',['n0']+args,[[3,4],[5,6]])
 for args in ([],[':external',7],[':external','nil'],[':external',7,':external',9],[':b',13],[':a',7]):add('key_alias',[29]+args)
 for args in ([7],[7,9],[7,9,':a',11],[7,9,':b',13],[7,9,':b',13,':a',11],[7,':a',11],[7,9,':bad',11],[7,9,':bad',11,':allow-other-keys','t']):add('opt_key',args)
 for name in ('key_caller','opt_key_caller'):add(name,['n0'],[[61,67]])
 for f in ('f:key_effect','f:key_allow',7):add('key_dynamic',[f,'n0'],[[3,4]])
 # Full 64-word incoming region and first/last duplicate semantics.
 add('key',[':a',7]+[':a',9]*31);add('key',[':bad',3]*31+[':allow-other-keys','t'])
 for n in (0,1,2,63,64,65,129,1024):add('rest_all',list(range(n)))
 for args in ([7],[7,9],[7,9,11,13],['n0','n1','n0','n1']):add('rest_parts',args,[[1,2],[3,4]])
 for args in ([],[':a',7],[':b',9,':a',7],[':a',7,':a',9],[':bad',7],[':a'],[':bad',7,':allow-other-keys','t']):add('rest_key',args)
 for args in (['n0'],['n0',31],['n0',31,41,43]):add('rest_default',args,[[5,6]])
 for name in ('rest_copies','rest_escape'):add(name,['n0'],[[3,4]])
 add('rest_mutate',[1,2,3]);add('rest_mutate',[])
 for f in ('f:v0','f:v2',3):add('rest_key_fail',['n0',f,':b',7],[[3,4]])
 def chain(values,tail='nil'):
  return [[x,('n'+str(i+1) if i+1<len(values) else tail)] for i,x in enumerate(values)]
 for n in (0,1,2,6,65,129,1024):
  nodes=chain(list(range(n)));xs='n0' if n else 'nil'
  for f in ('f:rest_all','f:v0','f:v2'):
   add('apply0',[f,xs],nodes);add('apply2',[f,71,73,xs],nodes)
 for xs,nodes in [(7,[]),('n0',[[11,7]]),('n0',[[11,'n1'],[13,7]])]:add('apply0',['f:rest_all',xs],nodes)
 for f in ('f:rest_all','f:v2',7):add('apply_effect',['n0',f,'n1'],[[8,9],[11,'nil']])
 add('apply_rest',['f:rest_all',7,9,11]);add('apply_rest',['f:v0']);add('apply_rest',['f:v2',1])
 for name in ('apply_nested','apply_keep'):add(name,['f:v6','n0'],chain(list(range(6))))
 add('apply_nil',['f:v2',17,19]);add('apply_built_list',['f:v2','n0'],[[3,4]])
 for f in ('f:v1','f:rest_all'):add('apply_type_fail',[f,'n0'],[[5,'nil']])
 add('call_long',[]);add('call_required_long',[])
 add('key',[':a',7]*512);add('key',[':bad',7]*511+[':allow-other-keys','t'])
 add('apply0',['f:key','n0'],chain([':a',7]*512))
 for n in (65,128,129,257,512,1024):
  cap=4*((n+3)//4);args=[(-i if i%2 else i) for i in range(n)]
  add(f'v{n}',args,capacity=cap)
  if n<=512:
   add(f'call{n}',args,capacity=cap)
   add('apply0',[f'f:v{n}','n0'],chain(args),capacity=cap)
   add('apply_keep',[f'f:v{n}','n0'],chain(args),capacity=max(64,cap))
 for cap in (132,256):
  for name in ('many','keep_large','keep_large_nested','many_optional','many_keyword','many_scalar','large_prog1','large_effects','bound_after_many'):
   add(name,['n0'],[[17,23]],capacity=cap)
  for flag in ('nil','t'):add('many_if',['n0',flag],[[17,23]],capacity=cap)
  for f in ('f:v0','f:v2',3):add('many_failure',['n0',f],[[17,23]],capacity=cap)
 add('bound_after_full',['n0'],[[17,23]],capacity=128)
 add('discard_values',[],capacity=132)
 for cap in (0,4,8,68,132,512):
  add('v0',[],capacity=cap)
  if cap:add('v1',[37],capacity=cap)
 for x in ('nil',7,'n0'):
  for name in ('quoted_call','function_call','self_named'):add(name,[x],[[17,19]])
 for name in ('function_value','quoted_value'):add(name,[])
 for name in ('quoted_apply','function_apply'):add(name,['n0'],chain([31,37]))
 for name in ('walk_list','mutual_a','mutual_b','recursive_keep'):
  for n in (0,1,2,8,16):add(name,['n0' if n else 'nil'],chain(list(range(n))))
 for f in ('s:v2','s:mutate','s:v1'):add('dynamic2',[f,'n0',17],[[3,5]])
 add('apply0',['s:v6','n0'],chain(list(range(6))))
 for target in ('alternate','v0','v2'):
  for name,args in [('call1',[37]),('quoted_call',[37]),('function_call',[37]),('function_value',[]),('dynamic_one',['s:v1',37]),('dynamic_one',['f:v1',37])]:add(name,args,bindings={'v1':target})
 # Literal byte accounting: each captured cell 8; function 24; one/two/three
 # capture environments 8/16/16. Rest-list cells are counted separately.
 for x in (7,'nil','t','n0',-536870912,536870911):
  add('closure_call',[x],[[3,5]],closure_bytes=40)
  add('closure_set',[x,23],[[3,5]],closure_bytes=40)
  add('closure_siblings',[x,23,'n0'],[[3,5]],closure_bytes=72)
  add('closure_distinct',[x,29],[[3,5]],closure_bytes=80)
  add('closure_nested',[x],[[3,5]],closure_bytes=72)
  for name in ('closure_shadow','closure_parallel','closure_parent_write','closure_local_write','closure_default'):
   add(name,[x],[[3,5]],closure_bytes=40)
  add('closure_sequential',[x],[[3,5]],closure_bytes=40)
  add('closure_nested_mutate',[x,31],[[3,5]],closure_bytes=72)
  add('closure_same',[x],[[3,5]],closure_bytes=40)
  add('closure_keep',[x,37],[[3,5]],closure_bytes=40)
  add('closure_fail_escape',['n0',x,7],[[3,5]],closure_bytes=40)
  add('closure_apply',[x,'nil'],[[3,5]],closure_bytes=40)
  add('closure_apply',[x,'n0'],[[43,'nil']],closure_bytes=40)
 add('closure_empty',[],closure_bytes=24)
 add('closure_optional',[],closure_bytes=112)
 add('closure_key',[],closure_bytes=56)
 add('closure_rest',[],closure_bytes=40)
 add('closure_many_captures',[7,11,13],closure_bytes=64)
 add('closure_multiset',[7,11])
 for name in ('closure_capture_closure','closure_function_syntax','closure_default_capture','closure_three_levels'):
  add(name,['n0'],[[17,19]],closure_bytes={'closure_capture_closure':80,'closure_three_levels':104}.get(name,40))
 for name in ('closure_optional_empty','closure_optional_full','closure_key_empty'):add(name,[],closure_bytes=56)
 add('closure_bad_default',[17,5],closure_bytes=8)
 add('closure_let_order',['n0'],[[3,5]],closure_bytes=64)
 add('closure_wide',list(range(129)),capacity=132,closure_bytes=1576)
 return out

def lisp_input():
 def lit(x):
  if isinstance(x,list):return '('+' '.join(map(lit,x))+')'
  return json.dumps(x) if isinstance(x,str) else str(x)
 return '(in-package "CL-USER")\n(defparameter *call-sources* \''+lit([[m['name'],m['source']] for m in modules()])+')\n(defparameter *call-cases* \''+lit([[c['id'],c['function'],c['nodes'],c['args'],[list(pair) for pair in c['bindings'].items()]] for c in cases()])+')\n'
REFUSALS=[('escaped-key-literal','(lambda () (values :A :|a|))'),('escaped-key-parameter','(lambda (&key ((:|a| x))) x)'),('host-macro','(lambda (p) (typep p \'fixnum))'),('missing-rest-var','(lambda (&rest) nil)'),('rest-extra-var','(lambda (&rest p q) p)'),('aux','(lambda (&aux p) p)'),('bad-key','(lambda (&key ((p x))) x)'),('bad-order','(lambda (&key a &optional b) a)'),('duplicate-var','(lambda (a &optional a) a)'),('forward-default','(lambda (&optional (a b) b) a)'),('macro-default','(lambda (&optional (a (typep nil \'fixnum))) a)'),('apply-missing-tail','(lambda (p) (apply p))'),('local-function','(lambda (p) (flet ((f () p)) (f)))'),('unknown','(lambda (p) (unlinked p))'),('empty-prog1','(lambda () (prog1))'),('heap-constant','(lambda () \'(1 2))'),('cycle','(lambda (p) #1=(progn . #1#))'),('dotted','(lambda (p) (v1 . p))'),('extra-form','(lambda (p) p) 2')]
REFUSALS += [('inlined-lambda-bind','(lambda (x) (funcall (lambda () x)))'),('unbound-setq','(lambda (x) (setq y x))'),('special-declaration','(lambda (x) (let ((y x)) (declare (special y)) (lambda () y)))'),('inner-host-macro',"(lambda (x) (lambda () (typep x 'fixnum)))"),('duplicate-let','(lambda (x) (let ((a x) (a 7)) a))'),('inner-aux','(lambda (x) (lambda (&aux y) x))'),('inner-forward-default','(lambda (x) (lambda (&optional (a b) b) x))'),('setf-place','(lambda (x) (setf x 7))'),('labels','(lambda (x) (labels ((f () x)) (f)))'),('do-loop','(lambda (x) (loop repeat 3 do (setq x nil)))')]
old_input=lisp_input
def lisp_input():return old_input()+'(defparameter *call-refusals* \''+'('+' '.join('('+json.dumps(n)+' '+json.dumps(s)+')' for n,s in REFUSALS)+'))\n'
