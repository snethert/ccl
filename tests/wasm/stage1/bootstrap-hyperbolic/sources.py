"""Native bodies stay intact behind the target reader conditional."""
from pathlib import Path
import importlib.util,re
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('hyperbolic_source_parent',HERE.parent/'bootstrap-arch/sources.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
FILES=parent.FILES
OPERATIONS=('asinh','acosh','atanh')

def derive():
    text=(ROOT/'level-1/l1-numbers.lisp').read_text()
    for op in OPERATIONS:
        old=f'#-windows-target\n(progn\n(defun %double-float-{op}!'
        assert text.count(old)==1
        text=text.replace(old,old.replace('#-windows-target', '#-(or windows-target wasm32-target)'))
    for i,op in enumerate(OPERATIONS):
        for single,width in enumerate(('double','single')):
            text+=f'''\n#+wasm32-target
(defun %{width}-float-{op}! (x result)
  (declare ({width}-float x result))
  (%wasm-float-store result (%wasm-float-transcend {38+2*i+single} x 0)))
'''
    return {'level-1/l1-numbers.lisp':text}
