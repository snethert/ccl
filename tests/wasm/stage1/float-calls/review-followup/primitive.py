"""Separate Lisp coercion entry; preserve the mathematical primitive entry."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def source():
 s=(ROOT/'runtime/wasm32/float.c').read_text()
 s=replace(s,'EXPORT U float_calculate(U op,U av,U bv,U in,U end,U out,U limit,U result,U mask,U safe){','static U calculate(U op,U av,U bv,U in,U end,U out,U limit,U result,U mask,U safe,U native){')
 # Native x8664 U1 constructs bignum float bits in Lisp without FPU flags.
 # Its signed fixnums have 60 magnitude bits. A negative magnitude of exactly
 # 2^60 is a fixnum too, but its exact conversion has no flag in either path.
 for v,f in [('a','fa'),('b','fb')]:
  s=replace(s,f'{f}=safe?flags(status):0;',f'{f}=safe&&!(native&&!{v}.kind&&length(&{v}.i)>60)?flags(status):0;')
 for name,mode in [('float_calculate',0),('float_calculate_lisp',1)]:
  s+=f'\nEXPORT U {name}(U op,U av,U bv,U in,U end,U out,U limit,U result,U mask,U safe){{return calculate(op,av,bv,in,end,out,limit,result,mask,safe,{mode});}}\n'
 return s

def owner():
 return replace((ROOT/'runtime/wasm32/float-service.mjs').read_text(),'wasm.float_calculate(op,','wasm.float_calculate_lisp(op,')
