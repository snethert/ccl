#!/usr/bin/env python3
import argparse,subprocess,json
from pathlib import Path
from unit import HERE,ROOT
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
for path in sorted(a.output.glob('*.wat')):
    subprocess.run(['/usr/local/bin/wat2wasm','--enable-threads',str(path),'-o',str(path.with_suffix('.wasm'))],check=True)
subprocess.run(['/usr/local/bin/node',str(HERE/'execute.mjs'),str(a.output),str(ROOT/'doc/WASM/contracts/tcr.v1.json')],check=True)
