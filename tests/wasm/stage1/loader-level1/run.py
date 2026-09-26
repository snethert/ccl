"""Ordered whole-file compilation and explicitly bounded target execution."""
from pathlib import Path
import platform
import subprocess
import sys
import time
import product
import storage

c, HERE = product.c, product.HERE
config = product.module('level1_config', HERE.parent / 'loader-chain/config.py')


def inputs():
    folders = ('loader-level1', 'loader-chain', 'loader-gc', 'loader-fasl',
               'loader-hash', 'loader', 'loader-level0', 'loader-locks', 'loader-aref',
               'loader-new-ptr', 'loader-def', 'registration', 'bootstrap-validation')
    return {str(p.relative_to(c.ROOT)): c.sha(p) for folder in folders
            for p in c.files(HERE.parent / folder)
            if p.suffix in ('.py', '.mjs', '.json', '.lisp')}


def run(out):
    assert not out.exists(), 'use a fresh output directory'
    started = time.monotonic()
    pins = inputs()
    witnesses = config.witnesses() + [HERE.parent / 'loader-fasl/witnesses/fasl.lisp']
    witnesses += sorted((HERE.parent / 'loader-gc/witnesses').glob('*.lisp'))
    witnesses += [HERE / 'witnesses.lisp']
    cases = config.cases(product) + c.read(HERE.parent / 'loader-fasl/cases.json') + [
        dict(id='gc-fresh', call=['CCL', 'LOADER-GC-FRESH'], args=[]),
        dict(id='gc-constructor-flags', call=['CCL', 'LOADER-GC-CONSTRUCTOR-FLAGS'], args=[])]
    cases += [dict(id='level1-' + name, call=['CCL', 'LOADER-LEVEL1-' + name.upper()], args=[])
              for name in ('platform', 'metrics', 'metadata', 'plist', 'keyword', 'sets')]
    controls = [HERE.parent / n for n in ('loader-hash/controls/buffers.mjs', 'loader-fasl/controls/fasl.mjs')]
    controls += sorted((HERE.parent / 'loader-gc/controls').glob('*.mjs'))
    startup = c.read(HERE.parent / 'loader-fasl/startup-refusals.json')
    startup[2] = {**startup[2], 'name': 'force-export packages need callable STRING=',
                  'unbound': [['COMMON-LISP', 'STRING=']]}
    startup.append(dict(name='pathname escape DEFSTATIC initializer is not ready',
        symbols=[['CCL', '%DEFGLOBAL']],
        reason='checked 10'))
    startup.append(dict(name='TYPE-OF alias needs callable %TYPE-OF',
        symbols=[['CCL', '%FHAVE'], ['CCL', '%TYPE-OF']],
        unbound=[['CCL', '%TYPE-OF']], reason='checked 10'))
    for variable in ('*TOTAL-GC-MICROSECONDS*', '*TOTAL-BYTES-FREED*'):
        startup.append(dict(name=variable + ' pointer-function registration is not ready',
            symbols=[['CCL', '*LISP-SYSTEM-POINTER-FUNCTIONS*'], ['COMMON-LISP', 'MEMBER']],
            childSymbols=[['CCL', variable]], reason='checked 10'))
    product.module('level1_build', HERE.parent / 'loader-chain/build.py').run(
        out, product, witnesses, pins, checks=[HERE.parent / 'loader-fasl/scratch.lisp'],
        level1=True, preflights=[HERE / 'dispatch.lisp'], crossload_stop='level-1/l1-boot-2.lisp',
        execution_files=lambda name: name.startswith('level-0/') or name == 'level-1/l1-utils.lisp',
        support_forms=['("ccl:level-1;l1-boot-1.lisp" defun host-platform)',
                       '("ccl:level-1;l1-init.lisp" defloadvar *total-gc-microseconds* *total-bytes-freed*)'])
    result = product.module('level1_exercise', HERE.parent / 'loader-chain/exercise.py').run(
        out, product, cases, witnesses, controls, pins,
        startup,
        {**c.read(HERE.parent / 'loader-hash/pending-cases.json'),
         **c.read(HERE.parent / 'loader-fasl/pending-cases.json')})
    assert inputs() == pins
    c.save(out / 'environment.json', dict(platform=platform.platform(), python=sys.version,
        kernel=c.sha(c.KERNEL), image=c.sha(c.IMAGE),
        upstream_inputs=c.read(c.STORE / 'macos-u1-inputs/pins.json'),
        tools={str(p): dict(sha256=c.sha(p), version=subprocess.check_output(
            [str(p), '--version'], text=True).splitlines()[0]) for p in
            (c.NODE, c.WABT, Path('/usr/local/opt/llvm/bin/clang'))},
        seconds=time.monotonic()-started))
    c.save(out / 'artifacts.json', c.inventory(out))
    return result


if __name__ == '__main__':
    out = Path(sys.argv[1]).resolve()
    with storage.lease([out]):
        run(out)
