#!/usr/bin/env python3
"""R6/R6a of the proposal in a disposable U1 copy, reusing the accepted baseline."""
import argparse,importlib.util,sys
from pathlib import Path
from backend import generate
HERE=Path(__file__).resolve().parent;REG=HERE.parent/'registration'
sys.path.insert(0,str(REG));import unit
spec=importlib.util.spec_from_file_location('registration_run',REG/'run.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
def proposal(src,out):
    manifest=unit.proposal(src,out);p=out/'files/compiler/WASM32/wasm32-backend.lisp';p.write_text(generate())
    next(r for r in manifest['added'] if r['path']=='compiler/WASM32/wasm32-backend.lisp')['sha256']=unit.sha(p)
    unit.save(out/'unit.json',manifest);return manifest
driver.proposal=proposal
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('evidence','work','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();e=a.evidence.resolve()
    raise SystemExit(driver.run(e/'macos-u1-inputs',e/'2026-09-12-native-census-r7/baseline/build/dx86cl64',a.work.resolve(),a.output.resolve(),e/'2026-09-16-stage1-1a-r2/native'))
