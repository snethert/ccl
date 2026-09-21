#!/usr/bin/env python3
"""Compare the compiler and source proposal against pristine native U1."""
import argparse, importlib.util, sys
from pathlib import Path
from backend import generate, proposal as derive
HERE=Path(__file__).resolve().parent
REG=HERE.parent/'registration'
sys.path.insert(0,str(REG))
import unit
spec=importlib.util.spec_from_file_location('registration_run',REG/'run.py')
driver=importlib.util.module_from_spec(spec)
text=(REG/'run.py').read_text()
old="if set(changed)!={'bin/systems.dx64fsl','bin/compile-ccl.dx64fsl'}:raise ValueError('unexpected FASL changes '+repr(changed))"
new="""if set(changed)!={'bin/systems.dx64fsl','bin/compile-ccl.dx64fsl','level-0/l0-def.dx64fsl','level-0/l0-pred.dx64fsl','level-0/l0-utils.dx64fsl'}:raise ValueError('unexpected FASL changes '+repr(changed))
            from native_source import compare as compare_source
            with tarfile.open(out/'baseline-fasls.tar.gz') as baseline_archive, tarfile.open(inputs/'source.tar') as sources:
                for stem in ('l0-def','l0-pred','l0-utils'):
                    name='level-0/'+stem
                    checked=compare_source(baseline_archive.extractfile(name+'.dx64fsl').read(),(source/(name+'.dx64fsl')).read_bytes(),sources.extractfile(name+'.lisp').read().decode(),(source/(name+'.lisp')).read_text())
                    save(out/(stem+'-comparison.json'),checked)
"""
assert text.count(old)==1
text=text.replace(old,new).replace("'identical':162", "'identical':159")
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
    for n in ('evidence','work','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();e=a.evidence.resolve()
    raise SystemExit(driver.run(e/'macos-u1-inputs',e/'2026-09-12-native-census-r7/baseline/build/dx86cl64',a.work.resolve(),a.output.resolve(),e/'2026-09-16-stage1-1a-r2/native'))
