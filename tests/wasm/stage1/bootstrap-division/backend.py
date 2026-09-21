"""Add exact integer division using the accepted integer quotient/remainder path."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
PARENT=HERE.parent/'bootstrap-execution'
spec=importlib.util.spec_from_file_location('execution_backend',PARENT/'backend.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
source_files=parent.source_files
proposal=parent.proposal
runtime_files=parent.runtime_files

def generate():
    s=parent.generate()
    old='(defun b-restart-symbol (symbol)\n'
    assert s.count(old)==1
    s=s.replace(old,old+'  (when *bootstrap-front-end*\n    (return-from b-restart-symbol (bootstrap-symbol symbol)))\n')
    start=s.index('(defun b-float-call ');end=s.index('(defun b-float-runtime ',start)
    part=s[start:end]
    old='(if (< op 3)'
    assert part.count(old)==1
    part=part.replace(old,'(if (or (< op 3) (and *bootstrap-front-end* (= op 3)))')
    old="(b-integer-call (nth op '(%integer-add %integer-sub %integer-mul)) (list (make-b-raw-code :text a) (make-b-raw-code :text b)))"
    assert part.count(old)==1
    part=part.replace(old,"(if (= op 3) (bootstrap-integer-division root) "+old+")")
    s=s[:start]+part+s[end:]
    old='(format s "(if (i32.and (call $condition_mask ~a) (i32.shr_u (i32.load offset=4 (call $handler_cons ~a)) (i32.const 2))) (then" condition handlers)'
    assert s.count(old)==1
    s=s.replace(old,'''(write-string
                      (b-wat "(if (i32.and (call $condition_mask ~a) ~a) (then"
                        condition
                        (if *bootstrap-front-end*
                          (bootstrap-handler-mask
                           (b-wat "(i32.load offset=4 (call $handler_cons ~a))" handlers))
                          (b-wat "(i32.shr_u (i32.load offset=4 (call $handler_cons ~a)) (i32.const 2))" handlers))) s)''')
    return s+'\n'+(HERE/'division.lisp').read_text()
