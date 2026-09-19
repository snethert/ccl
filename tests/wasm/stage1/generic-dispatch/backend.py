"""Isolated empty-dispatch condition extension of the accepted compiler."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE='a303b8658339e4858e41121ed55af4c86b4471354a0c37d3db7befbaec3d30be'
def replace(s,a,b,n=1):
 assert s.count(a)==n,(a,s.count(a),n)
 return s.replace(a,b)
def generate():
 s=(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text();assert hashlib.sha256(s.encode()).hexdigest()==BASE
 s=replace(s,'(storage-condition . 4096)','(storage-condition . 4096) (ccl::no-applicable-method-exists . 8192)')
 s=replace(s,'unbound-variable storage-condition)','unbound-variable storage-condition ccl::no-applicable-method-exists)',2)
 # The trusted owner may supply either the accepted twelve-row registry or
 # that registry plus NO-APPLICABLE-METHOD-EXISTS. Both are bounded and checked.
 a='(local.set $table (call $object_base (global.get $symbol_condition_registry) (i32.const 4) (i32.const 3322)))\n (call $span (local.get $table) (i32.const 52))'
 b='''(local.set $table (i32.sub (global.get $symbol_condition_registry) (i32.const 6)))
 (if (i32.ne (i32.and (global.get $symbol_condition_registry) (i32.const 7)) (i32.const 6)) (then (throw $call_error (i32.const 5))))
 (call $span (local.get $table) (i32.const 4))
 (local.set $n (i32.shr_u (i32.load (local.get $table)) (i32.const 8)))
 (if (i32.or (i32.ne (i32.and (i32.load (local.get $table)) (i32.const 255)) (i32.const 250)) (i32.and (i32.ne (local.get $n) (i32.const 12)) (i32.ne (local.get $n) (i32.const 13)))) (then (throw $call_error (i32.const 5))))
 (call $span (local.get $table) (i32.mul (i32.add (local.get $n) (i32.const 1)) (i32.const 4)))'''
 s=replace(s,a,b,2);s=replace(s,'(i32.ge_u (local.get $i) (i32.const 12))','(i32.ge_u (local.get $i) (local.get $n))',2)
 a='(if (i32.eq (local.get $mask) (i32.const 156)) (then (i32.store offset=12 (local.get $slots) (local.get $expected))))'
 s=replace(s,a,a+'''\n (if (i32.eq (local.get $mask) (i32.const 32796)) (then (i32.store offset=8 (local.get $slots) (local.get $datum)) (i32.store offset=12 (local.get $slots) (local.get $expected))))''',2)
 # Privately named runtime calls are admitted only when supplied as corpus
 # definitions; intercept their real IR rather than executing host code.
 anchor='''      (ccl::call
       (when'''
 s=replace(s,anchor,'''      (ccl::call
       (when (and (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
                  (member (first (ccl::acode-operands (first args))) '(gd_condition gd_condition_gf gd_condition_args)))
         (unless (and (null (third args)) (null (second (second args)))) (refuse :gd-constructor-spread))
         (return-from b-multiple (gd-condition-call (first (ccl::acode-operands (first args))) (first (second args)))))
       (when''')
 s+='\n'+(HERE/'condition.lisp').read_text()
 return s
