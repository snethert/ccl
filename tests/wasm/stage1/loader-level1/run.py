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


def run(out, resume=False):
    assert resume or not out.exists(), 'use a fresh output directory'
    started = time.monotonic()
    pins = inputs()
    build_pins = pins
    written = None
    if resume:
        build_pins = c.read(out / 'proposal-inputs.json')
        changed = {n for n in set(pins) | set(build_pins) if pins.get(n) != build_pins.get(n)}
        assert changed <= {'tests/wasm/stage1/loader-level1/run.py',
                           'tests/wasm/stage1/loader-chain/exercise.py',
                           'tests/wasm/stage1/loader-level1/weak-collector-cases.mjs'}, changed
        written = c.read(out / 'write.log')
        c.save(out / 'execution-inputs.json', pins)
        c.save(out / 'build-reuse.json', dict(changed_harness_inputs=sorted(changed),
            original_inputs=c.sha(out / 'proposal-inputs.json'),
            execution_inputs=c.sha(out / 'execution-inputs.json'), materialization=written))
    witnesses = config.witnesses() + [HERE.parent / 'loader-fasl/witnesses/fasl.lisp']
    witnesses += sorted((HERE.parent / 'loader-gc/witnesses').glob('*.lisp'))
    witnesses += [HERE / 'witnesses.lisp', HERE / 'weak-witnesses.lisp']
    cases = config.cases(product) + c.read(HERE.parent / 'loader-fasl/cases.json') + [
        dict(id='gc-fresh', call=['CCL', 'LOADER-GC-FRESH'], args=[]),
        dict(id='gc-constructor-flags', call=['CCL', 'LOADER-GC-CONSTRUCTOR-FLAGS'], args=[])]
    cases += [dict(id='level1-' + name, call=['CCL', 'LOADER-LEVEL1-' + name.upper()], args=[])
              for name in ('namespace-tables', 'platform', 'metrics', 'metadata', 'plist', 'keyword', 'sets',
                           'setter', 'seed-zero', 'seed-high', 'seed-max', 'seed-refusals', 'seed-collect',
                           'random-state', 'random-fresh', 'random-bounds',
                           'local-special', 'local-functions', 'sort', 'sort-key')]
    cases += [dict(id='weak-%d-%d' % (kind, retain),
                   call=['CCL', 'LOADER-WEAK-RESULT'], args=[kind, retain],
                   beforeCollect=dict(call=['CCL', 'LOADER-WEAK-PREPARE'], args=[kind, retain]))
              for kind in range(4) for retain in range(2)]
    cases += [dict(id='weak-types', call=['CCL', 'LOADER-WEAK-TYPES'], args=[])]
    cases += [dict(id='weak-operations-%d' % kind, call=['CCL', 'LOADER-WEAK-OPERATIONS'], args=[kind])
              for kind in range(4)]
    controls = [HERE.parent / n for n in ('loader-hash/controls/buffers.mjs', 'loader-fasl/controls/fasl.mjs')]
    controls += sorted((HERE.parent / 'loader-gc/controls').glob('*.mjs'))
    startup = c.read(HERE.parent / 'loader-fasl/startup-refusals.json')
    startup[2] = {**startup[2], 'name': 'force-export packages need callable STRING=',
                  'unbound': [['COMMON-LISP', 'STRING=']]}
    # Callable EQL now permits the package-reference table and its registration.
    startup = startup[2:]
    startup.append(dict(name='TYPE-OF alias needs callable %TYPE-OF',
        symbols=[['CCL', '%FHAVE'], ['CCL', '%TYPE-OF']],
        unbound=[['CCL', '%TYPE-OF']], reason='checked 10'))
    for variable in ('*TOTAL-GC-MICROSECONDS*', '*TOTAL-BYTES-FREED*'):
        startup.append(dict(name=variable + ' pointer-function registration is not ready',
            symbols=[['CCL', '*LISP-SYSTEM-POINTER-FUNCTIONS*'], ['COMMON-LISP', 'MEMBER']],
            childSymbols=[['CCL', variable]], reason='checked 10'))
    if not resume:
        product.module('level1_build', HERE.parent / 'loader-chain/build.py').run(
          out, product, witnesses, pins, checks=[HERE.parent / 'loader-fasl/scratch.lisp', HERE / 'cold-eval.lisp'],
          level1=True, preflights=[HERE / 'dispatch.lisp'], crossload_stop=None,
          extra_files=[HERE / 'setter-second.lisp'],
          execution_files=lambda name: name.startswith('level-0/') or name in
              ('level-1/l1-utils.lisp', 'level-1/l1-numbers.lisp', 'level-1/l1-sort.lisp'),
          support_forms=['("ccl:level-1;WASM32;w32-files.lisp" defun %wasm-namespace-support-initialize)',
                         '("ccl:lib;hash.lisp" defun hash-table-weak-p next-hash-table-iteration-1 maphash)',
                         '("ccl:level-1;l1-aprims.lisp" defun setf-function-name existing-setf-function-name maybe-setf-name nthcdr)',
                         '("ccl:level-1;l1-boot-1.lisp" defun host-platform)',
                         '("ccl:level-1;l1-init.lisp" defloadvar *total-gc-microseconds* *total-bytes-freed*)'])
    result = product.module('level1_exercise', HERE.parent / 'loader-chain/exercise.py').run(
        out, product, cases, witnesses + [HERE / 'setter-second.lisp'], controls, build_pins,
        startup,
        {**c.read(HERE.parent / 'loader-hash/pending-cases.json'),
         **c.read(HERE.parent / 'loader-fasl/pending-cases.json'),
         'level1-seed-refusals': 'The execution prefix has not initialized the condition system; '
             'checked 10 precedes the Lisp ERROR/TYPE-ERROR handlers. No native-match credit.'},
        written=written)
    dispatch = c.read(out / 'dispatch.json')
    assert dispatch['status'] == 'PASS' and len(dispatch['rows']) == 18
    assert all(r['dispatch'] and r['unchanged_input_skipped'] for r in dispatch['rows'])
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
        run(out, resume='--resume' in sys.argv[2:])
