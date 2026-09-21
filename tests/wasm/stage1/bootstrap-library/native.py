#!/usr/bin/env python3
"""Compare the compiler and source proposal against pristine native U1."""
import argparse, importlib.util, sys
from pathlib import Path
from backend import generate, proposal as derive
HERE=Path(__file__).resolve().parent
REG=HERE.parent/'registration'
sys.path.insert(0,str(REG))
sys.path.insert(0,str(HERE.parent/'bootstrap-core'))
import unit
spec=importlib.util.spec_from_file_location('registration_run',REG/'run.py')
driver=importlib.util.module_from_spec(spec)
text=(REG/'run.py').read_text()
old="if set(changed)!={'bin/systems.dx64fsl','bin/compile-ccl.dx64fsl'}:raise ValueError('unexpected FASL changes '+repr(changed))"
new="""if set(changed)!={'bin/systems.dx64fsl','bin/compile-ccl.dx64fsl','level-0/l0-def.dx64fsl','level-0/l0-pred.dx64fsl','level-0/l0-utils.dx64fsl','level-0/l0-symbol.dx64fsl'}:raise ValueError('unexpected FASL changes '+repr(changed))
            from native_source import compare as compare_source
            with tarfile.open(out/'baseline-fasls.tar.gz') as baseline_archive, tarfile.open(inputs/'source.tar') as sources:
                for stem in ('l0-def','l0-pred','l0-utils','l0-symbol'):
                    name='level-0/'+stem
                    checked=compare_source(baseline_archive.extractfile(name+'.dx64fsl').read(),(source/(name+'.dx64fsl')).read_bytes(),sources.extractfile(name+'.lisp').read().decode(),(source/(name+'.lisp')).read_text())
                    save(out/(stem+'-comparison.json'),checked)
"""
assert text.count(old)==1
text=text.replace(old,new).replace("'identical':162", "'identical':158")
# Reuse native execution only after the new build and snapshot are byte-equal
# to a passing qualification. This never reuses the generated Wasm tests.
if '--reuse-native' in sys.argv:
    reuse=Path(sys.argv[sys.argv.index('--reuse-native')+1]).resolve()
    code="""prior_dir=Path(REUSE_NATIVE)
            prior=json.loads((prior_dir/'run.json').read_text())
            assert prior['status']=='PASS' and prior['inputs']==pins and prior['kernel_sha256']==sha(kernel)
            assert registered==json.loads((prior_dir/'registered-fasls.json').read_text())
            assert after==json.loads((prior_dir/'registered-snapshot.json').read_text())
            report['registered_tests']=prior['registered_tests']
            report['registered_tests_reuse']={'run_sha256':sha(prior_dir/'run.json'),'native_fasl_inventory_sha256':sha(prior_dir/'registered-fasls.json'),'snapshot_sha256':sha(prior_dir/'registered-snapshot.json'),'executed_here':False,'reason':'Exact equality of all 164 freshly rebuilt native FASLs and the complete native snapshot against the retained passing native test run; new Wasm functions are exercised separately.'}
"""
    text=text.replace("report['registered_tests']=tests('registered-tests',True)", code.strip())
    driver.REUSE_NATIVE=str(reuse)
exec(compile(text,str(REG/'run.py'),'exec'),driver.__dict__)
def proposal(src,out):
    manifest=derive(src,out)
    p=out/'files/compiler/WASM32/wasm32-backend.lisp';p.write_text(generate())
    next(r for r in manifest['added'] if r['path']=='compiler/WASM32/wasm32-backend.lisp')['sha256']=unit.sha(p)
    unit.save(out/'unit.json',manifest)
    return manifest
driver.proposal=proposal
if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--reuse-native',type=Path)
    for n in ('evidence','work','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();e=a.evidence.resolve()
    raise SystemExit(driver.run(e/'macos-u1-inputs',e/'2026-09-12-native-census-r7/baseline/build/dx86cl64',a.work.resolve(),a.output.resolve(),e/'2026-09-16-stage1-1a-r2/native'))
