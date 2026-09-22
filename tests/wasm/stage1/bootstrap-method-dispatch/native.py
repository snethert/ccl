"""Qualify the final isolated backend with the existing native comparison."""
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import backend
runpy.run_path(str(HERE.parent / 'bootstrap-gcd/native.py'), run_name='__main__')
