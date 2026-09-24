"""R6/R6a on the exact integrated READY compiler, arch and level-0 sources in a pristine U1 tree."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys
import time
from check import ROOT, PACKET_SHA, reviewed, sha

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'bootstrap-validation'))
import common as c
import storage


def run(out):
    started = time.monotonic()
    packet, identity, bound = reviewed(c.STORE)
    spec = importlib.util.spec_from_file_location(
        'ready_integration_native', HERE.parent / 'bootstrap-generic-dispatch/native.py')
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    driver = native.driver
    for pair in [('level-1/l1-readloop.lisp','l1-fasls/l1-readloop.dx64fsl'),
                 ('level-0/l0-aprims.lisp','level-0/l0-aprims.dx64fsl'),
                 ('level-0/l0-misc.lisp','level-0/l0-misc.dx64fsl')]:
        if pair not in driver.SOURCE_PAIRS:
            driver.SOURCE_PAIRS.append(pair)
    driver.EXPECTED = ['bin/systems.dx64fsl', 'bin/compile-ccl.dx64fsl'] + [p[1] for p in driver.SOURCE_PAIRS]

    def proposal(source, target):
        target.mkdir(parents=True)
        manifest = dict(source_revision='c994217adc56b3f8a564526cee4695893ac84d86',
                        added=[], modified=[])
        for name, digest in identity.items():
            assert sha(ROOT / name) == digest, name
            path = target / 'files' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
            if (source / name).exists():
                manifest['modified'].append(dict(path=name, before=sha(source / name), after=digest))
            else:
                manifest['added'].append(dict(path=name, sha256=digest))
        (target / 'unit.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        return manifest

    driver.proposal = proposal
    out.mkdir(parents=True)
    c.save(out / 'proposal-identity.json', identity)
    status = driver.run(c.STORE / 'macos-u1-inputs', c.KERNEL, out / 'work',
                        out / 'results', c.STORE / '2026-09-16-stage1-1a-r2/native')
    assert status == 0
    # O-63: this envelope, rather than the reusable native run alone, binds
    # the actual integrated sources to the native qualification result.
    c.save(out / 'qualification.json', dict(status='PASS', packet_sha256=PACKET_SHA,
           source_identity=identity, source_identity_sha256=sha(out / 'proposal-identity.json'),
           native_run_sha256=sha(out / 'results/run.json'), native_rebuilt=True,
           seconds=time.monotonic() - started))
    return status


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sys.setrecursionlimit(10000)
    with storage.lease([args.output]):
        raise SystemExit(run(args.output))
