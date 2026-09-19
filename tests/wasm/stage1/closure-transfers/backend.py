"""Closed lexical transfers and conservative ordinary-branch TAGBODY lowering."""
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('closure_transfers_prior',HERE.parent/'temporaries/backend.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
replace=prior.replace;base=prior.base

def generate():
 s=prior.generate()
 a=s.index('(lambda-form (parts outer depth)');b=prior.prior.end_form(s,a)
 old=s[a:b]
 head='(lambda-form (parts outer depth) (let ((saved-tags tags)) (unwind-protect (progn (setq tags nil) '
 assert old.startswith(head) and old.endswith(') (setq tags saved-tags))))')
 s=s[:a]+'(lambda-form (parts outer depth)'+old[len(head):-len(') (setq tags saved-tags))))')]+')'+s[b:]
 s=replace(s,'(defun b-tagbody (tags forms)','(defun b-unwinding-tagbody (tags forms)')
 s=replace(s,'         (record (fourth entry)))\n    (concatenate', '''         (record (fourth entry)))
    (when (fifth entry)
      (return-from b-go
        (b-wat "(local.set ~a (i32.const ~d)) (br ~a)"
          (second entry) (third entry) (fifth entry))))
    (concatenate''')
 return s+'\n'+(HERE/'branches.lisp').read_text()
