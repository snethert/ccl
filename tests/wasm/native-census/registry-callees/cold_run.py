"""Compile one U1 file in fresh bootstrap sessions, with a native reference."""
from pathlib import Path
import gzip
import json
import os
import shutil
import subprocess
import time
from payloads import require,read,save,prefix_check

HERE=Path(__file__).resolve().parent
LOADS=('observer.lisp','dependencies.lisp','rich-observation/observer.lisp',
       'resident-bodies/export.lisp','dispatch-registry/inspect.lisp',
       'registry-callees/build-observer.lisp','registry-callees/cold-bodies.lisp')


def run(source,image,input_path,output,evidence):
    output.mkdir(parents=True,exist_ok=False)
    source_digest=__import__('hashlib').sha256(input_path.read_bytes()).hexdigest()
    for mode in ('reference','observed'):
        out=output/mode;out.mkdir();start=time.monotonic()
        argv=[str(source/'dx86cl64'),'--image-name',str(image),'--no-init','--batch',
              '--load',str(source/'lib/x8664env.lisp')]
        for path in LOADS:argv+=['--load',str(HERE.parent/path)]
        argv+=['--eval','(progn (ccl-cold-bodies::run) (ccl:quit))']
        env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(source),CCL_COLD_INPUT=str(input_path),
                 CCL_COLD_OUTPUT=str(out),CCL_COLD_MODE=mode)
        save(out/'command.json',dict(argv=argv,input_sha256=source_digest,cwd=str(source),mode=mode))
        try:
            with (out/'native.log').open('wb') as log:
                p=subprocess.run(argv,cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
            require(p.returncode==0 and 'COLD-BODY-PASS' in (out/'native.log').read_text(),'COLD_NATIVE_'+mode)
        finally:
            for name in ('build.jsonl','registries.jsonl'):
                path=out/name
                if path.exists():
                    with path.open('rb') as src,gzip.open(str(path)+'.gz','wb',compresslevel=1) as dest:shutil.copyfileobj(src,dest)
                    path.unlink()
        print(mode,round(time.monotonic()-start,3),'seconds',flush=True)
    require((output/'reference/outputs.json').read_bytes()==(output/'observed/outputs.json').read_bytes(),
            'COLD_REFERENCE_CODE_DIFFERENCE')
    require(__import__('hashlib').sha256(input_path.read_bytes()).hexdigest()==source_digest,'COLD_SOURCE_CHANGED')
    prefix_check(output/'observed/build.jsonl.gz',evidence/'2026-09-14-resident-bodies-r1/first-prefix.jsonl.gz')
    result=dict(status='PASS',source=str(input_path),source_sha256=source_digest,
        output_functions=len(read(output/'observed/outputs.json')['functions']),
        native_output_code_identical=True,readonly_prefix_identical=True,fasl_publication=False)
    save(output/'summary.json',result);print(result,flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','image','input','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence')
    a=p.parse_args();run(a.source.resolve(),a.image.resolve(),a.input.resolve(),a.output.resolve(),a.evidence.resolve())
