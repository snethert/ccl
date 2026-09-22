"""Build the integrated float module and its pinned libm."""
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location('integrated_float_build',ROOT/'runtime/wasm32/build-float.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
build=m.build
