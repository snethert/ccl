"""Reload the source of the sixteen methods lacking intrinsic source notes."""
from pathlib import Path
import gzip
import hashlib
import json
import os
import shutil
import subprocess
from payloads import require,save,prefix_check

HERE=Path(__file__).resolve().parent
LOADS=('observer.lisp','dependencies.lisp','rich-observation/observer.lisp',
       'resident-bodies/export.lisp','dispatch-registry/inspect.lisp',
       'registry-callees/build-observer.lisp','registry-callees/deferred-probes.lisp',
       'registry-callees/method-reload.lisp')
UNITS=(('library/sockets.lisp',[36,37,40,43,151,126,125,124,123,46,138,17]),
       ('lib/describe.lisp',[1583]),('level-1/l1-io.lisp',[8951,8949,8947]))


def run(source,image,output,evidence):
    output.mkdir(parents=True,exist_ok=False);summaries=[]
    for unit,methods in UNITS:
        out=output/Path(unit).stem;out.mkdir();path=source/unit;original=path.read_bytes()
        provenance=dict(source=unit,sha256=hashlib.sha256(original).hexdigest(),selection='complete-file')
        if unit=='level-1/l1-io.lisp':
            # Loading the whole printer replaces machinery used by live
            # observation. Keep exactly the three conditional method forms.
            start=original.index(b'#+x86-target\n(defmethod print-object ((tra tagged-return-address)')
            end=original.index(b'(defmethod print-object ((c class-cell)',start)
            excerpt=b'(in-package "CCL")\n'+original[start:end]
            fragment=out/'ccl';fragment.mkdir();path=fragment/'printer-methods.lisp';path.write_bytes(excerpt)
            provenance.update(selection='three-conditional-methods',start=start,end=end,
                              excerpt_sha256=hashlib.sha256(excerpt).hexdigest(),prefix='(in-package "CCL")\n')
        save(out/'source.json',provenance)
        for mode in ('reference','observed'):
            argv=[str(source/'dx86cl64'),'--image-name',str(image),'--no-init','--batch',
                  '--load',str(source/'lib/x8664env.lisp'),'--load',str(source/'xdump/faslenv.lisp')]
            for name in LOADS:argv+=['--load',str(HERE.parent/name)]
            argv+=['--eval','(progn (ccl-method-reload::run) (ccl:quit))']
            env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(source),CCL_RELOAD_INPUT=str(path),CCL_RELOAD_OUTPUT=str(out),
                     CCL_RELOAD_METHODS='('+' '.join(map(str,methods))+')',CCL_RELOAD_MODE=mode)
            save(out/(mode+'-command.json'),dict(argv=argv,cwd=str(source),mode=mode,methods=methods,input=str(path)))
            with (out/(mode+'.log')).open('wb') as log:
                p=subprocess.run(argv,cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
            require(p.returncode==0 and ('METHOD-REFERENCE-PASS' if mode=='reference' else 'METHOD-RELOAD-PASS')
                    in (out/(mode+'.log')).read_text(),'METHOD_NATIVE_'+mode)
        require((out/'reference.dx64fsl').read_bytes()==(out/'observed.dx64fsl').read_bytes(),'METHOD_FASL_CHANGED')
        prefix_check(out/'build.jsonl',evidence/'2026-09-14-resident-bodies-r1/first-prefix.jsonl.gz')
        for name in ('build.jsonl','registries.jsonl'):
            path=out/name
            with path.open('rb') as inp,gzip.open(str(path)+'.gz','wb',compresslevel=1) as dest:shutil.copyfileobj(inp,dest)
            path.unlink()
        require((source/unit).read_bytes()==original,'METHOD_SOURCE_CHANGED')
        summaries.append(dict(unit=unit,methods=len(methods),fasl_unchanged=True,readonly_prefix_identical=True))
        print(summaries[-1],flush=True)
    result=dict(status='PASS',units=summaries);save(output/'native-summary.json',result)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','image','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence');a=p.parse_args()
    try:run(a.source,a.image,a.output,a.evidence)
    except BaseException:
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
