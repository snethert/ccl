#!/usr/bin/env python3
"""Recompile damaged emitters; a native/target oracle must reject execution."""
import json,sys
from pathlib import Path
from compiler import generate
from compile import run as compile_run
from execute_compiled import run as execute_run
MUTATIONS = {
 'header-as-slot-zero': ('(+ 4 (* 4 index)) tmp)', '(* 4 index) tmp)'),
 'lost-child-pool': ('base (pool-child-load afunc) base)', 'base "(i32.const 77825)" base)'),
 'wrong-self-root': ('(i32.load offset=24 (call $object_base (i32.load offset=40 (local.get $context))', '(i32.load offset=24 (call $object_base (i32.load offset=44 (local.get $context))'),
 'temporary-environment-overwrites-pool': ('(then (i32.store offset=2 (local.get $dispatch_self)', '(then (i32.store offset=18 (local.get $dispatch_self)'),
}
# Literal first-failure identities, independent of the emitter metadata.
EXPECTED = {
 'header-as-slot-zero': 'tail_pool: call_error 4',
 'lost-child-pool': 'tail_pool: call_error 4',
 'wrong-self-root': 'tail_pool: call_error 4',
 'temporary-environment-overwrites-pool': 'tail_pool: call_error 4',
}
def run(evidence,out):
 out.mkdir(parents=True,exist_ok=False);base=generate();rows=[]
 (out/'compiler_controls.py').write_bytes(Path(__file__).read_bytes())
 for name in ('execute_compiled.py','execute_compiled.mjs'):(out/name).write_bytes((Path(__file__).parent/name).read_bytes())
 for name,(old,new) in MUTATIONS.items():
  if base.count(old)!=1:raise ValueError('mutation anchor '+name)
  dest=out/name;compile_run(evidence,dest,base.replace(old,new))
  try:execute_run(dest)
  except RuntimeError:
   log=(dest/'execution.log').read_text()
   if EXPECTED[name] not in log:raise ValueError('unexpected failure '+name+'; '+str(dest/'execution.log'))
   rows.append({'name':name,'compiled':True,'rejected':True,'expected':EXPECTED[name]})
  else:raise ValueError('escaped mutant '+name)
  (out/'controls.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('PASS:',len(rows),'recompiled compiler mutants rejected')
if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
