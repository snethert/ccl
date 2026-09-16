"""Compile the U1 constructor privately and exercise returned native bodies."""
import os,subprocess,traceback,argparse
from pathlib import Path
from run import HERE,read,save,require


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    original=(a.source/'level-1/l1-clos-boot.lisp').read_bytes()
    argv=[str(a.source/'dx86cl64'),'--image-name',str(a.image),'--no-init','--batch']
    for n in ('observer.lisp','dependencies.lisp','rich-observation/observer.lisp','resident-bodies/export.lisp',
              'finite-callees/probes.lisp','finite-callees/constructor-probes.lisp'):
        argv+=['--load',str(HERE.parent/n)]
    argv+=['--eval','(progn (census-finite-probes::constructor-run) (ccl:quit))']
    save(a.output/'command.json',dict(argv=argv,cwd=str(a.source)))
    with (a.output/'native.log').open('wb') as log:
        p=subprocess.run(argv,cwd=a.source,env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(a.source),
            FINITE_OUTPUT=str(a.output/'native.json')),stdout=log,stderr=subprocess.STDOUT,timeout=90)
    require(p.returncode==0,'CONSTRUCTOR_NATIVE_EXIT')
    require((a.source/'level-1/l1-clos-boot.lisp').read_bytes()==original,'CONSTRUCTOR_SOURCE_CHANGED')
    raw=read(a.output/'native.json')
    require(raw['restored'] is True and raw['factory_checks']==12 and len(raw['checks'])==6,
            'CONSTRUCTOR_NATIVE_COMPLETION')
    (a.output/'source-form.lisp').write_bytes(original[raw['source_start']:raw['source_end']])
    print(dict(status='PASS',probes=6,factory_checks=12,source_unchanged=True),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('source','image','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
