"""Append the READY file to the retained whole-file compilation environment."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
from probe import probe
from prepare import prepare
import storage

if __name__=='__main__':
    base,out=map(Path,sys.argv[1:])
    with storage.lease([base,out]):
        report=probe(base,HERE/'startup.lisp',HERE/'inputs.lisp',out,c.DEFAULT_CACHE,'class',4)
        prepare(out)
        c.save(out/'ready-compile.json',report)
        print(report['status'],report['compiled_modules'])
