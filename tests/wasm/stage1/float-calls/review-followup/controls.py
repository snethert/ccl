"""Focused old-policy and overbroad-policy rejections."""
import shutil,subprocess
from pathlib import Path

def run(e,out,driver):
 import primitive
 rows=driver.read(out/'native.json');code=primitive.source();owner=primitive.owner();result=[]
 def named(name):return next(r for r in rows if r.get('name')==name)
 faults=[
  ('old-conversion-entry',None,owner.replace('wasm.float_calculate_lisp(', 'wasm.float_calculate('),named('64/below-limit/1/m7/s1/convert')),
  ('old-right-conversion',code.replace('fb=safe&&!(native&&!b.kind&&length(&b.i)>60)?','fb=safe?'),None,named('32/below-limit/1/m7/s1/add-right')),
  ('silence-fixnum-inexact',code.replace('&&length(&a.i)>60',''),None,named('32/inexact/1/m31/s1/convert')),
  ('native-cutoff-too-low',code.replace('length(&a.i)>60','length(&a.i)>59'),None,named('64/native-fixnum-below/1/m31/s1/convert')),
  ('silence-arithmetic-flags',code.replace('f=safe?flags(status):0;','f=0;'),None,named('32/arithmetic-overflow/m7/s1')),
  ('silence-arithmetic-invalid',code.replace('f=safe?flags(status):0;','f=0;'),None,named('64/arithmetic-invalid-mul/m7/s1')),
 ]
 for name,c,o,row in faults:
  assert c is None or c!=code,name
  p=out/name;p.mkdir();shutil.copytree(out/'compiled',p/'compiled');driver.prior.save(p/'native.json',[row]);binary=out/'primitive/float.wasm'
  if c:driver.build(p/'primitive',c);binary=p/'primitive/float.wasm'
  try:driver.execute(e,p,binary,o)
  except subprocess.CalledProcessError:
   log=(p/'eager.log').read_text();assert 'AssertionError' in log and row['function']+'/'+str(row['id']) in log,(name,log[-1200:])
  else:raise AssertionError('escaped '+name)
  result.append(dict(name=name,status='REJECTED',case=row['name'],id=row['id'],expected=row['expected']))
 # The reviewed adapter remains unchanged. Exercise all three old adapter faults
 # on the new primitive, rather than assuming their old outcomes still hold.
 for name,old,new,row in [
  ('copy-same-format','if(op>=10&&op<=11&&safe<=1','if(false&&op>=10&&op<=11&&safe<=1',next(r for r in rows if r['function']=='f_identity' and r['expected'][0]=='T')),
  ('lost-native-overflow','x.integer>=limit||x.integer<=-limit','false',named('64/limit/1/m7/s1/convert')),
  ('mathematical-infinity','if(special){','if(false&&special){',next(r for r in rows if r['function']=='f_eq' and r['args'][0]==str(1<<1024)))]:
  p=out/name;p.mkdir();shutil.copytree(out/'compiled',p/'compiled');driver.prior.save(p/'native.json',[row]);original=driver.prior.command
  def altered(args,log):
   if log.name=='eager.log':
    f=p/'service.mjs';s=f.read_text();assert s.count(old)==1;f.write_text(s.replace(old,new))
   return original(args,log)
  try:
   driver.prior.command=altered
   try:driver.execute(e,p,out/'primitive/float.wasm')
   except subprocess.CalledProcessError:
    text=(p/'eager.log').read_text();assert 'AssertionError' in text and row['function']+'/'+str(row['id']) in text,(name,text[-1200:])
   else:raise AssertionError('escaped '+name)
  finally:driver.prior.command=original
  result.append(dict(name=name,status='REJECTED',case=row.get('name',row['function']),id=row['id'],expected=row['expected']))
 driver.prior.save(out/'controls.json',result)
