"""Collector prerequisite: retiring a binding must never grow its vector."""
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('collector_ll17_backend',HERE.parent/'binding-vector/backend.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
replace=prior.replace
base=prior.base

def generate():
 s=prior.generate()
 s=replace(s,'(func $special_location', '''(func $existing_dynamic_slot (param $symbol i32) (result i32) (local $index i32) (local $base i32) (local $cap i32)
 (local.set $index (call $binding_index (local.get $symbol)))
 (local.set $base (i32.load offset=104 (global.get $tcr))) (local.set $cap (i32.load offset=108 (global.get $tcr)))
 (call $binding_vector_check (local.get $base) (local.get $cap))
 (if (i32.or (i32.eqz (local.get $index)) (i32.ge_u (local.get $index) (local.get $cap))) (then (throw $call_error (i32.const 11))))
 (i32.add (local.get $base) (i32.mul (local.get $index) (i32.const 4))))
(func $special_location''')
 s=replace(s,'(b-wat "(i32.load offset=~d (local.get $closure_env))" (+ 4 (* 4 n)))', '(b-wat "(i32.load offset=~d (i32.sub (i32.load offset=2 (i32.load offset=40 (local.get $context))) (i32.const 6)))" (+ 4 (* 4 n)))')
 s=replace(s,'(let ((self (if (eq op \'b-self) "(local.get $self)"', '(let ((self (if (eq op \'b-self) "(i32.load offset=40 (local.get $context))"')
 return replace(s,'(local.set $slot (call $dynamic_slot (i32.load offset=16 (local.get $p))))','(local.set $slot (call $existing_dynamic_slot (i32.load offset=16 (local.get $p))))')
