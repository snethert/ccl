import json
OPS=[('box','%box-s32',['s32'],'node'),('unbox','%unbox-fixnum',['node'],'s32'),('address_fixnum','%address-fixnum',['address'],'node'),('fixnum_address','%fixnum-address',['node'],'address'),('tag','%tag-misc',['address'],'node'),('untag','%untag-misc',['node'],'address'),('effective','%effective-address',['address','s32'],'address'),('header','%header-word',['node'],'u32'),('array_bytes','%array-bytes',['u32','u32'],'u32'),('issue','%issue-code',['address'],'code-id'),('validate_id','%validate-code',['node','address'],'code-id'),('validate_slot','%validate-slot',['u32','u32','u32','u32','address'],'slot')]
def modules():
 out=[dict(name='slot_target',args=['u32'],result='u32',source='(lambda (p) p)')]
 for name,op,args,result in OPS:
  vs=[f'p{i}' for i in range(len(args))];out.append(dict(name=name,args=args,result=result,source=f'(lambda ({" ".join(vs)}) ({op} {" ".join(vs)}))'))
 for name,source,args,result in [('roundtrip','(lambda (p) (%unbox-fixnum (%box-s32 p)))',['s32'],'s32'),('pointer_roundtrip','(lambda (p) (%untag-misc (%tag-misc p)))',['address'],'address'),('id_index','(lambda (n r) (%code-index (%validate-code n r)))',['node','address'],'u32'),('slot_index','(lambda (n k s v r) (%slot-index (%validate-slot n k s v r)))',['u32','u32','u32','u32','address'],'u32')]:out.append(dict(name=name,source=source,args=args,result=result))
 return out
def cases():return []
def lisp_input():
 return '(in-package "CL-USER")\n(defparameter *conversion-modules* \''+'('+ ' '.join('('+json.dumps(m['name'])+' '+json.dumps(m['source'])+' ('+' '.join(':'+a for a in m['args'])+') :'+m['result']+')' for m in modules())+'))\n'

U32=2**32;MEM=32769*65536
class Refusal(Exception):pass
def need(ok,reason):
 if not ok:raise Refusal(reason)
def signed(n):return n-U32 if n>=2**31 else n
def model(name,a,mem):
 def span(p,n):need(0<=p and p+n<=MEM,4)
 def rd(p):return mem.get(p,0)
 def ident(n,r):
  span(r,12);first,nxt,limit=rd(r),rd(r+4),rd(r+8);need(first<=nxt<=limit<=2**29,7)
  need(n%4==0 and n<2**31,2);need(first<=n//4<nxt,5);return n
 if name in ('box','roundtrip'):
  n=signed(a[0]);need(-2**29<=n<2**29,1);return (n*4 if name=='box' else n)%U32
 if name=='unbox':need(a[0]%4==0,2);return signed(a[0])//4%U32
 if name=='address_fixnum':need(a[0]<2**29,1);return a[0]*4
 if name=='fixnum_address':need(a[0]%4==0,2);need(a[0]<2**31,1);return a[0]//4
 if name in ('tag','pointer_roundtrip'):need(a[0]%8==0,3);return a[0]+6 if name=='tag' else a[0]
 if name in ('untag','header'):
  need(a[0]%8==6,2);base=a[0]-6
  if name=='untag':return base
  span(base,4);return rd(base)
 if name=='effective':n=a[0]+signed(a[1]);need(0<=n<U32,4);return n
 if name=='array_bytes':need(a[0]<2**24 and a[1]>0,1);n=a[0]*a[1];need(n<U32,4);return n
 if name=='issue':
  r=a[0];span(r,12);first,nxt,limit=rd(r),rd(r+4),rd(r+8);need(first<=nxt<=limit<=2**29,7);need(nxt<limit,6);mem[r+4]=nxt+1;return nxt*4
 if name in ('validate_id','id_index'):
  n=ident(*a);return n if name=='validate_id' else n//4
 if name in ('validate_slot','slot_index'):
  n,kind,sig,role,r=a;span(r,8);need(kind==3,9);cap,reserved=rd(r),rd(r+4);need(reserved<=cap<=8,7);need(n<cap,7);need(n>=reserved,8);q=r+8+n*8;span(q,8);need(sig>0 and rd(q)==sig,10);need(role>0 and rd(q+4)==role,11);need(n in (4,5),12);return n
 raise AssertionError(name)

def cases():
 out=[]
 def add(name,args,memory=None,label=None):
  mem=dict(memory or {});before=dict(mem);args=[n%U32 for n in args]
  try:expected={'value':model(name,args,mem),'error':0}
  except Refusal as x:expected={'value':None,'error':x.args[0]}
  out.append(dict(id=label or f'{name}-{len(out):03}',function=name,args=args,memory=[[k,v] for k,v in sorted(before.items())],after=[[k,v] for k,v in sorted(mem.items())],expected=expected))
 for name in ('box','roundtrip'):
  for n in (-2**31,-2**29-1,-2**29,-17,-1,0,1,2**29-1,2**29,2**31-1):add(name,[n])
 for name in ('unbox','fixnum_address'):
  for n in (0,4,0x7ffffffc,0x80000000,0xfffffffc,77825,77838,*range(1,8)):add(name,[n])
 for n in (0,1,2**29-1,2**29,2**31-1,2**31,2**32-1):add('address_fixnum',[n])
 for name in ('tag','pointer_roundtrip'):
  for n in (0,4096,0x7ffffff8,0x80000000,0x80000008,0xfffffff0,0xfffffff8,*range(1,8)):add(name,[n])
 for n in (6,4102,0x7ffffffe,0x80000006,0xfffffff6,0xfffffffe,*range(8)):add('untag',[n])
 for addr in (0,6,0x7ffffffe,0x80000006,0xfffffffe):
  for disp in (-2**31,-8,-6,-1,0,1,2,4,8,2**31-1):add('effective',[addr,disp])
 for base in (8192,0x7ffffff8,0x80000000,MEM-8):add('header',[base+6],{base:0xa5c30123,base+4:0x12345678},f'header-real-{base}')
 for n in (0,1,0xfffffffe,MEM+6):add('header',[n])
 for count in (0,1,2**24-2,2**24-1,2**24,2**24+1,2**32-1):
  for width in (0,1,4,8,256,257,2**32-1):add('array_bytes',[count,width])
 for first,nxt,limit in [(0,0,3),(0,2,3),(0,3,3),(7,7,8),(7,8,8),(2**29-2,2**29-2,2**29),(2**29-2,2**29-1,2**29),(2**29-2,2**29,2**29),(3,2,4),(0,5,4),(0,0,2**29+1)]:
  mem={512:first,516:nxt,520:limit};add('issue',[512],mem)
  for word in (0,4,8,28,32,0x7ffffff8,0x7ffffffc,0x80000000,77825):add('validate_id',[word,512],mem)
 for word in (0,4,8,0x7ffffffc):add('id_index',[word,512],{512:1,516:3,520:2**29})
 for name in ('issue','validate_id'):add(name,[MEM-8] if name=='issue' else [4,MEM-8])
 reg={1024:8,1028:2,1064:17,1068:23,1072:17,1076:23,1080:17,1084:23}
 for n in (0,1,2,3,4,5,6,7,8,0x80000000,0xffffffff):add('validate_slot',[n,3,17,23,1024],reg)
 for kind in (0,2,4,0xffffffff):add('validate_slot',[4,kind,17,23,1024],reg)
 for sig,role in ((0,23),(18,23),(17,0),(17,24)):add('validate_slot',[4,3,sig,role,1024],reg)
 for cap,res in ((9,2),(8,9),(1,2),(0,0)):
  mem=dict(reg);mem.update({1024:cap,1028:res});add('validate_slot',[4,3,17,23,1024],mem)
 add('slot_index',[4,3,17,23,1024],reg)
 add('validate_slot',[4,3,17,23,MEM-4]);add('validate_slot',[4,3,17,23,MEM-8],{MEM-8:8,MEM-4:2})
 # Same physical bits 4: issued code ID 1 versus callable slot 4.
 add('validate_id',[4,512],{512:0,516:2,520:4},'logical-id-bits-4')
 add('validate_slot',[4,2,17,23,1024],reg,'logical-id-not-slot')
 add('validate_slot',[4,3,17,23,1024],reg,'typed-slot-bits-4')
 return out

REFUSALS=[('address-as-integer','(lambda (p) (%box-s32 p))',['address'],'node'),('node-as-address','(lambda (p) (%tag-misc p))',['node'],'node'),('raw-as-id','(lambda (p) (%code-index p))',['u32'],'u32'),('raw-as-slot','(lambda (p) (%slot-index p))',['u32'],'u32'),('id-as-slot','(lambda (p r) (%slot-index (%validate-code p r)))',['node','address'],'u32'),('untrusted-id-entry','(lambda (p) (%code-index p))',['code-id'],'u32'),('untrusted-slot-entry','(lambda (p) (%slot-index p))',['slot'],'u32'),('wrong-result','(lambda (p) (%tag-misc p))',['address'],'address'),('host-fold','(lambda (p) (typep p \'fixnum))',['node'],'node'),('unknown-call','(lambda (p) (abs p))',['s32'],'s32'),('trailing','(lambda (p) (%box-s32 p)) 3',['s32'],'node'),('duplicate-variable','(lambda (p p) (%box-s32 p))',['s32','s32'],'node'),('dotted','(lambda (p) (%box-s32 . p))',['s32'],'node'),('circular','(lambda (p) #1=(%box-s32 . #1#))',['s32'],'node')]
_old_lisp_input=lisp_input
def lisp_input():
 def lit(x):
  if isinstance(x,list):return '('+' '.join(lit(v) for v in x)+')'
  if isinstance(x,str):return json.dumps(x)
  return str(x)
 return _old_lisp_input()+'(defparameter *conversion-cases* \''+lit([[c['id'],c['function'],c['args'],c['memory']] for c in cases()])+')\n(defparameter *conversion-refusals* \''+'('+ ' '.join('('+json.dumps(n)+' '+json.dumps(s)+' ('+' '.join(':'+a for a in args)+') :'+result+')' for n,s,args,result in REFUSALS)+'))\n'
