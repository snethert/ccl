"""Opt-in owner retry before fixed heap construction and rest-list publication."""
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('retry_live_backend',HERE.parent/'collector-live/backend.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
replace=prior.replace;base=prior.base
RUNTIME='''(func $heap_ensure (param $bytes i32)
 (local $p i32) (local $limit i32)
 (local.set $p (i32.load offset=48 (global.get $tcr)))
 (local.set $limit (i32.load offset=52 (global.get $tcr)))
 (if (i32.or (i32.eqz (local.get $bytes)) (i32.and (local.get $bytes) (i32.const 7))) (then (throw $call_error (i32.const 6))))
 (if (i32.or (i32.and (local.get $p) (i32.const 7)) (i32.or (i32.lt_u (local.get $p) (i32.load offset=56 (global.get $tcr))) (i32.gt_u (local.get $p) (local.get $limit)))) (then (throw $call_error (i32.const 6))))
 (if (i64.gt_u (i64.extend_i32_u (local.get $limit)) (i64.shl (i64.extend_i32_u (memory.size)) (i64.const 16))) (then (throw $call_error (i32.const 6))))
 (if (i64.gt_u (i64.add (i64.extend_i32_u (local.get $p)) (i64.extend_i32_u (local.get $bytes))) (i64.extend_i32_u (local.get $limit)))
  (then (call $owner_ensure (local.get $bytes)))))'''
def generate():
 s=prior.generate()
 s=replace(s,'(defvar *b-call-links* nil)','(defvar *b-call-links* nil)\n(defvar *b-allocation-retry* nil)')
 s=replace(s,'(dolist (name (sort *b-keywords*', '(when *b-allocation-retry* (write-string "(import \\"owner\\" \\"ensure\\" (func $owner_ensure (param i32)))" s))\n             (dolist (name (sort *b-keywords*'.replace('\\"','\\"'))
 s=replace(s,'(write-string (b-object-runtime) s)', '(when *b-allocation-retry* (write-string (b-allocation-runtime) s))\n             (write-string (b-object-runtime) s)')
 a=s.index('(defun b-heap-block ');b=s.index('(defun b-initialize-cells',a)
 original=s[a:b]
 changed=original.replace('(b-wat "(block (result i32) (local.set ~a ~a) ~a ~a ~a ~a ~a (local.get ~a))"','(b-wat "(block (result i32) ~a(local.set ~a ~a) ~a ~a ~a ~a ~a (local.get ~a))"\n      (if *b-allocation-retry* (b-wat "(if (i64.gt_u (i64.add (i64.extend_i32_u (i32.load offset=48 (global.get $tcr))) (i64.const ~d)) (i64.extend_i32_u (i32.load offset=52 (global.get $tcr)))) (then (call $heap_ensure (i32.const ~d)))) " bytes bytes) "")')
 assert changed!=original;s=s[:a]+changed+s[b:]
 old='(format s "(if (local.get ~a) (then (local.set ~a ~a)" n cursor (b-load wasm32::tcr.alloc_pointer))'
 new='''(format s "(if (local.get ~a) (then " n)
      (when *b-allocation-retry*
        (write-string (b-condition (b-wat "(i64.gt_u (i64.mul (i64.extend_i32_u (local.get ~a)) (i64.const 8)) (i64.const 4294967295))" n) 6) s)
        (format s "(if (i64.gt_u (i64.add (i64.extend_i32_u (i32.load offset=48 (global.get $tcr))) (i64.mul (i64.extend_i32_u (local.get ~a)) (i64.const 8))) (i64.extend_i32_u (i32.load offset=52 (global.get $tcr)))) (then (call $heap_ensure (i32.mul (local.get ~a) (i32.const 8)))))" n n))
      (format s "(local.set ~a ~a)" cursor (b-load wasm32::tcr.alloc_pointer))'''
 s=replace(s,old,new)
 # Default mode is deliberately byte-identical, including whitespace.
 s+='\n(in-package :wasm32-compiler)\n(defun b-allocation-runtime () '+ '"'+RUNTIME.replace('"','\\"')+'")\n'
 s+='''(defun compile-retrying-call-module (source-text name links)
 (let ((*b-allocation-retry* t)) (compile-call-module source-text name links)))
(defun compile-retrying-call-form (form name links)
 (let ((*b-allocation-retry* t)) (compile-call-form form name links)))
'''
 return s
if __name__=='__main__':print(generate())
