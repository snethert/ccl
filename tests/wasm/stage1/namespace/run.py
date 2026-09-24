#!/usr/bin/env python3
"""Build and exercise the isolated namespace, with native byte/path comparisons."""
from pathlib import Path
import argparse
import json
import os
import shutil
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'bootstrap-validation'))
import common as c
import storage


def lisp(value):
    if isinstance(value, list):
        return '(' + ' '.join(map(lisp, value)) + ')'
    if isinstance(value, str):
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return str(value)


def execution_inputs():
    paths = [p for p in c.files(HERE) if p.suffix in ('.py', '.mjs', '.lisp')]
    for directory in ('integrated-runtime', 'runtime-boundary'):
        paths += c.files(c.ROOT / 'tests/wasm/stage0' / directory)
    paths += [c.ROOT / 'runtime/wasm32' / name for name in ('sha256.mjs', 'bytes.mjs')]
    paths += [HERE.parent / 'bootstrap-validation' / name for name in ('common.py', 'storage.py')]
    return {str(p.relative_to(c.ROOT)): c.sha(p) for p in sorted(set(paths))}


def run(out):
    if (out / 'summary.json').exists():
        raise ValueError('Do not overwrite a completed run')
    out.mkdir(parents=True, exist_ok=True)
    times = {}
    inputs = execution_inputs()
    (out / 'runtime').mkdir(exist_ok=True)
    shutil.copyfile(HERE / 'namespace.mjs', out / 'runtime/namespace.mjs')
    for name in ('sha256.mjs', 'bytes.mjs'):
        shutil.copyfile(c.ROOT / 'runtime/wasm32' / name, out / 'runtime' / name)
    c.command([c.NODE, HERE / 'prepare.mjs', out], out / 'prepare.log')
    (out / 'requests.lisp').write_text(lisp(c.read(out / 'requests.json')) + '\n')
    kernel = out / 'dx86cl64'
    shutil.copyfile(c.KERNEL, kernel)
    kernel.chmod(0o755)
    env = dict(os.environ, CCL_DEFAULT_DIRECTORY=str(c.ROOT) + '/',
               NAMESPACE_ROOT=str(out / 'native-tree'),
               NAMESPACE_REQUESTS=str(out / 'requests.lisp'),
               NAMESPACE_RESULTS=str(out / 'native.json'),
               NAMESPACE_FTD_RESULTS=str(out / 'foreign-types.json'))
    times['native'] = c.command([kernel, '--image-name', c.IMAGE, '--no-init', '--batch',
                                 '--load', HERE / 'native.lisp'], out / 'native.log', env, timeout=60)
    times['foreign_types'] = c.command([kernel, '--image-name', c.IMAGE, '--no-init', '--batch',
                                        '--load', HERE / 'foreign-types.lisp'], out / 'foreign-types.log', env, timeout=60)
    times['mailbox'] = c.command([c.NODE, HERE / 'mailbox.mjs', out], out / 'mailbox.log', timeout=90)
    times['provider'] = c.command([c.NODE, HERE / 'check.mjs', out], out / 'provider.log', timeout=60)
    from provider_controls import run as controls
    started = time.monotonic()
    faults = controls(out)
    times['faults'] = time.monotonic() - started
    record = c.read(out / 'namespace.json')
    assert execution_inputs() == inputs, 'input changed during execution'
    c.save(out / 'summary.json', dict(status='PASS', execution_inputs=inputs, native_comparisons=record['native_comparisons'],
            controls=len(record['checks']), faults=len(faults), mailbox_cases=len(c.read(out / 'mailbox.json')['rows']),
            foreign_types=c.read(out / 'foreign-types.json'), namespace_identity=record['identity'],
            times=times, kernel=c.sha(c.KERNEL), image=c.sha(c.IMAGE), node=c.sha(c.NODE),
            implementation=c.sha(HERE / 'namespace.mjs'), generated_lisp=False,
            slot_credit=False, files_loaded_on_target=0))
    kernel.unlink()
    return c.read(out / 'summary.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    storage.gc()
    with storage.lease([args.output]):
        print(json.dumps(run(args.output), sort_keys=True))
