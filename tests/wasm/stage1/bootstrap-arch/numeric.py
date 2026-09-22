"""Execute actual whole-file numeric entries with the retained recipe runner."""
from pathlib import Path
import importlib.util,json,shutil,subprocess,sys
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
    result=copy(src,dest,*args,**kwargs)
    if Path(dest).name=='compile.lisp':
        for name in ('numeric-files.lisp','arch-probes.lisp'):copy(HERE/name,Path(dest).parent/name)
    return result
parent.shutil.copy=copy_driver
parent.compile_corpus(out)
parent.stable_reader_diagnostics(out)
subprocess.run([sys.executable,PARENT/'execute.py',out],check=True)

whole=json.loads((out/'compiled/whole-file.json').read_text())
native=json.loads((out/'compiled/native.json').read_text())
execution=json.loads((out/'execution.json').read_text())
numeric={r['name']:r for r in whole if r['name'] and r['status']=='ADMITTED' and r['file'].endswith(('l0-numbers.lisp','l0-float.lisp','l0-bignum32.lisp'))}
rows=[r for r in native if r['definition'] in numeric and r['name']==numeric[r['definition']]['module']]
originals={r['definition'] for r in native if not r.get('targetOnly') and not r['definition'].startswith('CORE-') and r['definition'] not in ('EQL','FULLTAG','LISPTAG','TYPECODE','ASSQ')}
non_nil={r['definition'] for r in native if r['definition'] in originals and not r.get('caught') and any(v is not None for v in r['values'])}
prior=json.loads((parent.EVIDENCE/'2026-09-21-stage1-bootstrap-recipes-r1/execution/execution-frontier.json').read_text())
previous=set(prior['names'])|{'MULTIPLY-FIXNUMS','UPGRADED-COMPLEX-PART-TYPE'}
assert previous<=originals
probes={name:sum(r['definition']==name for r in native) for name in sorted({r['definition'] for r in native if r['definition'].startswith('CORE-ARCH-')})}
assert set(probes)=={'CORE-ARCH-RATIO','CORE-ARCH-IDENTITY','CORE-ARCH-SYMBOL-IDENTITY','CORE-ARCH-DOUBLE','CORE-ARCH-SINGLE','CORE-ARCH-COPY-ORDER'}
assert {'MULTIPLY-FIXNUMS','UPGRADED-COMPLEX-PART-TYPE'}<={r['definition'] for r in rows}
parent.save(out/'numeric-execution.json',dict(status='PASS',original_definitions_executed=len(originals),non_nil_witness=len(non_nil),new_executions=sorted(originals-previous),arch_probe_cases=probes,arch_probe_comparisons=4*sum(probes.values()),unexecuted_probe='CORE-ARCH-STACK-SINGLE: initializing via the unchanged %SHORT-FLOAT definition is not dependency-closed',whole_file_numeric_definitions=sorted({r['definition'] for r in rows}),whole_file_numeric_cases=len(rows),whole_file_numeric_comparisons=4*len(rows),target_comparisons=sum(r['comparisons'] for r in execution['rows']),scope='Every numeric row names its actual whole-file module. Other corpus definitions retain their prior compilation provenance; the independent recount does not claim all prior executions used file environments. The new ratio mutation/allocation and fixnum float conversions execute whole-file. Full ratio arithmetic, bignum library arithmetic and initialized stack-float macro callers still have missing dependencies. The symbol-identity observer asserts architecture-specific answers rather than bit-identical macro results.'))
