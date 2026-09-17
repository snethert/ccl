#!/usr/bin/env python3
"""Requalify the reviewed B corpus with explicit function-layout oracle changes."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from compiler import generate
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE.parent/'b-call-errors'

def adapt_harness(s):
    s=s.replace('1322','1578').replace('x+18<=get(48)','x+26<=get(48)')
    s=s.replace('store(base+20,NIL);','store(base+20,NIL);store(base+24,NIL);store(base+28,0);')
    s=s.replace('[0,7,8,39,40]','[0,7,8,47,48]').replace('bytes<40','bytes<48').replace('?8:40','?8:48').replace('heap+120','heap+144').replace('heap+56','heap+64').replace('heap:104','heap:120').replace('heap:40','heap:48')
    return s

def prepare(out):
    out.mkdir(parents=True,exist_ok=False)
    pins={}
    import hashlib
    for p in BASE.iterdir():
        if not p.is_file():continue
        pins[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        shutil.copy(p,out/p.name)
    (out/'wasm32-backend.lisp').write_text(generate())
    for p in out.glob('*.py'):
        s=p.read_text().replace("ROOT=HERE.parents[3]",'ROOT=Path('+repr(str(ROOT))+')').replace("HERE.parent/",'Path('+repr(str(HERE.parent))+')/')
        p.write_text(s)
    for name in ('execute.mjs','conditions.mjs','loader_controls.mjs'):
        p=out/name;p.write_text(adapt_harness(p.read_text()))
    p=out/'harness_setup.py';p.write_text(p.read_text().replace(' return storage(s)',' return constants_layout(storage(s))')+'\n'+__import__('inspect').getsource(adapt_harness).replace('def adapt_harness','def constants_layout'))
    for name in ('condition_lazy.py','full_loader.py'):
        p=out/name;s=p.read_text()
        if name=='condition_lazy.py':
            s=s.replace("(out/'harness.mjs').write_text(harness)","from harness_setup import constants_layout\n harness=constants_layout(harness)\n (out/'harness.mjs').write_text(harness)")
        else:s=s.replace("(out/'controls.mjs').write_text(s)","from harness_setup import constants_layout\n s=constants_layout(s)\n (out/'controls.mjs').write_text(s)")
        p.write_text(s)
    profile='wasm32-shared-B-exnref-tail-mv-storage-constants-v1'
    for name in ('loader.mjs','binary.mjs','stub.wat'):
        p=out/name;p.write_text(p.read_text().replace('wasm32-shared-B-exnref-tail-mv-storage-v2',profile))
    layout=json.loads((out/'layout.json').read_text());f=json.loads((HERE/'function-layout.json').read_text())
    layout['function']={k:f[k] for k in ('subtag','elements','bytes','header','fields','representation')};layout['temporary_results']['profile']=profile
    (out/'layout.json').write_text(json.dumps(layout,indent=2)+'\n')
    # Count heap closures in the independent source evaluator, excluding literal
    # callables that the accepted language inlines or keeps on the stack.
    p=out/'corpus.py';s=p.read_text()
    s=s.replace('def evaluate(name,inputs,nodes):','HEAP_FUNCTIONS=0\nINLINE_LAMBDAS=set()\ndef evaluate(name,inputs,nodes):\n global HEAP_FUNCTIONS')
    s=s.replace('  nonlocal functions,declared,blocks','  nonlocal functions,declared,blocks\n  global HEAP_FUNCTIONS')
    s=s.replace("  if op in ('flet','labels'):\n", "  if op in ('flet','labels'):\n   HEAP_FUNCTIONS+=len(args[0])\n")
    s=s.replace("  if op=='lambda':\n", "  if op=='lambda':\n   if id(expr) not in INLINE_LAMBDAS:HEAP_FUNCTIONS+=1\n")
    # Count separately per case, including the extension's own case builder.
    s=s.replace('  global BINDINGS\n','  global BINDINGS,HEAP_FUNCTIONS\n  HEAP_FUNCTIONS=0\n')
    s=s.replace('closure_bytes=closure_bytes))','closure_bytes=closure_bytes+8*HEAP_FUNCTIONS,heap_functions=HEAP_FUNCTIONS))')
    # The final extension creates cases without the common add() helper.
    s=s.replace("  SPECIAL_VALUES.clear();SPECIAL_VALUES.update", "  SPECIAL_VALUES.clear();SPECIAL_VALUES.update")
    s+='''
REFUSALS=[r for r in REFUSALS if r[0]!='heap-constant']
_original_cases=cases
def cases():
 global HEAP_FUNCTIONS
 def params(vs):
  for x in vs:
   if isinstance(x,list) and len(x)>1:walk(x[1])
 def walk(x):
  if not isinstance(x,list) or not x:return
  if x[0] in ('let','let*'):
   for b in x[1]:
    if isinstance(b,list) and len(b)>1:walk(b[1])
   for v in x[2:]:walk(v)
   return
  if x[0] in ('flet','labels'):
   for f in x[1]:params(f[1]);walk(f[2])
   for v in x[2:]:walk(v)
   return
  if x[0]=='lambda':
   params(x[1])
   for v in x[2:]:walk(v)
   return
  if isinstance(x[0],list):INLINE_LAMBDAS.add(id(x[0]))
  elif x[0] in ('funcall','apply','multiple-value-call') and len(x)>1:
   f=x[1]
   if isinstance(f,list) and f and f[0]=='function':f=f[1]
   if isinstance(f,list) and f and f[0]=='lambda':INLINE_LAMBDAS.add(id(f))
  for v in x:walk(v)
 for vs,body in FORMS.values():params(vs);walk(body)
 rows=_original_cases()
 # Storage-extension rows have separate literal allocation expectations:
 # only its escaping child is a heap function; literal MVC is stack temporary.
 for row in rows:
  if 'heap_functions' not in row:
   n=1 if row['function']=='rv_literal_escape' else 0
   row['closure_bytes']+=8*n;row['heap_functions']=n
 return rows
'''
    p.write_text(s)
    (out/'sources.json').write_text(json.dumps(pins,indent=2)+'\n')
    return out

def run(evidence,out):
    out.mkdir(parents=True,exist_ok=False);h=prepare(out/'harness')
    script='''from pathlib import Path
import sys,json
from support import compile_cases,save
from replay import execute
out=Path(sys.argv[2]);e=Path(sys.argv[1])
compile_cases(e,out/'positive')
code,_=execute(out/'positive',out/'execution.log',out/'execution.json')
assert code==0,str(out/'execution.log')
from conditions import run as conditions
conditions(e,out/'conditions')
from call_errors import run as errors
errors(e,out/'call-errors')
from lazy_composition import run as lazy
lazy(out/'positive',out/'execution.json',out/'lazy')
from condition_lazy import run as clazy
clazy(out/'conditions/compiled',out/'conditions/execution.json',out/'condition-lazy')
clazy(out/'call-errors/compiled',out/'call-errors/execution.json',out/'error-lazy',call_errors=True)
from full_loader import run as full_loader
full_loader(out/'positive',out/'lazy',out/'full-loader')
from loader_controls import run as loader_controls
loader_controls(out/'positive',out/'loader-controls')
save(out/'summary.json',{'status':'PASS','corpus':json.loads((out/'execution.json').read_text()),'conditions':json.loads((out/'conditions/execution.json').read_text()),'call_errors':json.loads((out/'call-errors/execution.json').read_text())})
'''
    (h/'qualify_inherited.py').write_text(script)
    command=[sys.executable,str(h/'qualify_inherited.py'),str(evidence),str(out)]
    (out/'command.json').write_text(json.dumps(command))
    with (out/'run.log').open('w') as log:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
