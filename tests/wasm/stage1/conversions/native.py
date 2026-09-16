#!/usr/bin/env python3
"""R6 over the complete proposed unit, reusing the accepted pristine baseline."""
import argparse,importlib.util
from pathlib import Path
from support import REG,proposal
spec=importlib.util.spec_from_file_location('registration_run',REG/'run.py');driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
driver.proposal=proposal
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('evidence','work','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.evidence.resolve()
 raise SystemExit(driver.run(e/'macos-u1-inputs',e/'2026-09-12-native-census-r7/baseline/build/dx86cl64',a.work.resolve(),a.output.resolve(),e/'2026-09-16-stage1-1a-r2/native'))
