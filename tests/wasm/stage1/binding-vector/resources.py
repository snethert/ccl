"""Owner-capacity and malformed-owner tests; no native byte-budget oracle."""
import json,shutil,subprocess
from pathlib import Path

def run(h,compiled,out):
 out.mkdir(parents=True,exist_ok=False)
 shutil.copytree(compiled,out/'compiled');d=out/'compiled'
 rows=[]
 def add(name,fn='v_bound',status='RETURN',values=None,owner=None,cap=None,allocated=None):
  rows.append(dict(id=name,function=fn,args=['s:dyn_a'],nodes=[],bindings={},capacity=16,owner=owner or {},vectorCheck=dict(cap=cap,allocated=allocated),expected=dict(status=status,values=values if values is not None else [7,11,11],nodes=[],specials=[101,103,'unbound'])))
 for index,cap in [(14,16),(15,16),(16,32),(31,32),(32,64),(37,64),(63,64),(64,128),(127,128),(128,256)]:
  add('index-'+str(index),owner=dict(index=index),cap=cap,allocated=8*((4+cap*4+7)//8))
 add('empty',owner=dict(initialCapacity=0),cap=32,allocated=136)
 add('fits',owner=dict(index=13),cap=14,allocated=0)
 add('high-global-read',fn='v_read',values=[101],owner=dict(index=536870911),cap=14,allocated=0)
 add('short-growth',status='HEAP',values=[],owner=dict(heapBytes=135),cap=14,allocated=0)
 add('exact-growth',owner=dict(heapBytes=136),cap=32,allocated=136)
 add('second-growth-failure',fn='v_nested',status='HEAP',values=[],owner=dict(heapBytes=136),cap=32,allocated=136)
 add('oversize-index',status='HEAP',values=[],owner=dict(index=16777215),cap=14,allocated=0)
 add('misaligned-allocation',status='HEAP',values=[],owner=dict(allocDelta=1),cap=14,allocated=1)
 for name,owner in [('bad-index-tag',dict(rawIndex=5)),('negative-index',dict(rawIndex=4294967292)),('null-index',dict(index=0)),('bad-vector-alignment',dict(baseDelta=1)),('bad-vector-extent',dict(vectorBase=2147549180,initialCapacity=14)),('overlap-allocation',dict(vectorBase='heap'))]:
  add(name,status='BINDING',values=[],owner=owner,cap=14,allocated=0)
 (d/'cases.json').write_text(json.dumps(rows,indent=2)+'\n')
 s=(h/'conditions.mjs').read_text();a=s.index("  for(const fault of ['fixnum'");b=s.index('\n }\n}',a);s=s[:a]+s[b:]
 (out/'harness.mjs').write_text(s)
 cmd=['/usr/local/bin/node',str(out/'harness.mjs'),str(d),str(out/'execution.json')];(out/'command.json').write_text(json.dumps(cmd))
 with (out/'execution.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
 return json.loads((out/'execution.json').read_text())
