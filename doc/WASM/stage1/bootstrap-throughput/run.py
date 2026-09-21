#!/usr/bin/env python3
"""Run measure.lisp inside the retained compile driver. Reviewer instrument; writes one text tally."""
import argparse,importlib.util,os
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];E=ROOT.parent/'ccl-evidence'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();out=a.output.resolve()
tally=out.with_suffix('.tally.txt')
import json
source=(HERE/'measure.lisp').read_text().replace('(getenv "BT_ROOT")',json.dumps(str(ROOT))).replace('(getenv "BT_OUTPUT")',json.dumps(str(tally)))  # the driver runs CCL with a clean environment
spec=importlib.util.spec_from_file_location('cc',ROOT/'tests/wasm/stage1/startup-joined/compile.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
try:c.compile_source(E,out,source,None)
except RuntimeError:pass  # the driver expects modules; this instrument emits none
print(tally.read_text())
