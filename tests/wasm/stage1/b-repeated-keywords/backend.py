"""Small proposal over the accepted LL10 compiler; shared sources stay unchanged."""
import hashlib, importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'constants/compiler.py'
spec=importlib.util.spec_from_file_location('accepted_constants_compiler',BASE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

def replace(s,old,new):
    if s.count(old)!=1:raise ValueError('compiler anchor: '+old)
    return s.replace(old,new)

def generate():
    s=base.generate()
    # Lambda variables must still be distinct. Keyword names need not be:
    # U1 binds only the first formal for a supplied name; later aliases default.
    s=replace(s,'(and (keywordp key) (not (member key keys)))','(keywordp key)')
    s=replace(s,'(loop for var in vars for sp in supplied for name across names do',
      '''(loop for var in vars for sp in supplied for name across names
                for index from 0
                when (= index (position name names :test #'eq)) do''')
    return s
