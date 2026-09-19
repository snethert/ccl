"""Requalify accepted generated corpora with this compiler proposal."""
import argparse,importlib.util
from pathlib import Path
from run import core
from backend import generate
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('live_inherited',HERE.parent/'constants/inherited.py');driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
def prepare(out):
 core.prior.generate=generate
 return core.prior.prepare(out)
driver.prepare=prepare
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();driver.run(a.evidence.resolve(),a.output.resolve())
