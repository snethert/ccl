"""Re-execute the existing LL19 native-derived corpus with the new compiler."""
import argparse,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 spec=importlib.util.spec_from_file_location('gd_proposal',HERE/'backend.py');backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)
 sys.path.insert(0,str(HERE.parent/'control'))
 spec=importlib.util.spec_from_file_location('gd_inherited_control',HERE.parent/'control/run.py');driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
 driver.generate=backend.generate
 driver.run(a.evidence.resolve(),a.output.resolve())
