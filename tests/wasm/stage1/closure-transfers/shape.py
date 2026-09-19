"""Inspect the generated function body, independently of emitter proof decisions."""
import json
from pathlib import Path
def body(text):
 a=text.index('(func $body ');depth=0;quoted=False;escape=False
 for i in range(a,len(text)):
  c=text[i]
  if quoted:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c=='"':quoted=False
  elif c=='"':quoted=True
  elif c=='(':depth+=1
  elif c==')':
   depth-=1
   if depth==0:return text[a:i+1]
 raise ValueError('unterminated function body')
def inspect(compiled):
 rows=[]
 for name in ['fast_loop','fast_choices','fast_fallthrough','fast_pending']:
  t=body((compiled/(name+'.wat')).read_text())
  assert '(loop $tag_branch_' in t,name+' no direct loop'
  assert '(call $control_push ' not in t,name+' loop control overhead'
  assert '(throw $nonlocal_exit' not in t,name+' loop exception overhead'
  rows.append(dict(name=name,branch_loops=t.count('(loop $tag_branch_'),control_pushes=0,exit_throws=0))
 for name in ['go_operand','go_pending','closed_cleanup','handler_cleanup','closed_binding']:
  t=body((compiled/(name+'.wat')).read_text())
  assert '(call $control_push ' in t,name+' missing unwind frame'
  rows.append(dict(name=name,control_pushes=t.count('(call $control_push '),unwind_required=True))
 return rows
if __name__=='__main__':
 import sys
 Path(sys.argv[2]).write_text(json.dumps(inspect(Path(sys.argv[1])),indent=2,sort_keys=True)+'\n')
