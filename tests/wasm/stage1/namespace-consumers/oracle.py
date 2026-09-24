"""Run the same public Lisp consumers in the pinned native CCL image."""
from pathlib import Path
import os, shutil, sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c

def run(out):
    out.mkdir(parents=True,exist_ok=True)
    c.command([c.NODE,HERE.parent/'namespace/prepare.mjs',out],out/'native-prepare.log')
    c.command([c.NODE,'--input-type=module','-e',
        "import fs from 'node:fs'; import {manifest} from '"+(HERE/'fixtures.mjs').as_uri()+"'; "
        "for(const e of manifest().entries) if(e.kind==='file') fs.writeFileSync(process.argv[1]+e.path,e.bytes);",
        out/'native-tree'],out/'native-large.log')
    kernel=out/'dx86cl64'
    shutil.copyfile(c.KERNEL,kernel);kernel.chmod(0o755)
    env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(out/'native-tree/ccl')+'/',NAMESPACE_SOURCE=str(HERE)+'/',
             NAMESPACE_ROOT=str(out/'native-tree'),NAMESPACE_NATIVE=str(out/'consumer-native.json'))
    paths=list((out/'native-tree').rglob('*'))+[out/'native-tree']
    try:
        for p in paths:p.chmod(0o555 if p.is_dir() else 0o444)
        c.command([kernel,'-I',c.IMAGE,'--no-init','--batch','--load',HERE/'native.lisp'],out/'consumer-native.log',env,timeout=60)
    finally:
        for p in paths:p.chmod(0o755 if p.is_dir() else 0o644)
        kernel.unlink()

if __name__=='__main__':run(Path(sys.argv[1]).resolve())
