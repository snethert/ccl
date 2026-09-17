"""One-site omissions in producer ownership, storage and continuation publication."""
from pathlib import Path
import importlib.util

def mutations(source):
 result={}
 def change(name,fn,old,new):
  a=source.index('(defun '+fn+' ');b=source.find('\n(defun ',a+1)
  if b<0:b=len(source)
  part=source[a:b];assert part.count(old)==1,(name,part.count(old));result[name]=source[:a]+part.replace(old,new)+source[b:]
 change('producer-parent-budget','b-producer','(local.set $dynamic_results (i32.const 1))','(local.set $dynamic_results (i32.const 0))')
 change('literal-callable-heap','b-multiple-call','(*b-stack-closure* literal)','(*b-stack-closure* nil)')
 change('mvc-reverse-producers','b-multiple-call','(dolist (code codes)','(dolist (code (reverse codes))')
 change('mvc-destination-offset','b-multiple-call','" target context n target target)','" target context slots target target)')
 change('mvc-drop-values','b-multiple-call','(memory.copy (i32.load offset=8 (local.get ~a)) (local.get ~a) (i32.mul (local.get $count) (i32.const 4)))','(memory.copy (i32.load offset=8 (local.get ~a)) (local.get ~a) (i32.const 0))')
 change('mvc-drop-accumulation','b-multiple-call','(local.set ~a (i32.add (local.get ~a) (local.get $count))) (local.set ~a','(local.set ~a (i32.add (i32.and (local.get ~a) (i32.const 0)) (local.get $count))) (local.set ~a')
 change('mvc-short-root-range','b-multiple-call','(i32.store offset=36 (local.get ~a) (i32.add (i32.const 2) (local.get ~a)))','(i32.store offset=36 (local.get ~a) (i32.add (i32.const 0) (local.get ~a)))')
 change('mvc-count-padding','b-multiple-call','(b-internal-dispatch (b-local context) (b-local n))','(b-internal-dispatch (b-local context) (b-local slots))')
 change('mvc-no-tail','b-multiple-call','(if *b-tail-position*\n        (progn','(if nil\n        (progn')
 change('literal-no-tail-relocation','b-multiple-call','(b-local n) ephemeral-bytes)','(b-local n) 0)')
 change('retained-double-scanner','b-save-control','(i32.store offset=12 (local.get $result_descriptor) (i32.const 0))','(i32.store offset=12 (local.get $result_descriptor) (local.get $count))')
 change('retained-empty-results','b-load-control','(b-control-values record) record record','"(i32.const 0)" record record')
 change('result-cursor-leak','b-result-runtime','(i32.store offset=76 (global.get $tcr) (local.get $keep))','(i32.store offset=76 (global.get $tcr) (local.get $end))')
 change('result-lost-owner','b-result-runtime','(i32.store (i32.sub (local.get $src) (i32.const 12)) (i32.load offset=16 (local.get $d)))','(i32.store (i32.sub (local.get $src) (i32.const 12)) (i32.const 0))')
 change('mvb-zero-pad','b-multiple-bind','(else (i32.const 77825))','(else (i32.const 0))')
 change('mvb-inclusive-count','b-multiple-bind','(i32.gt_u (local.get $count)','(i32.ge_u (local.get $count)')
 # Semantics unchanged: copying into an intermediate caller-owned buffer is a
 # performance regression. Only the executed-copy oracle is expected to reject it.
 old=''' (local.set $dst (i32.load offset=8 (local.get $d)))
 (if (i32.and (i32.ne (local.get $dst) (i32.add (local.get $d) (i32.const 32)))'''
 new=''' (local.set $dst (call $rv_ensure (local.get $d) (local.get $n)))
 (memory.copy (local.get $dst) (local.get $src) (i32.mul (local.get $n) (i32.const 4))) (return (local.get $dst))
 (local.set $dst (i32.load offset=8 (local.get $d)))
 (if (i32.and (i32.ne (local.get $dst) (i32.add (local.get $d) (i32.const 32)))'''
 change('intermediate-result-copy','b-result-runtime',old,new)
 change('inline-result-arena','b-result-runtime','(then (return (local.get $old))))','(then (drop (call $rv_alloc (local.get $n) (i32.load offset=16 (local.get $d)))) (return (local.get $old))))')
 change('direct-handoff-live-retired-roots','b-result-runtime','(i32.store offset=128 (global.get $tcr) (i32.load offset=24 (local.get $d)))','(nop)')
 return result

def source_regression(source):
 old=(Path(__file__).parent/'rejected-normalizer.lisp').read_text();a=source.index('(defun b-normalize-literal-apply');b=source.index('\n;;; One continuation',a)
 return source[:a]+old+source[b:]
