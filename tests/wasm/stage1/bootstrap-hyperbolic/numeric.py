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
parent.HERE=HERE
parent.compile_corpus(out)
parent.stable_reader_diagnostics(out)
subprocess.run([sys.executable,HERE/'execute.py',out],check=True)
subprocess.run(['/usr/local/bin/node',HERE/'math-check.mjs',out,out/'math-raw.json'],check=True)
subprocess.run(['/usr/local/bin/node',HERE.parent/'float-core/execute.mjs',out/'float.wasm',out/'detector.wasm',parent.EVIDENCE/'2026-09-19-stage1-float-core-r2/execution/cases.json',out/'raw-regression.json'],check=True)
subprocess.run([sys.executable,HERE/'faults.py',out],check=True)

whole=json.loads((out/'compiled/whole-file.json').read_text())
native=json.loads((out/'compiled/native.json').read_text())
execution=json.loads((out/'execution.json').read_text())
numeric={r['name']:r for r in whole if r['name'] and r['status']=='ADMITTED' and r['file'].endswith(('l0-numbers.lisp','l0-float.lisp','l0-bignum32.lisp','l1-numbers.lisp'))}
rows=[r for r in native if r['definition'] in numeric and r['name']==numeric[r['definition']]['module']]
originals={r['definition'] for r in native if not r.get('targetOnly') and not r['definition'].startswith('CORE-') and r['definition'] not in ('EQL','FULLTAG','LISPTAG','TYPECODE','ASSQ')}
non_nil={r['definition'] for r in native if r['definition'] in originals and not r.get('caught') and any(v is not None for v in r['values'])}
prior=json.loads((parent.EVIDENCE/'2026-09-21-stage1-bootstrap-recipes-r1/execution/execution-frontier.json').read_text())
previous=set(prior['names'])|{'MULTIPLY-FIXNUMS','UPGRADED-COMPLEX-PART-TYPE','%FIXNUM-DFLOAT','%FIXNUM-SFLOAT','%MAYBE-MAKE-RATIO'}
assert previous<=originals
probes={name:sum(r['definition']==name for r in native) for name in sorted({r['definition'] for r in native if r['definition'].startswith('CORE-ARCH-')})}
assert set(probes)=={'CORE-ARCH-RATIO','CORE-ARCH-IDENTITY','CORE-ARCH-SYMBOL-IDENTITY','CORE-ARCH-DOUBLE','CORE-ARCH-SINGLE','CORE-ARCH-COPY-ORDER'}
assert {'MULTIPLY-FIXNUMS','UPGRADED-COMPLEX-PART-TYPE'}<={r['definition'] for r in rows}
hyperbolic=[r for row in execution['rows'] for r in row['libmRows'] if any(op in r['definition'] for op in ('ASINH','ACOSH','ATANH'))]
conditions=[r for r in native if r['definition'].startswith('CORE-HYPER-')]
assert len(hyperbolic)==176 and len(conditions)==20
assert {'%DOUBLE-FLOAT+-2!','%DOUBLE-FLOAT--2!','%DOUBLE-FLOAT*-2!','%DOUBLE-FLOAT/-2!'}<=originals
parent.save(out/'numeric-execution.json',dict(hyperbolic_comparisons=len(hyperbolic),hyperbolic_max_ulps=max(r['ulps'] for r in hyperbolic),hyperbolic_condition_comparisons=4*len(conditions),status='PASS',original_definitions_executed=len(originals),non_nil_witness=len(non_nil),new_executions=sorted(originals-previous),arch_probe_cases=probes,arch_probe_comparisons=4*sum(probes.values()),unexecuted_probe='CORE-ARCH-STACK-SINGLE: initializing via the unchanged %SHORT-FLOAT definition is not dependency-closed',whole_file_numeric_definitions=sorted({r['definition'] for r in rows}),whole_file_numeric_cases=len(rows),whole_file_numeric_comparisons=4*len(rows),target_comparisons=sum(r['comparisons'] for r in execution['rows']),scope='Every numeric row names its actual whole-file module. Other corpus definitions retain their prior compilation provenance; the independent recount does not claim all prior executions used file environments. Four additional destructive double-float arithmetic functions execute whole-file. Hyperbolic target bodies are counted separately under the adopted two-ULP limit; signed zeros, exact identities and conditions are exact. Full ratio arithmetic, bignum library arithmetic and initialized stack-float macro callers still have missing dependencies. The symbol-identity observer asserts architecture-specific answers rather than bit-identical macro results.'))
