"""Compile the native LAP units with reversible assembler observation."""
from pathlib import Path
import gzip,os,shutil,subprocess,traceback
from payloads import read,save,require,prefix_check,source_key
from method_reload_run import LOADS

HERE=Path(__file__).resolve().parent


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    units=sorted({source_key(r['source']) for r in read(a.frontends)})
    original_paths={str(p.relative_to(a.source)).casefold():p for p in a.source.glob('level-0/**/*.lisp')}
    completed=[]
    for unit in units:
        source=original_paths[unit];old=source.read_bytes();out=a.output/source.stem;out.mkdir()
        for mode in ('reference','observed'):
            argv=[str(a.source/'dx86cl64'),'--image-name',str(a.image),'--no-init','--batch',
                  '--load',str(a.source/'lib/x8664env.lisp'),'--load',str(a.source/'xdump/faslenv.lisp')]
            for name in LOADS[:-1]+('registry-callees/lap-observation.lisp',):argv+=['--load',str(HERE.parent/name)]
            argv+=['--eval','(progn (ccl-lap-census::run) (ccl:quit))']
            save(out/(mode+'-command.json'),dict(argv=argv,cwd=str(a.source)))
            env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(a.source),CCL_LAP_INPUT=str(source),
                     CCL_LAP_OUTPUT=str(out),CCL_LAP_MODE=mode)
            with (out/(mode+'.log')).open('wb') as log:
                p=subprocess.run(argv,cwd=a.source,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
            require(p.returncode==0 and 'LAP-NATIVE-PASS' in (out/(mode+'.log')).read_text(),'LAP_NATIVE_'+mode+' '+unit)
        require((out/'reference.dx64fsl').read_bytes()==(out/'observed.dx64fsl').read_bytes(),'LAP_FASL_DIFFERENCE '+unit)
        prefix_check(out/'build.jsonl',a.evidence/'2026-09-14-resident-bodies-r1/first-prefix.jsonl.gz')
        for name in ('build.jsonl','registries.jsonl'):
            path=out/name
            with path.open('rb') as inp,gzip.open(str(path)+'.gz','wb',compresslevel=1) as dest:shutil.copyfileobj(inp,dest)
            path.unlink()
        require(source.read_bytes()==old,'LAP_SOURCE_CHANGED')
        completed.append(dict(unit=unit,fasl_unchanged=True,readonly_prefix_identical=True))
        print(completed[-1],flush=True)
        save(a.output/'progress.json',completed)
    save(a.output/'summary.json',dict(status='PASS',units=completed))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('source','image','output','frontends'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence');a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
