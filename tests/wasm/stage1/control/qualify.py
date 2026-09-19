#!/usr/bin/env python3
"""Execute and retain LL19, using an exact separately executed native R6 unit."""
import argparse,tempfile
from pathlib import Path
from packet import ROOT,command,retain
HERE=Path(__file__).resolve().parent
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('evidence','native','output'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--work',type=Path,required=True);a=p.parse_args()
 work=a.work.resolve();work.mkdir(parents=True,exist_ok=False)
 import sys
 command([sys.executable,HERE/'run.py','--evidence',a.evidence.resolve(),'--output',work/'execution','--qualify'],work/'execution.log')
 command([sys.executable,HERE/'inherited.py','--evidence',a.evidence.resolve(),'--output',work/'inherited'],work/'inherited.log')
 retain(a.evidence.resolve(),work/'execution',a.native.resolve(),work/'inherited',a.output.resolve())
