"""One bound CCL session; explicit compile/oracle phases and cached WABT."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import os
import shutil
import sys
import tempfile
import time
import tarfile
import common as c


def environment():
    bound = c.parent_inputs()
    return dict(version=1, parent_packet=c.sha(c.PARENT/'packet.json'),
                parent_sources=c.sha(c.PARENT/'source-pins.json'),
                parent_drivers=bound['review-artifacts.tar.gz'],
                proposal_and_corpus=bound['execution.tar.gz'],
                dependencies=c.read(c.PARENT/'dependencies.json'),
                kernel=c.sha(c.KERNEL), image=c.sha(c.IMAGE),
                source=c.sha(c.STORE/'macos-u1-inputs/source.tar'),
                bootstrap=c.sha(c.STORE/'macos-u1-inputs/bootstrap.tar.gz'),
                registration=c.sha(c.ROOT/'tests/wasm/stage1/registration/load.lisp'),
                implementation={str(p.relative_to(c.HERE)):c.sha(p)
                                for p in c.files(c.HERE/'driver')},
                builder={name:c.sha(c.HERE/name) for name in ('build.py','common.py')},
                modes=['default','class'], environment_order='retained driver/compile.lisp',
                source_root_policy='pristine U1 with the exact parent proposal')


def prepare(parent, stage):
    c.extract(parent/'review-artifacts.tar.gz', stage, lambda n:n.startswith('driver/'))
    hashes=c.read(parent/'review-artifacts.json')['files']
    c.verify_files(stage,{n:h for n,h in hashes.items() if n.startswith('driver/')})
    for p in c.files(c.HERE/'driver'):
        shutil.copyfile(p,stage/'driver'/p.name)
    c.extract(parent/'execution.tar.gz',stage,
              lambda n:n.startswith('compiled/proposal/') or n.startswith('runtime/') or
              ('/' not in n and n.endswith(('.wasm','.mjs'))))
    # The compiler and native oracle consume these exact files, in this order.
    c.save(stage/'driver-manifest.json',c.inventory(stage/'driver'))


def cold_session(stage):
    prepare(c.PARENT,stage)
    output=stage/'compiled'
    with tempfile.TemporaryDirectory(prefix='ccl-p4-u1-') as tmp:
        work=Path(tmp);source=work/'ccl';source.mkdir()
        for name in ('source.tar','bootstrap.tar.gz'):
            with tarfile.open(c.STORE/'macos-u1-inputs'/name) as archive:
                archive.extractall(source,filter='data')
        c.save(work/'stage1-disposable.json',{'source':str(source)})
        shutil.copyfile(c.KERNEL,source/'dx86cl64');(source/'dx86cl64').chmod(0o755)
        shutil.copyfile(c.IMAGE,source/'dx86cl64.image')
        sys.path.insert(0,str(c.ROOT/'tests/wasm/stage1/registration'))
        from unit import Unit
        env=dict(PATH='/usr/local/bin:/usr/bin:/bin',LANG='C',LC_ALL='C',
                 CCL_DEFAULT_DIRECTORY=str(source),POOL_OUTPUT=str(output)+'/')
        argv=[source/'dx86cl64','--no-init','--batch','--eval',
              '(ccl::in-development-mode (load "ccl:lib;systems.lisp") (load "ccl:lib;compile-ccl.lisp"))',
              '--load',c.ROOT/'tests/wasm/stage1/registration/load.lisp',
              '--load',stage/'driver/compile.lisp']
        with Unit(source,output/'proposal'):
            seconds=c.command(argv,stage/'compile.log',env,source,timeout=600)
            if 'VALIDATION-BUILD-PASS' not in (stage/'compile.log').read_text():
                raise ValueError('compiler did not reach completion')
            assert (output/'compiler.image').is_file()
            native_seconds=c.command([source/'dx86cl64','-I',output/'compiler.image',
                 '--no-init','--batch','--load',stage/'driver/native.lisp'],
                 stage/'oracle.log',env,source,timeout=600)
            if 'VALIDATION-ORACLE-PASS' not in (stage/'oracle.log').read_text():
                raise ValueError('oracle did not reach completion')
            shutil.copyfile(source/'bin/wasm32-backend.dx64fsl',output/'compiler.dx64fsl')
        c.save(stage/'build-completion.json',dict(status='PASS',compiler_rebuilt=True,
              oracle_rebuilt=True,seconds=seconds,oracle_seconds=native_seconds,
              phases=[c.read(output/(p+'-phase.json')) for p in ('compile','oracle')]))


def build(out,cache,workers=4,cold=False):
    start=time.monotonic();identity=environment();key=c.digest(identity)
    hit=c.cache_read(cache,'session',key)
    rebuilt=hit is None or cold
    if rebuilt:
        with c.cache_write(cache,'session',key) as stage:
            cold_session(stage)
            c.save(stage/'environment.json',identity)
        hit=c.cache_read(cache,'session',key)
    out=Path(out);out.mkdir()
    shutil.copytree(hit,out,dirs_exist_ok=True)
    (out/'cache-manifest.json').unlink()
    paths=sorted((out/'compiled').glob('*.wat'))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        assembly=list(pool.map(lambda p:c.assemble(p,cache,cold),paths))
    c.save(out/'assembly.json',dict(workers=workers,rows=assembly))
    c.save(out/'build-invocation.json',dict(status='PASS',key=key,cache_hit=not rebuilt,
           compiler_processes=int(rebuilt),oracle_processes=int(rebuilt),oracle_rebuilt=rebuilt,
           wabt_processes=sum(r['rebuilt'] for r in assembly),workers=workers,
           seconds=time.monotonic()-start,environment=identity))
    return c.read(out/'build-invocation.json')
