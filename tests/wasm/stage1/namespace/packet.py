#!/usr/bin/env python3
"""Retain or replay the namespace provider without copying compilation sessions."""
from pathlib import Path
import argparse
import json
import shutil
import sys
from run import c, storage, run, HERE, execution_inputs

RECORDS = ('native.json', 'namespace.json', 'mailbox.json', 'foreign-types.json', 'controls.json')


def pins():
    paths = list(c.files(HERE))
    for directory in ('integrated-runtime', 'runtime-boundary'):
        paths += c.files(c.ROOT / 'tests/wasm/stage0' / directory)
    paths += [c.ROOT / name for name in (
        'runtime/wasm32/sha256.mjs', 'runtime/wasm32/bytes.mjs',
        'tests/wasm/stage1/bootstrap-validation/common.py',
        'tests/wasm/stage1/bootstrap-validation/storage.py',
        'lib/foreign-types.lisp', 'lib/db-io.lisp', 'level-0/l0-io.lisp',
        'level-1/l1-files.lisp', 'level-1/linux-files.lisp',
        'compiler/WASM32/wasm32-backend.lisp')]
    return {str(p.relative_to(c.ROOT)): c.sha(p) for p in sorted(set(paths))}


def binaries(out):
    return {str(p.relative_to(out / 'transport')): c.sha(p)
            for p in sorted((out / 'transport').rglob('*.wasm'))}


def retain(out, packet):
    summary = c.read(out / 'summary.json')
    assert summary['status'] == 'PASS'
    assert summary['implementation'] == c.sha(HERE / 'namespace.mjs')
    assert summary['execution_inputs'] == execution_inputs()
    packet.mkdir()
    for name in (*RECORDS, 'summary.json', 'requests.json'):
        shutil.copyfile(out / name, packet / name)
    shutil.copytree(HERE, packet / 'source', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(out / 'controls', packet / 'controls')
    # No session archive, temporary native filesystem or regenerable D5 binaries.
    for name in ('versions.json', 'build-commands.json'):
        if (out / 'transport' / name).exists():
            shutil.copyfile(out / 'transport' / name, packet / name)
    for p in out.glob('*.log'):
        shutil.copyfile(p, packet / p.name)
    if (out / 'development').exists():
        shutil.copytree(out / 'development', packet / 'development')
    c.save(packet / 'binaries.json', binaries(out))
    c.save(packet / 'pins.json', pins())
    c.save(packet / 'packet.json', dict(id='STAGE1-NAMESPACE-PROVIDER-R1',
                files=c.inventory(packet), slot_credit=False))
    c.verify_files(packet, c.read(packet / 'packet.json')['files'])
    shutil.rmtree(storage.workspace(out))
    return dict(status='PASS', packet=str(packet), execution_during_retention=False,
                output_deleted=True)


def verify(packet, out):
    c.verify_files(packet, c.read(packet / 'packet.json')['files'])
    assert pins() == c.read(packet / 'pins.json'), 'source pins differ: use the recorded source commit'
    prior = c.read(packet / 'summary.json')
    for name, executable in [('kernel', c.KERNEL), ('image', c.IMAGE), ('node', c.NODE)]:
        assert c.sha(executable) == prior[name], name
    with storage.lease([out]):
        actual = run(out)
        assert {k: v for k, v in actual.items() if k != 'times'} == {k: v for k, v in prior.items() if k != 'times'}
        for name in RECORDS:
            assert c.read(out / name) == c.read(packet / name), name
        assert binaries(out) == c.read(packet / 'binaries.json')
        result = dict(status='PASS', native_comparisons=actual['native_comparisons'],
                      mailbox_cases=actual['mailbox_cases'], controls=actual['controls'],
                      times=actual['times'], new_execution=True, slot_credit=False)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['retain', 'verify'])
    parser.add_argument('packet', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    storage.gc()
    if args.command == 'retain':
        with storage.lease([args.output]):
            result = retain(args.output, args.packet)
    else:
        result = verify(args.packet, args.output)
    print(json.dumps(result, sort_keys=True))
