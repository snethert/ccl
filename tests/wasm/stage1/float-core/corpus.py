"""Independent exact-rational oracle, including integer/float comparisons."""
import importlib.util,math,random,struct
from fractions import Fraction
from pathlib import Path
HERE=Path(__file__).resolve().parent
p=HERE.parents[1]/'stage0/float-detection/ieee.py';s=importlib.util.spec_from_file_location('fp_ieee',p);ieee=importlib.util.module_from_spec(s);s.loader.exec_module(ieee)
OPS=['add','sub','mul','div','lt','le','eq','ne','ge','gt','single','double']
MASKS=[0,1,2,4,8,16,7,31]
def bits(x,w):
 if math.isnan(x):return 'nan'
 return struct.pack('>f' if w==32 else '>d',x).hex()
def number(x,w=None):return dict(kind='integer',value=str(x)) if w is None else dict(kind=str(w),bits=bits(x,w))
def value(x):
 if x['kind']=='integer':return int(x['value'])
 if x['bits']=='nan':return math.nan
 return struct.unpack('>f' if x['kind']=='32' else '>d',bytes.fromhex(x['bits']))[0]
def flags(s):return {0:0,1:20,2:2,3:1,4:24,5:16}[s]
def chosen(f,mask,safe):
 x=f&mask if safe else 0
 return x&-x

def coerce(x,w,full,safe):
 a=value(x)
 if x['kind']=='integer':
  r,fs=ieee.round_binary(Fraction(a),ieee.SINGLE if w==32 else ieee.DOUBLE);status=ieee.status_of(fs);r=float(r)
 elif x['kind']=='64' and w==32 and math.isfinite(a):
  r,fs=ieee.round_binary(Fraction(a),ieee.SINGLE);status=ieee.status_of(fs);r=float(r)
  if a==0:r=a
 else:r=a;status=0
 if not full and status in (4,5):status=0
 return r,flags(status) if safe else 0

def expected(op,a,b,mask,safe):
 x,y=value(a),value(b)
 w=32 if op=='single' else 64 if op=='double' else 64 if a['kind']=='64' or b['kind']=='64' else 32
 base=dict(width=w,flags=0,condition=0,stage=3,a_flags=0,b_flags=0)
 if op in OPS[4:10]:
  unordered=(isinstance(x,float) and math.isnan(x)) or (isinstance(y,float) and math.isnan(y))
  if unordered:v=op=='ne'
  else:v={'lt':x<y,'le':x<=y,'eq':x==y,'ne':x!=y,'ge':x>=y,'gt':x>y}[op]
  f=1 if safe and unordered else 0;c=chosen(f,mask,safe)
  return dict(base,width=0,flags=f,condition=c,value='NIL' if c or not v else 'T')
 full=bool(safe and mask&24);x,fa=coerce(a,w,full,safe);c=chosen(fa,mask,safe)
 if c:return dict(base,flags=fa,a_flags=fa,condition=c,stage=1,value='NIL')
 if op in ('single','double'):return dict(base,flags=fa,a_flags=fa,stage=1,value=bits(x,w))
 y,fb=coerce(b,w,full,safe);c=chosen(fb,mask,safe)
 if c:return dict(base,flags=fb,a_flags=fa,b_flags=fb,condition=c,stage=2,value='NIL')
 status,r=ieee.expected(op,x,y,ieee.SINGLE if w==32 else ieee.DOUBLE)
 if not full and status in (4,5):status=0
 f=flags(status) if safe else 0;c=chosen(f,mask,safe)
 return dict(base,flags=f,condition=c,a_flags=fa,b_flags=fb,value='NIL' if c else bits(r,w))

def cases():
 rows=[]
 def add(name,op,a,b=None,masks=(7,31),safes=(1,)):
  b=b or number(0)
  for safe in safes:
   for mask in masks:rows.append(dict(name=f'{name}/m{mask}/s{safe}',op=op,a=a,b=b,mask=mask,safe=safe,expected=expected(op,a,b,mask,safe)))
 for w in [32,64]:
  fmt=ieee.SINGLE if w==32 else ieee.DOUBLE
  mn=math.ldexp(1.0,fmt['emin']);sub=math.ldexp(1.0,fmt['emin']-fmt['p']+1)
  mx=float((2-Fraction(2)**(1-fmt['p']))*Fraction(2)**fmt['emax'])
  samples=[0.,-0.,1.,-1.,3.,-7.,mn,-mn,sub,-sub,mx,-mx,math.inf,-math.inf,math.nan]
  for i,a in enumerate(samples):
   for j,b in enumerate(samples):
    for op in OPS[:4]:add(f'{w}-{op}-{i}-{j}',op,number(a,w),number(b,w),MASKS,(0,1))
    for op in OPS[4:10]:add(f'{w}-{op}-{i}-{j}',op,number(a,w),number(b,w),(0,7),(1,))
  p=fmt['p']
  for sign in [-1,1]:
   for k in [p-1,p,p+1,127,128,1023,1024,32767]:
    for delta in [-1,0,1]:
     integer=sign*((1<<k)+delta)
     add(f'coerce-{w}-{sign}-{k}-{delta}','single' if w==32 else 'double',number(integer),masks=MASKS)
     if k<1025:
      for op in OPS[:4]:add(f'mixed-{w}-{sign}-{k}-{delta}-{op}',op,number(integer),number(3.,w))
  for k in [24,53,100,1023,1024,32767]:
   for delta in [-1,0,1]:
    a=number((1<<k)+delta);b=number(math.ldexp(1.,k) if k<1024 else math.inf,w) if (w==64 or k<=127 or k>=1024) else number(math.inf,w)
    for op in OPS[4:10]:
     add(f'exact-order-{w}-{k}-{delta}-{op}',op,a,b,(0,31))
     add(f'exact-order-reverse-{w}-{k}-{delta}-{op}',op,b,a,(0,31))
 # f32 tininess after rounding: below, at and above quarter-subnormal cutoff.
 for i,x in enumerate([float(Fraction(2)**-126-Fraction(2)**-151+d*Fraction(2)**-175) for d in [-1,0,1]]):
  add(f'single-tiny-{i}','single',number(x,64),masks=MASKS)
 # The integer must round directly to f32, not through a rounded double.
 for sign in [-1,1]:
  for k in [55,80,120]:
   x=sign*((1<<k)+(1<<(k-24))+1)
   add(f'double-round-{sign}-{k}','single',number(x),masks=MASKS)
 for i in range(-4,5):
  for j in range(-4,5):
   for op in ['mul','div']:
    a=dict(kind='32',bits=f'{0x00800000+i:08x}');b=dict(kind='32',bits=f'{0x3f800000+j:08x}')
    add(f'single-boundary-{i}-{j}-{op}',op,a,b,(7,8,16,31))
 add('mixed-precision','add',number(1.,32),number(2**-30,64),(0,7,31))
 rng=random.Random(160064)
 def randfloat(w):
  raw=rng.getrandbits(w);return dict(kind=str(w),bits=raw.to_bytes(w//8,'big').hex())
 for i in range(1200):
  w=rng.choice([32,64]);a=randfloat(w);b=number(rng.getrandbits(rng.choice([30,54,128,1024]))*rng.choice([-1,1])) if i%3==0 else randfloat(rng.choice([32,64]))
  add('random-'+str(i),rng.choice(OPS[:10]),a,b,(7,31),(1,))
 return rows
