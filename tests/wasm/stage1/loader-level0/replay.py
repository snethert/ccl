"""Reproduce the producer and target checks in a differently located Git-free tree."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tarfile
import product
import storage

HERE = Path(__file__).resolve().parent
c = product.c


def run(out, first):
    out.mkdir(parents=True)
    checkout = out / 'archive/ccl'
    checkout.mkdir(parents=True)
    archive = out / 'source.tar'
    with archive.open('wb') as stream:
        subprocess.run(['git', 'archive', 'HEAD'], cwd=c.ROOT, stdout=stream, check=True)
    with tarfile.open(archive) as source:
        source.extractall(checkout, filter='data')
    archive.unlink()
    target = checkout / 'tests/wasm/stage1/loader-level0'
    shutil.copytree(HERE, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copyfile(HERE.parent / 'loader/d2.mjs', target.parent / 'loader/d2.mjs')
    (checkout.parent / 'ccl-evidence').symlink_to(c.STORE, target_is_directory=True)
    env = dict(os.environ)
    for key in ('GIT_DIR', 'GIT_WORK_TREE'):
        env.pop(key, None)
    env['GIT_CEILING_DIRECTORIES'] = str(out)
    assert not (checkout / '.git').exists()
    c.command([sys.executable, '-c',
               'import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
               'import run,exercise; out=Path(sys.argv[2]); run.run(out); exercise.run(out)',
               target, out / 'execution'], out / 'replay.log', env, checkout, timeout=1800)
    paths = list(first.glob('*.w32fsl')) + list((first / 'inputs').iterdir())
    for label in ('prefix', 'keywords'):
        paths += [p for p in c.files(first / label) if p.suffix in ('.json', '.bin', '.wasm', '.wat')]
    identities = {}
    for path in paths:
        name = path.relative_to(first)
        assert path.read_bytes() == (out / 'execution' / name).read_bytes(), name
        identities[str(name)] = c.sha(path)
    a, b = (c.read(p / 'summary.json') for p in (first, out / 'execution'))
    assert a == b, 'execution, stops, controls or source identity changed'
    c.save(out / 'summary.json', dict(status='PASS', gitless=True, artifacts=identities,
                                     source_identity=a['source_identity'], observations_equal=True))
    print('GIT-FREE-REPLAY-PASS', len(identities))


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
