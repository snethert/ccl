"""LL19 prerequisite: semantic APPLY list failures signal before unwinding."""
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
p=HERE.parent/'b-repeated-keywords/backend.py'
spec=importlib.util.spec_from_file_location('accepted_keywords',p)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
replace=base.replace

def generate():
    s=base.generate()
    old='''(b-condition (b-wat "(i32.ne (i32.and ~a (i32.const ~d)) (i32.const ~d))" node wasm32::fulltagmask wasm32::fulltag-cons) 5)'''
    new='''(b-wat "(if (i32.ne (i32.and ~a (i32.const ~d)) (i32.const ~d)) (then (call $implicit_error (i32.const 5) (local.get $top)) unreachable))" node wasm32::fulltagmask wasm32::fulltag-cons)'''
    # Only a semantic non-cons tail enters Lisp. Corrupt address, cyclic-list,
    # resource and runtime-metadata checks retain their existing fatal paths.
    return replace(s,old,new)
