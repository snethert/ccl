"""Replay from a Git-free source snapshot at a different absolute path."""
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


def artifacts(root):
    paths = [root / 'l0-aprims.w32fsl', root / 'package-support.w32fsl',
             root / 'package-first.w32fsl', root / 'package-second.w32fsl']
    paths += list((root / 'inputs').glob('*.w32fsl'))
    paths += [p for p in c.files(root / 'prefix')
              if p.suffix in ('.bin', '.wasm', '.json', '.wat')]
    return {str(p.relative_to(root)): c.sha(p) for p in sorted(paths)}


def run(out, original):
    out.mkdir(parents=True, exist_ok=True)
    checkout = out / 'checkout'
    checkout.mkdir()
    archive = out / 'source.tar'
    with archive.open('wb') as stream:
        subprocess.run(['git', '-C', str(c.ROOT), 'archive', 'HEAD'], stdout=stream, check=True)
    with tarfile.open(archive) as stream:
        stream.extractall(checkout, filter='data')
    archive.unlink()
    shutil.copytree(HERE, checkout / HERE.relative_to(c.ROOT), dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__'))
    (out / 'ccl-evidence').symlink_to(c.STORE, target_is_directory=True)
    assert not (checkout / '.git').exists()
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    # Child drivers acquire their own workspace lease. Use a separate packet
    # root so they never contend with this parent's retained source snapshot.
    produced = out.parents[1] / (out.parent.name + '-execution') / 'run'
    for name in ('run', 'exercise'):
        c.command([sys.executable, checkout / HERE.relative_to(c.ROOT) / (name + '.py'), produced],
                  out / (name + '.log'), env, cwd=checkout, timeout=600)
    before, after = artifacts(original), artifacts(produced)
    assert before == after, {n for n in before.keys() | after.keys() if before.get(n) != after.get(n)}
    a, b = c.read(original / 'summary.json'), c.read(produced / 'summary.json')
    assert a == b, 'execution differs'
    c.save(out / 'summary.json', dict(status='PASS', git_free=True, different_root=True,
        source_identity=a['source_identity'], compared=len(before), artifacts=before,
        executions_equal=True, ordered_equal=c.read(original / 'ordered.json') == c.read(produced / 'ordered.json')))
    print(dict(status='PASS', compared=len(before)))


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1]), Path(sys.argv[2])]):
        run(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
