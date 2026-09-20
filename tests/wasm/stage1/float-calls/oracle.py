"""Join native values to approved D6 policy; retain the exact-tiny distinction."""
import importlib.util,math
from pathlib import Path
path=Path(__file__).resolve().parent.parent/'float-core/corpus.py';spec=importlib.util.spec_from_file_location('raw_float_oracle',path);raw=importlib.util.module_from_spec(spec);spec.loader.exec_module(raw)
def apply(rows):
 differences=[];checked=0
 for r in rows:
  if not r['policy']:continue
  op=r['function'].removeprefix('h_').removesuffix('__unchecked');op={'single':'single','double':'double'}.get(op,op)
  def parse(x):
   if x.startswith('f'):return dict(kind=x[1:3],bits=x[4:])
   return dict(kind='integer',value=x)
  a,b=map(parse,r['args']);e=raw.expected(op,a,b,r['mask'],r['safe'])
  width=e['width'];limit=1<<(128 if width==32 else 1024)
  if op not in raw.OPS[4:10] and any(x['kind']=='integer' and abs(int(x['value']))>=limit for x in ([a] if op in ['single','double'] else [a,b])):e=dict(e,condition=4)
  value=str(100+e['condition']) if e['condition'] else 'nan' if e['value']=='nan' else 'f'+str(width)+':'+e['value']
  wanted=[value];checked+=1
  if wanted!=r['expected']:
   # x86 unmasked underflow traps on tiny exact results. D6 explicitly chooses
   # the masked-flag/IEEE tiny-and-inexact policy, independently of that trap.
   v=raw.value(dict(kind=str(width),bits=e['value']))
   assert r['expected']==['108'] and not e['condition'] and e['flags']==0 and v!=0 and abs(v)<(2**-126 if width==32 else 2**-1022),(r,e,wanted)
   differences.append(dict(id=r['id'],function=r['function'],args=r['args'],native=r['expected'],D6=wanted,reason='native-unmasked-exact-tiny-trap'))
  r['expected']=wanted
 return dict(checked=checked,differences=differences)
