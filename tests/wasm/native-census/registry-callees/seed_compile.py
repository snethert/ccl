"""Batch the seed-bearing source units with reference/observed output comparison."""
import argparse,gzip,json,os,shutil,subprocess,traceback
from pathlib import Path
from payloads import read,save,require,source_key
HERE=Path(__file__).resolve().parent


def run(a):
    require(a.timeout_seconds>0,'SEED_COMPILE_TIMEOUT')
    a.output.mkdir(parents=True,exist_ok=False)
    selected=read(a.selection);units=sorted(({source_key(f['source']) for f in selected['functions'].values()}-{None}) |
        {'level-0/X86/x86-pred.lisp','level-0/X86/x86-clos.lisp'})
    if a.additional_units:
        combined={u.casefold():u for u in units}
        for u in read(a.additional_units):
            require(isinstance(u,str) and not Path(u).is_absolute() and '..' not in Path(u).parts,'SEED_SOURCE_PATH')
            combined.setdefault(u.casefold(),u)
        units=sorted(combined.values())
    originals={u:(a.source/u).read_bytes() for u in units}
    save(a.output/'units.json',units)
    (a.output/'units.lisp').write_text('('+ ' '.join(json.dumps(str(a.source/u)) for u in units)+')\n')
    for mode in ('reference','observed'):
        out=a.output/mode;out.mkdir()
        argv=[str(a.source/'dx86cl64'),'--image-name',str(a.image),'--no-init','--batch',
              '--load',str(a.source/'lib/x8664env.lisp')]
        for n in ('observer.lisp','dependencies.lisp','rich-observation/observer.lisp','resident-bodies/export.lisp',
                  'dispatch-registry/inspect.lisp','registry-callees/build-observer.lisp','registry-callees/cold-bodies.lisp',
                  'startup-closure/image-inventory.lisp','registry-callees/seed-functions.lisp',
                  'registry-callees/deferred-probes.lisp','registry-callees/lap-observation.lisp',
                  'registry-callees/seed-compile.lisp'):
            argv+=['--load',str(HERE.parent/n)]
        argv+=['--eval','(progn (ccl-seed-functions::compile-seed-units) (ccl:quit))']
        env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(a.source),SEED_COMPILE_OUTPUT=str(out),SEED_COMPILE_MODE=mode,
            SEED_COMPILE_UNITS=str(a.output/'units.lisp'),SEED_ONLY_RETAIN='1',
            SEED_INSPECTOR_SOURCE=str(HERE.parent/'startup-closure/image-inventory.lisp'),
            SEED_IMAGE_INVENTORY=str(out/'image.json'))
        save(out/'command.json',dict(argv=argv,cwd=str(a.source),mode=mode,timeout_seconds=a.timeout_seconds))
        with (out/'native.log').open('wb') as log:
            p=subprocess.run(argv,cwd=a.source,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=a.timeout_seconds)
        require(p.returncode==0 and f'SEED-COMPILE-PASS {len(units)}' in (out/'native.log').read_text(),
                'SEED_COMPILE_EXIT '+mode)
        for name in ('build.jsonl','registries.jsonl'):
            path=out/name
            if path.exists():
                with path.open('rb') as src,gzip.open(str(path)+'.gz','wb',compresslevel=1) as dst:shutil.copyfileobj(src,dst)
                path.unlink()
        print(mode,'complete',len(units),'units',flush=True)
    for index,unit in enumerate(units):
        name=f'outputs-{index:03d}.json'
        require((a.output/'reference'/name).read_bytes()==(a.output/'observed'/name).read_bytes(),
                'SEED_REFERENCE_CODE_DIFFERENCE '+unit)
        require((a.source/unit).read_bytes()==originals[unit],'SEED_COMPILE_SOURCE_CHANGED')
    summary=dict(status='PASS',units=len(units),native_output_code_identical=True,source_unchanged=True,fasls_written=False)
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('source','image','selection','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--additional-units',type=Path)
    p.add_argument('--timeout-seconds',type=int,default=900,help='Deadline for each native session; increase for source-wide captures.')
    a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():
            (a.output/'failure.txt').write_text(traceback.format_exc())
            for n in ('seed_compile.py','seed-compile.lisp','seed-functions.lisp'):(a.output/n).write_bytes((HERE/n).read_bytes())
        raise
