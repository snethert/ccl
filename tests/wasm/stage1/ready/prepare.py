"""Prepare the written READY driver; compiler and pending image sources stay fixed."""
from pathlib import Path
import importlib.util
import shutil
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c

def prepare(out):
    spec=importlib.util.spec_from_file_location('class_image',HERE.parent/'class-image/prepare.py')
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    parent.prepare(out)
    shutil.copyfile(HERE/'worker.mjs',out/'ready-worker.mjs')
    shutil.copyfile(HERE/'process.mjs',out/'process.mjs')
    shutil.copyfile(c.ROOT/'runtime/wasm32/initialization-owner.mjs',out/'runtime/initialization-owner.mjs')
    code=c.read(out/'class-image-code.json')
    for name in ('runtime/initialization-owner.mjs','process.mjs','ready-worker.mjs'):
        code[name]=c.sha(out/name)
    (out/'class-image-code.json').write_bytes(c.canonical(code))
    (out/'class-image-code.sha256').write_text(c.sha(out/'class-image-code.json')+'\n')

if __name__=='__main__':prepare(Path(sys.argv[1]))
