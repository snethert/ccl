"""Close common bootstrap calls using existing arithmetic, predicates and errors."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('division_backend',HERE.parent/'bootstrap-division/backend.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
source_files=parent.source_files;proposal=parent.proposal;runtime_files=parent.runtime_files

def generate():
    s=parent.generate()
    old='(defun bootstrap-numeric-call (name forms)\n'
    assert s.count(old)==1
    s=s.replace(old,old+'  (let ((code (bootstrap-dependency-call name forms)))\n    (when code (return-from bootstrap-numeric-call code)))\n')
    old='(defun bootstrap-operator (ir)\n'
    assert s.count(old)==1
    s=s.replace(old,old+'  (let ((code (bootstrap-dependency-operator ir)))\n    (when code (return-from bootstrap-operator code)))\n')
    return s+'\n'+(HERE/'dependencies.lisp').read_text()
