import json,subprocess
from corpus import number,expected

def faults():
 return [
  ('stack-floor','TOOLCHAIN','TOOLCHAIN','add',number(0.,32),number(0.,32),0),
  ('round-tie','sticky||(sig&1)','sticky||1','single',number(2**24+1),number(0),0),
  ('round-sticky','sticky|=bit(a,j);','sticky|=0;','single',number(2**55+2**31+1),number(0),0),
  ('mixed-format','a.kind==64||b.kind==64','a.kind==64&&b.kind==64','add',number(1.,32),number(2**-30,64),7),
  ('integer-fraction-compare','if(!c&&fraction)c=-1;','if(!c&&fraction)c=0;','lt',number(0),number(2**-1074,64),7),
  ('rounded-integer-compare','if(inf(f))return f>0?-1:1;', 'if(inf(f))return f>0?-1:1; U st;double rounded=integer_float(a,64,&st);return rounded<f?-1:rounded>f?1:0;', 'eq',number(2**53+1),number(2**53,64),7),
  ('quiet-nan-comparison','f=safe&&unordered?1:0;','f=0;', 'lt',number(float('nan'),64),number(1.,64),7),
  ('underflow-inexact','s==4?24','s==4?16','mul',number(2**-149,32),number(.5,32),31),
  ('boundary-tie','mag<0x1p-126-0x1p-151','mag<=0x1p-126-0x1p-151','single',number(2**-126-2**-151,64),number(0),31),
  ('lost-small-addend','exact=r==sum&&err==0','exact=r==sum&&(err==0||1)','add',number(1.,32),number(2**-149,32),31),
  ('unneeded-witness','full=safe&&(mask&24)','full=safe','add',number(1.,64),number(1.,64),7),
  ('wrong-priority','return x&1?1:x&2?2:','return x&16?16:x&1?1:x&2?2:','mul',number(float.fromhex('0x1.fffffep127'),32),number(2.,32),31),
  ('lost-negative-zero','D x={.f=r};GET(out)=791','D x={.f=r==0?0:r};GET(out)=791','add',number(-0.,64),number(-0.,64),7),
  ('early-publication','if((W)out+size>limit)return 3;','GET(result)=99;if((W)out+size>limit)return 3;','add',number(1.,64),number(1.,64),7),
  ('strict-reservation','if((W)out+size>limit)','if((W)out+size>=limit)','add',number(1.,64),number(1.,64),7),
 ]
def run(out,driver):
 rows=[]
 for name,old,new,op,a,b,mask in faults():
  p=out/name;p.mkdir();source=(driver.HERE/'float.c').read_text();assert name=='stack-floor' or source.count(old)==1,(name,source.count(old));(p/'float.c').write_text(source.replace(old,new))
  driver.command([driver.CLANG,*[x for x in driver.FLAGS if name!='stack-floor' or x!='-fno-jump-tables'],p/'float.c','-o',p/'float.wasm'],p/'build.log')
  safe=0 if name=='stack-floor' else 1
  focus=[dict(name=name,op=op,a=a,b=b,mask=mask,safe=safe,expected=expected(op,a,b,mask,safe))];driver.save(p/'cases.json',focus)
  driver.command([driver.NODE,out/'execute.mjs',out/'float.wasm',out/'detector.wasm',p/'cases.json',p/'positive.json'],p/'positive.log')
  oracle='no-output-space' if name=='early-publication' else 'exact-fit-32' if name=='strict-reservation' else name
  try:driver.command([driver.NODE,out/'execute.mjs',p/'float.wasm',out/'detector.wasm',p/'cases.json',p/'execution.json'],p/'execution.log')
  except subprocess.CalledProcessError:
   failure=json.loads((p/'execution.json').read_text());assert failure['status']=='FAIL' and failure['message'].startswith(oracle+':'),(name,oracle,failure);rows.append(dict(name=name,oracle=oracle,status='REJECTED'))
  else:raise AssertionError('escaped '+name)
 driver.save(out/'controls.json',rows)


def oracle_regression(out,driver):
 # Literal bit/flag expectations independent of the rational rounding helper.
 checks=[]
 for sign,raw in [(-1,'80000000'),(1,'00000000')]:
  a=number(sign*4.67e-95,64);b=number(0)
  for mask in [0,7,31]:
   got=expected('single',a,b,mask,1)
   literal=dict(width=32,flags=24 if mask==31 else 0,condition=8 if mask==31 else 0,stage=1,a_flags=24 if mask==31 else 0,b_flags=0,value='NIL' if mask==31 else raw)
   assert got==literal,(got,literal)
   checks.append(dict(sign=sign,mask=mask,expected=literal))
 driver.save(out/'oracle-signed-zero.json',checks)
 # Re-execute the genuine old expectation against the unchanged service.
 a=number(-4.67e-95,64);b=number(0);old=expected('single',a,b,0,1);old['value']='00000000'
 case=dict(name='old-oracle-negative-zero',op='single',a=a,b=b,mask=0,safe=1,expected=old)
 driver.save(out/'old-oracle-cases.json',[case])
 try:driver.command([driver.NODE,out/'execute.mjs',out/'float.wasm',out/'detector.wasm',out/'old-oracle-cases.json',out/'old-oracle-result.json'],out/'old-oracle.log')
 except subprocess.CalledProcessError:
  failure=json.loads((out/'old-oracle-result.json').read_text());message=failure['message']
  assert message.startswith('old-oracle-negative-zero:') and "80000000" in message and "00000000" in message,failure
 else:raise AssertionError('old oracle escaped')
 driver.save(out/'oracle-control.json',dict(status='REJECTED',fault='rounded Fraction zero loses source sign',literal_checks=len(checks),service_changed=False))
