"""Recompile the bootstrap loader wrapper under its original deferred marker."""
from pathlib import Path
import gzip,os,shutil,subprocess
from payloads import save,require,prefix_check
from method_reload_run import LOADS
HERE=Path(__file__).resolve().parent


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    source=a.source/'lib/compile-ccl.lisp';original=source.read_bytes()
    for mode in ('reference','observed'):
        argv=[str(a.source/'dx86cl64'),'--image-name',str(a.image),'--no-init','--batch',
              '--load',str(a.source/'lib/x8664env.lisp'),'--load',str(a.source/'xdump/faslenv.lisp')]
        for name in LOADS+('registry-callees/initial-marker.lisp',):argv+=['--load',str(HERE.parent/name)]
        argv+=['--eval','(progn (ccl-initial-marker::run) (ccl:quit))']
        save(a.output/(mode+'-command.json'),dict(argv=argv,cwd=str(a.source)))
        with (a.output/(mode+'.log')).open('wb') as log:
            p=subprocess.run(argv,cwd=a.source,env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(a.source),
                CCL_MARKER_OUTPUT=str(a.output),CCL_MARKER_MODE=mode),stdout=log,stderr=subprocess.STDOUT,timeout=120)
        require(p.returncode==0 and 'INITIAL-MARKER-PASS' in (a.output/(mode+'.log')).read_text(),'INITIAL_MARKER_NATIVE_'+mode)
    require(source.read_bytes()==original,'INITIAL_MARKER_SOURCE_CHANGED')
    require((a.output/'reference.dx64fsl').read_bytes()==(a.output/'observed.dx64fsl').read_bytes(),'INITIAL_MARKER_FASL_CHANGED')
    prefix_check(a.output/'build.jsonl',a.evidence/'2026-09-14-resident-bodies-r1/first-prefix.jsonl.gz')
    for name in ('build.jsonl','registries.jsonl'):
        path=a.output/name
        with path.open('rb') as inp,gzip.open(str(path)+'.gz','wb',compresslevel=1) as dest:shutil.copyfileobj(inp,dest)
        path.unlink()
    save(a.output/'summary.json',dict(status='PASS',source_unchanged=True,fasl_unchanged=True,readonly_prefix_identical=True))


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('source','image','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
