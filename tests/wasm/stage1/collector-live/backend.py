"""Keep tagged operands rooted and compute moving store addresses after RHS."""
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('live_core_backend',HERE.parent/'collector-core/backend.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
replace=prior.replace;base=prior.base

def generate():
 s=prior.generate()
 s=replace(s,EQ_OLD,EQ_NEW)
 s=replace(s,BIND_OLD,BIND_NEW)
 for old,new in CONDITION_FIXES:s=replace(s,old,new)
 return s

EQ_OLD='(b-wat "(if (result i32) (i32.eq ~a ~a) (then (i32.const 77838)) (else (i32.const 77825)))" (b-scalar (second args)) (b-scalar (third args)))'
EQ_NEW='''(b-wat "(block (result i32) ~a)" (b-frame 2 (lambda (root)
         (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a) (if (result i32) (i32.eq (i32.load offset=8 ~a) (i32.load offset=12 ~a)) (then (i32.const 77838)) (else (i32.const 77825)))"
           root (b-scalar (second args)) root (b-scalar (third args)) root root))))'''


BIND_OLD='(var (b-wat "(i32.store ~a ~a)" (b-variable-address var) value))'
BIND_NEW='''(var (if (b-captured-p var)
    (let ((staged (temporary)))
      ;; Evaluation may collect. The cell address must be read afterwards.
      ;; Address lookup itself has no call, allocation or poll.
      (b-wat "(local.set ~a ~a) (i32.store ~a (local.get ~a))"
        staged value (b-variable-address var) staged))
    (b-wat "(i32.store ~a ~a)" (b-variable-address var) value)))'''

# The implicit service's four result words can be overwritten by SIGNAL.
# Its existing 32-byte frame has two padding words; make them roots and keep
# the condition in the first, separate from those four result words.
CONDITION_FIXES=[
 ('(b-initialize-roots "(local.get $frame)" 4)', '(b-initialize-roots "(local.get $frame)" 6)'),
 ('(signal (b-signal (make-b-raw-code :text "(local.get $condition)") nil))', '(signal (b-signal (make-b-raw-code :text "(i32.load offset=24 (local.get $frame))") nil))'),
 ('(debugger (b-debugger "(local.get $condition)"))', '(debugger (b-debugger "(i32.load offset=24 (local.get $frame))"))'),
 ('(i32.store (local.get $results) (local.get $condition))', '(i32.store (local.get $results) (local.get $condition)) (i32.store offset=24 (local.get $frame) (local.get $condition))'),
]
