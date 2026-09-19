"""Use the accepted disposable U1 compiler driver, with this corpus and exporter."""
import importlib.util,shutil,sys
from pathlib import Path
from backend import generate,ROOT
HERE=Path(__file__).resolve().parent;CONSTANTS=HERE.parent/'constants'
def run(e,out,code=None):
 # A private driver directory supplies its own corpus and exact source inputs.
 h=out.parent/(out.name+'-driver');shutil.copytree(CONSTANTS,h,ignore=shutil.ignore_patterns('__pycache__','development','review-followup'))
 shutil.copy(HERE/'compile.lisp',h/'compile.lisp')
 p=h/'compile.py';s=p.read_text().replace('ROOT=HERE.parents[3];REG=HERE.parent/\'registration\'', 'ROOT=Path('+repr(str(ROOT))+');REG=Path('+repr(str(HERE.parent/'registration'))+')');p.write_text(s)
 oldpath=sys.path.copy();sys.path.insert(0,str(h))
 spec=importlib.util.spec_from_file_location('metadata_compile',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 try:m.run(e,out,generate() if code is None else code)
 finally:sys.path[:]=oldpath
if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
