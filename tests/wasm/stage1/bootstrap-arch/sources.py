"""Retire native foreign-pointer implementations, not portable interfaces."""
import importlib.util, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'bootstrap-admission'))
spec=importlib.util.spec_from_file_location('arch_source_parser',HERE.parent/'bootstrap-admission/sources.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)

EXCLUDED={
    'level-1/l1-utils.lisp': ['%set-composite-pointer-ref'],
    'level-1/l1-aprims.lisp': ['%new-gcable-ptr'],
}
FILES=tuple(dict.fromkeys((*parser.FILES,*EXCLUDED)))

def derive():
    result={}
    for name,symbols in EXCLUDED.items():
        text=(ROOT/name).read_text()
        rows=[r for r in parser.definitions(text) if r[3].lower() in symbols]
        assert len(rows)==len(symbols)
        for start,end,kind,symbol in reversed(rows):
            assert kind.lower()=='defun'
            text=text[:start]+'#-wasm32-target\n'+text[start:]
        result[name]=text
    return result
