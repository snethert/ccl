"""Exact Python integer oracle. No target output is used to derive expectations."""
import random
OPS=['add','sub','mul','ash','length','truncate']
def expected(op,a,b):
 if op=='add':return [a+b]
 if op=='sub':return [a-b]
 if op=='mul':return [a*b]
 if op=='ash':return [0 if a==0 else (a<<b if b>=0 else a>>-b)]
 if op=='length':return [(a if a>=0 else ~a).bit_length()]
 if not b:return 'division-by-zero'
 q=abs(a)//abs(b);q=-q if (a<0)!=(b<0) else q
 return [q,a-q*b]
def cases():
 rows=[]
 def add(name,op,a,b=0):
  v=expected(op,a,b);rows.append(dict(name=name,op=op,a=str(a),b=str(b),expected=[str(x) for x in v] if isinstance(v,list) else v))
 boundaries=[0,1,-1,2,-2,536870911,536870912,-536870912,-536870913]
 for k in [31,32,33,63,64,65,127,128,255,256,511,1023]:
  for delta in [-1,0,1]:
   for sign in [-1,1]:boundaries.append(sign*((1<<k)+delta))
 for i,a in enumerate(boundaries):
  add(f'length-{i}','length',a)
  for b in [0,1,-1,31,32,33,64,127,1024,-31,-32,-33,-64,-127,-1024,-(1<<63)]:add(f'shift-{i}-{b}','ash',a,b)
  for op in ['add','sub','mul','truncate']:
   for j,b in enumerate([0,1,-1,536870911,-536870912,(1<<64)-1,-((1<<64)-1)]):add(f'{op}-{i}-{j}',op,a,b)
 # Multi-limb carries/borrows, all sign combinations, and 2-result bignums.
 for k in [32,64,96,128,256,512,1024]:
  for sign in [-1,1]:
   add(f'carry-{k}-{sign}','add',sign*((1<<k)-1),sign)
   add(f'borrow-{k}-{sign}','sub',sign*(1<<k),sign)
   for ds in [-1,1]:add(f'quotrem-{k}-{sign}-{ds}','truncate',sign*((1<<(k*2))+17),ds*((1<<k)+3))
 rng=random.Random(1616)
 for i in range(400):
  op=rng.choice(OPS);a=rng.getrandbits(rng.randrange(1,1025))*rng.choice([-1,1]);b=rng.getrandbits(rng.randrange(1,513))*rng.choice([-1,1])
  if op=='ash':b=rng.randrange(-1100,1101)
  add(f'random-{i}',op,a,b)
 # Exact supported magnitude limit and resource refusal after both results prepared.
 add('max-input-positive','length',(1<<32768)-1)
 add('max-input-negative','length',-((1<<32768)-1))
 add('max-output','ash',1,32767)
 add('max-right','ash',-((1<<32768)-1),-32767)
 add('zero-enormous-left','ash',0,1<<100)
 # Chains retain target-produced bignums as the next operand, without re-encoding.
 a=1
 for i in list(range(2,161))+list(range(160,1,-1)):
  op='mul' if len([x for x in rows if x.get('chain')])<159 else 'truncate'
  add('factorial-chain-'+str(sum('chain' in x for x in rows)),op,a,i)
  rows[-1]['chain']='factorial';a=int(rows[-1]['expected'][0])
 return rows
