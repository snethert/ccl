"""Remove each new scalar-complex shape count check on its own."""
from pathlib import Path
import shutil
import common as c
HERE=Path(__file__).resolve().parent


def check(out):
    compiled=out/'compiled'
    work=out/'complex-mutants';work.mkdir()
    rows=[]
    source=(compiled/'runtime/collector.c').read_text()
    image=(compiled/'runtime/heap-image.mjs').read_text()
    flags=['--target=wasm32','-O2','-nostdlib','-fno-builtin','-matomics','-mbulk-memory',
           '-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,--shared-memory',
           '-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer']
    for kind in ('collector','image'):
        for tag,count,size in ((71,3,12),(79,5,20)):
            name=f'{kind}-{tag}-count'
            target=work/name; (target/'runtime').mkdir(parents=True)
            shutil.copyfile(compiled/'runtime/sha256.mjs',target/'runtime/sha256.mjs')
            shutil.copyfile(compiled/'runtime/bytes.mjs',target/'runtime/bytes.mjs')
            (target/'runtime/heap-image.mjs').write_text(image)
            shutil.copyfile(compiled/'collector.wasm',target/'collector.wasm')
            if kind=='collector':
                old=f'case {tag}:return n=={count}?{size}:0xffffffffu;'
                assert source.count(old)==1
                (target/'mutant.c').write_text(source.replace(old,f'case {tag}:return {size};'))
                c.command(['/usr/local/opt/llvm/bin/clang',*flags,target/'mutant.c','-o',target/'collector.wasm'],target/'compile.log')
            else:
                old=f'tag==={tag}&&n==={count}';assert image.count(old)==1
                (target/'runtime/heap-image.mjs').write_text(image.replace(old,f'tag==={tag}'))
            import subprocess
            try:
                c.command([c.NODE,HERE/'complex-shapes.mjs',target,target/'unexpected.json'],target/'check.log',timeout=60)
            except subprocess.CalledProcessError:
                log=(target/'check.log').read_text()
                needle='invalid count is a checked refusal' if kind=='collector' else 'Missing expected exception'
                assert needle in log, (name,log[-1200:])
                rows.append(dict(name=name,rejected_by=needle))
            else:raise AssertionError('shape-count omission survived: '+name)
    c.save(out/'complex-controls.json',dict(status='PASS',rows=rows))
    retained=out/'development/complex-count-controls';retained.mkdir(parents=True)
    for file in c.files(work):
        if file.suffix in ('.c','.mjs','.log'):
            dest=retained/file.relative_to(work);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,dest)
    shutil.rmtree(work)
