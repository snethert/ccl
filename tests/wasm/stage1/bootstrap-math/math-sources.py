"""Target branches at native libm entry definitions, never consumer rewriting."""
import importlib.util,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('foreign_inventory',HERE.parent/'bootstrap-admission/foreign.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
OPERATIONS=('expt','sin','cos','acos','asin','cosh','log','tan','atan','atan2','exp','sinh','tanh')

def derive():
    text=(ROOT/'level-1/l1-numbers.lisp').read_text();masked=m.mask(text)
    names={f'%{width}-float-{op}!' for width in ('double','single') for op in OPERATIONS}
    positions=[match.start() for match in re.finditer(r'\(defun\s+([^\s()]+)',masked,re.I) if match[1].lower() in names]
    for pos in reversed(positions):text=text[:pos]+'#-wasm32-target\n'+text[pos:]
    for i,op in enumerate(OPERATIONS):
        binary=op in ('expt','atan2');args='x y result' if binary else 'x result'
        for single,width in enumerate(('double','single')):
            text+=f'''\n#+wasm32-target
(defun %{width}-float-{op}! ({args})
  (declare ({width}-float {args}))
  (%wasm-float-store result (%wasm-float-transcend {12+2*i+single} x {'y' if binary else '0'})))
'''
    return text
