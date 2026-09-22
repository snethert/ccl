"""Use the accepted per-file measuring instrument with the proposed backend."""
from pathlib import Path
import importlib.util,sys,json
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));import backend
spec=importlib.util.spec_from_file_location('file_recount',HERE.parent/'bootstrap-lexpr-spread/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.backend=backend
out=Path(sys.argv[1]).resolve();m.run(out)
p=out/'summary.json';s=json.loads(p.read_text())
# This process measures compilation only; the execution run supplies its own figures.
s.pop('original_definitions_executed_reused',None);s.pop('non_nil_witness_reused',None)
p.write_text(json.dumps(s,indent=2,sort_keys=True)+'\n')
