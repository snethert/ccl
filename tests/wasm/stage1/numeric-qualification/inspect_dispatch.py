"""Read emitted code to rule out recursive primitive fallbacks."""
import json,re
from pathlib import Path

def graph(text):
 edges={};current=None
 for line in text.splitlines():
  m=re.match(r'  \(func \(;([0-9]+);\)',line)
  if m:current=int(m[1]);edges[current]=[]
  m=re.match(r'\s+(?:return_)?call ([0-9]+)(?:\s|$)',line)
  if m:
   assert current is not None;edges[current].append(int(m[1]))
 assert edges and not re.search(r'\b(?:call_indirect|return_call_indirect)\b',text),'indirect primitive dispatch'
 done=set()
 def visit(n,active):
  assert n not in active,'recursive primitive fallback'
  if n in done:return
  for t in edges.get(n,[]):visit(t,active|{n})
  done.add(n)
 for n in edges:visit(n,set())
 return edges

def inspect_all(d,out,command):
 rows=[]
 for name,imports in [('integer',0),('float',4),('detector',0)]:
  command(['/usr/local/bin/wasm2wat',d/(name+'.wasm'),'-o',d/(name+'.wat')],d/(name+'-decode.log'))
  s=(d/(name+'.wat')).read_text();g=graph(s)
  actual=re.findall(r'\(import "([^"]+)" "([^"]+)" \(func ',s)
  assert len(actual)==imports,(name,actual)
  if name=='float':assert {m for m,n in actual}=={'detector'}
  assert '(start ' not in s and '(data ' not in s and '(elem ' not in s
  rows.append(dict(module=name,functions=g,imports=actual,cycles=0))
 # Independent controls use real disassembly with one call changed to a self
 # call, and one direct call changed into an indirect transfer.
 s=(d/'integer.wat').read_text();m=re.search(r'  \(func \(;([0-9]+);\)',s);n=m[1]
 bad=s[:m.end()]+ '\n    call '+n+'\n'+s[m.end():]
 for name,text in [('self-call',bad),('indirect-fallback',s+'\n call_indirect (type 0)\n')]:
  try:graph(text)
  except AssertionError:pass
  else:raise AssertionError(name+' escaped')
 out.write_text(json.dumps(dict(status='PASS',modules=rows,controls=['self-call','indirect-fallback'],scope='Primitive and detector call graphs. Generated numeric leaves also execute with all generated table entries poisoned; owner assurance is the reviewed synchronous no-Lisp service.'),indent=2,sort_keys=True)+'\n')
