"""Opt-in callable metadata in existing function-object fields and pools."""
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('metadata_prior',HERE.parent/'closure-transfers/backend.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
replace=prior.replace;base=prior.base

def generate():
 s=prior.generate()
 s=replace(s,'(defvar *pool-layouts* nil)', '(defvar *b-callable-metadata* nil)\n(defvar *pool-layouts* nil)')
 s=replace(s,'    (pool-plan)\n    (b-plan-local-environments)', '    (when *b-callable-metadata* (b-plan-local-environments))\n    (pool-plan)\n    (unless *b-callable-metadata* (b-plan-local-environments))')
 s=replace(s,'(let ((values nil) (children nil))', '(let ((values (when *b-callable-metadata* (list (metadata-arity (first entry)) (metadata-debug (first entry))))) (children nil))')
 # Fill existing payload slots; function object remains six node words, 32 bytes.
 old='(i32.store offset=16 ~a (i32.const 77825)) (i32.store offset=20 ~a (i32.const 77825))"\n            base base (second entry) base (if (zerop n) "(i32.const 77825)" (b-at base 38)) base base base)'
 new='(i32.store offset=16 ~a ~a) (i32.store offset=20 ~a ~a)"\n            base base (second entry) base (if (zerop n) "(i32.const 77825)" (b-at base 38)) base base (metadata-child-load afunc 0) base (metadata-child-load afunc 1))'
 s=replace(s,old,new)
 # A host entry must validate the full function and metadata before executing.
 s=replace(s,'(let ((prepare (concatenate \'string (or (b-environment-entry) "") (b-initialize-cells)))', '(let ((prepare (concatenate \'string (metadata-entry afunc) (or (b-environment-entry) "") (b-initialize-cells)))')
 return s+'\n'+(HERE/'metadata.lisp').read_text()
