"""Run new CLOS recipes with the unchanged whole-file compiler and harness."""
from pathlib import Path
import importlib.util,subprocess,sys,shutil
HERE=Path(__file__).resolve().parent;PRIOR=HERE.parent/'bootstrap-lexpr-spread'
sys.path.insert(0,str(HERE));import backend
spec=importlib.util.spec_from_file_location('recipes_runner',HERE.parent/'bootstrap-recipes/run.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
parent.backend=backend;parent.HERE=PRIOR
fallback=parent.fixture
parent.fixture=lambda name: HERE/name if (HERE/name).is_file() else PRIOR/name if (PRIOR/name).is_file() else fallback(name)
copy=shutil.copy

def driver_copy(src,dest,*args,**kwargs):
 name=Path(dest).name
 if name in ('new-inputs.lisp','execute.lisp','observers.lisp'):src=HERE/name
 if name=='class-shapes.lisp':src=PRIOR/name
 result=copy(src,dest,*args,**kwargs)
 if name=='compile.lisp':
  for name in ('numeric-files.lisp','arch-probes.lisp','new-inputs.lisp','clos-inputs.lisp'):
   copy(HERE/name if (HERE/name).exists() else PRIOR/name,Path(dest).parent/name)
 return result
parent.shutil.copy=driver_copy
out=Path(sys.argv[1]).resolve()
parent.compile_corpus(out);parent.stable_reader_diagnostics(out)
subprocess.run([sys.executable,HERE/'execute.py',out],check=True)
subprocess.run([sys.executable,HERE/'summary.py',out],check=True)
