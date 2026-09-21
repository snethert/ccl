from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def replace(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def adapter():
 s=(ROOT/'tests/wasm/stage1/hash-tables/adapter.wat').read_text()
 return replace(s,'(local.set $n (if (result i32) (i32.eqz (global.get $op)) (then (i32.const 2)) (else (i32.const 1))))','(local.set $n (i32.const 1))')
def generated():
 s=(ROOT/'tests/wasm/stage1/hash-tables/generated.mjs').read_text()
 s=s.replace('service.ht_run','service.pop_run').replace('op===0?2:1','1')
 return s
