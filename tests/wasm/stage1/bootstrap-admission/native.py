"""Qualify the compiler and source-location-only target branches."""
import argparse, importlib.util, sys
from pathlib import Path
from backend import proposal
from sources import FILES
HERE=Path(__file__).resolve().parent;REG=HERE.parent/'registration'
sys.path.insert(0,str(REG));sys.path.insert(0,str(HERE.parent/'bootstrap-core'))
import unit
from native_compare import compare as compare_source

def source_pairs():
    paths=['level-0/'+s+'.lisp' for s in ('l0-def','l0-pred','l0-utils','l0-symbol')]+list(FILES)
    return [(p, p.replace('level-1/level-1.lisp','level-1.dx64fsl').replace('level-1/','l1-fasls/').replace('.lisp','.dx64fsl')) for p in paths]

spec=importlib.util.spec_from_file_location('registration_run',REG/'run.py')
driver=importlib.util.module_from_spec(spec)
text=(REG/'run.py').read_text()
old="if set(changed)!={'bin/systems.dx64fsl','bin/compile-ccl.dx64fsl'}:raise ValueError('unexpected FASL changes '+repr(changed))"
new="""if set(changed)!=set(EXPECTED):raise ValueError('unexpected FASL changes '+repr(changed))
            with tarfile.open(out/'baseline-fasls.tar.gz') as baseline_archive, tarfile.open(inputs/'source.tar') as sources:
                for srcname,faslname in SOURCE_PAIRS:
                    checked=compare_source(baseline_archive.extractfile(faslname).read(),(source/faslname).read_bytes(),sources.extractfile(srcname).read().decode(),(source/srcname).read_text())
                    save(out/(Path(srcname).stem+'-comparison.json'),checked)
"""
assert text.count(old)==1
text=text.replace(old,new).replace("'identical':162", "'identical':164-len(changed)")
exec(compile(text,str(REG/'run.py'),'exec'),driver.__dict__)
driver.proposal=proposal;driver.SOURCE_PAIRS=source_pairs();driver.EXPECTED=['bin/systems.dx64fsl','bin/compile-ccl.dx64fsl']+[p[1] for p in source_pairs()];driver.compare_source=compare_source
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('evidence','work','output'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();e=a.evidence.resolve()
    raise SystemExit(driver.run(e/'macos-u1-inputs',e/'2026-09-12-native-census-r7/baseline/build/dx86cl64',a.work.resolve(),a.output.resolve(),e/'2026-09-16-stage1-1a-r2/native'))
