"""Execute actual whole-file numeric entries with the retained recipe runner."""
from pathlib import Path
import importlib.util,json,shutil,subprocess,sys,tarfile,hashlib
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'bootstrap-recipes'
sys.path.insert(0,str(HERE))
import backend
spec=importlib.util.spec_from_file_location('numeric_parent',PARENT/'run.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
parent.backend=backend
out=Path(sys.argv[1]).resolve()
prior=parent.fixture
parent.fixture=lambda name: HERE/name if (HERE/name).is_file() else prior(name)
# Copy the additional file alongside the ordinary driver support files.
copy=parent.shutil.copy
def copy_driver(src,dest,*args,**kwargs):
    if Path(dest).name=='class-shapes.lisp':src=HERE/'class-shapes.lisp'
    result=copy(src,dest,*args,**kwargs)
    if Path(dest).name=='compile.lisp':
        for name in ('numeric-files.lisp','arch-probes.lisp','new-inputs.lisp'):copy(HERE/name,Path(dest).parent/name)
    return result
parent.shutil.copy=copy_driver
parent.HERE=HERE
parent.compile_corpus(out)
parent.stable_reader_diagnostics(out)
subprocess.run([sys.executable,HERE/'class-proof.py',out],check=True)
subprocess.run([sys.executable,HERE/'execute.py',out],check=True)

subprocess.run([sys.executable,HERE/'summary.py',out],check=True)

import readers
readers.replay(parent.EVIDENCE,out/'compiled/proposal/files',out/'readers')

packet=parent.EVIDENCE/'2026-09-22-stage1-bootstrap-condition-frontier-r1'
with tarfile.open(packet/'artifacts.tar.gz') as archive:
    data=archive.extractfile('numeric/condition-controls.json').read()
assert hashlib.sha256(data).hexdigest()==json.loads((packet/'deterministic.json').read_text())['numeric/condition-controls.json']
(out/'condition-controls.json').write_bytes(data)
