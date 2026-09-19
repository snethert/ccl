"""PROG2 admission and local TAGBODY/GO over the reviewed exit protocol."""
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('temporaries_prior',HERE.parent/'constructor-retry/backend.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
replace=prior.replace;base=prior.base

def generate():
 s=prior.generate()
 s=replace(s,'(local-names nil) (blocks nil))','(local-names nil) (blocks nil) (tags nil))')
 s=replace(s,'                          (block\n','''                          (tagbody
                           (let ((new nil) (saved tags))
                             (dolist (part (cdr xs))
                               (when (atom part)
                                 (unless (or (symbolp part) (integerp part)) (refuse :b-tag-source))
                                 (when (member part new :test #'eql) (refuse :b-tag-source))
                                 (push part new)))
                             (unwind-protect
                               (progn (setq tags (append new tags))
                                 (dolist (part (cdr xs)) (when (consp part) (walk part vars (1+ depth)))))
                               (setq tags saved))))
                          (go (unless (and (= n 1) (member (second xs) tags :test #'eql)) (refuse :b-go-source)))
                          (block
''')
 # A GO in an inner function is outside this admission; native closed transfers
 # are deliberately not inferred from a same-function tag map.
 a=s.index('(lambda-form (parts outer depth)');b=prior.end_form(s,a);h=prior.end_form(s,s.index('(',a+1))
 s=s[:h]+' (let ((saved-tags tags)) (unwind-protect (progn (setq tags nil) '+s[h:b-1]+') (setq tags saved-tags))))'+s[b:]
 s=replace(s,"(and (member head '(prog1 multiple-value-prog1 unwind-protect catch)) (<= 1 n))", "(and (eq head 'prog2) (<= 2 n)) (and (member head '(prog1 multiple-value-prog1 unwind-protect catch)) (<= 1 n))")
 s=replace(s,'(defvar *b-blocks* nil)','(defvar *b-local-tags* nil)\n(defvar *b-blocks* nil)')
 s=replace(s,'           (*b-blocks* nil)','           (*b-blocks* nil) (*b-local-tags* nil)')
 # Add both to scalar delegation, but never to the leaf scratch proof.
 s=replace(s,'ccl::local-block ccl::local-return-from ccl::multiple-value-call','ccl::local-block ccl::local-return-from ccl::local-tagbody ccl::local-go ccl::multiple-value-call')
 s=replace(s,'      (ccl::local-block (b-local-block (first args) (second args)))', '''      (ccl::local-tagbody (b-tagbody (first args) (second args)))
      (ccl::local-go (b-go (first args)))
      (ccl::local-block (b-local-block (first args) (second args)))''')
 s=s.replace(';;; This slice has no loop IR, collection or poll during allocation/publication.',';;; Allocation/publication after assurance contains no calls or polls.')
 return s+'\n'+(HERE/'loops.lisp').read_text()
