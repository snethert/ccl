#!/usr/bin/env python3
"""Run the accepted B/condition/error/loader corpus with the proposal."""
import argparse,importlib.util,sys
from pathlib import Path
from backend import generate
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'constants'
sys.path.insert(0,str(BASE))
spec=importlib.util.spec_from_file_location('constants_inherited',BASE/'inherited.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver);driver.generate=generate
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('evidence','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();driver.run(a.evidence.resolve(),a.output.resolve())
