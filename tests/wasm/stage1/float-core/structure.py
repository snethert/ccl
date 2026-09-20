"""Check the emitted module, including actual stack floor and call graph."""
import re

def run(out,driver):
 driver.command(['/usr/local/bin/wasm2wat',out/'float.wasm','-o',out/'float.wat'],out/'decode.log')
 s=(out/'float.wat').read_text();assert '(data ' not in s and '(start ' not in s and '(elem ' not in s
 assert not re.search(r'\b(?:call_indirect|return_call_indirect|memory\.grow)\b',s)
 assert re.search(r'\(global \(;0;\) \(mut i32\) \(i32.const 131072\)\)',s),'reserved C stack floor'
 graph={};current=None
 for line in s.splitlines():
  m=re.match(r'  \(func \(;([0-9]+);\)',line)
  if m:current=int(m[1]);graph[current]=[]
  m=re.match(r'\s+(?:return_)?call ([0-9]+)(?:\s|$)',line)
  if m:assert current is not None;graph[current].append(int(m[1]))
 assert graph and all(n in graph or n<4 for xs in graph.values() for n in xs)
 def visit(n,active):
  assert n not in active,'numeric recursion'
  for target in graph.get(n,[]):visit(target,active|{n})
 for n in graph:visit(n,set())
 driver.save(out/'structure.json',dict(status='PASS',functions=graph,detector_imports=4,stack_top=131072,data_segments=0,cycles=0))
