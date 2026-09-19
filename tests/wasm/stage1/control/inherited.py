#!/usr/bin/env python3
import argparse,importlib.util,sys
from pathlib import Path
from run import prepare
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('inherited_driver',HERE.parent/'constants/inherited.py');driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
driver.prepare=prepare
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();driver.run(a.evidence.resolve(),a.output.resolve())
