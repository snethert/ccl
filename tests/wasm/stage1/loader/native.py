"""Run the same cases natively in the pinned CCL image."""
from pathlib import Path
import json, os, shutil, sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
def lisp_cases(cases):
    rows=[]
    for x in cases:
        if 'call' in x: rows.append('(:call "%s" "%s" (%s))'%(x['call'][0],x['call'][1],' '.join(str(a) for a in x['args'])))
        else: rows.append('(:value "%s" "%s")'%(x['value'][0],x['value'][1]))
    return '('+' '.join(rows)+')'
def run(out):
    out.mkdir(parents=True,exist_ok=True)
    (out/'cases.lisp').write_text(lisp_cases(json.loads((HERE/'cases.json').read_text()))+'\n')
    kernel=out/'dx86cl64';shutil.copyfile(c.KERNEL,kernel);kernel.chmod(0o755)
    env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(c.ROOT)+'/',LOADER_SOURCE=str(HERE)+'/',LOADER_OUTPUT=str(out)+'/')
    try:
        c.command([kernel,'-I',c.IMAGE,'--no-init','--batch','--load',HERE/'native.lisp'],out/'native.log',env,timeout=120)
    finally:
        kernel.unlink()
    return c.read(out/'native.json')
if __name__=='__main__':print(json.dumps(run(Path(sys.argv[1]).resolve())))
