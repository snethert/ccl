"""Derive the execution proposal without changing the reviewed library fixture."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
PARENT=HERE.parent/'bootstrap-library'
spec=importlib.util.spec_from_file_location('library_backend',PARENT/'backend.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
source_files=parent.source_files
proposal=parent.proposal
runtime_files=parent.runtime_files

def generate():
    s=parent.generate()
    def definition(name):
        start=s.index('(defun '+name+' ')
        end=s.find('\n(defun ',start+1)
        return s[start:] if end<0 else s[start:end]
    operator=definition('library-prior-operator').replace('library-prior-operator','bootstrap-operator')
    operator=operator.replace('(case op\n','(case op\n'+(HERE/'operator-clauses.lisp').read_text(),1)
    numeric=definition('library-prior-call').replace('library-prior-call','bootstrap-numeric-call')
    numeric=numeric.replace('(cond (','(cond '+(HERE/'call-clauses.lisp').read_text()+'\n          (',1)
    for name in ['library-prior-operator','library-prior-call','library-condition-call','bootstrap-operator','bootstrap-numeric-call']:
        s=s.replace(definition(name),'')
    s += '\n'+operator+'\n'+numeric+'\n'+(HERE/'helpers.lisp').read_text()
    old='(object (first values)) (value (and storep (second values)))\n                 (index (if storep (third values) (second values)))'
    assert s.count(old)==1
    s=s.replace(old,'(object (first values)) (index (second values))\n                 (value (and storep (third values)))')
    old="(direct (and (symbolp name) (or *bootstrap-front-end* (assoc name *b-call-links* :test #'eq))))"
    assert s.count(old)==4
    s=s.replace(old,"(direct (and (eq op 'ccl::immediate) (symbolp name)\n                      (or *bootstrap-front-end* (assoc name *b-call-links* :test #'eq))))")
    for name, arguments in [('b-apply', 'callee argument-list &optional local-self (ephemeral-bytes 0)'),
                            ('b-internal-apply', 'callee argument-list local-self')]:
        old='(defun '+name+' ('+arguments+')'
        assert s.count(old)==1
        s=s.replace(old,old+"\n  (when (and *bootstrap-front-end* (not local-self)\n             (not (eq (ccl::acode-operator-name (ccl::acode-operator callee)) 'ccl::immediate)))\n    (setq *bootstrap-dynamic-call* t))")
    assert 'library-prior-' not in s
    return s
