"""Retain division as a delta; rerun the native bignum reader proof."""
from pathlib import Path
import importlib.util
import subprocess
import sys
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('numeric_packet',HERE.parent/'bootstrap-numeric-dispatch/packet.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
parent.HERE=HERE
parent.PARENT=parent.EVIDENCE/'2026-09-22-stage1-bootstrap-limb-multiply-r1'
parent.ID='STAGE1-BOOTSTRAP-LIMB-DIVISION-R1'

def reports(numeric,environment,native):
    output=numeric/'reader-proof'
    subprocess.run([sys.executable,HERE/'readers.py',output],check=True)
    subprocess.run([sys.executable,HERE/'summary.py',numeric,environment,native],check=True)
    subprocess.run([sys.executable,HERE.parent/'bootstrap-lexpr-spread/frontier.py',environment,numeric],check=True)
parent.reports=reports
if __name__=='__main__':parent.main()
