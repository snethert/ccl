"""Compare a Git-free, different-root rebuild with the development execution."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import tarfile
import product
import storage

c = product.c


def run(work, original):
    tree, out = work / 'ccl', work / 'run'
    with storage.lease([work]):
        assert not tree.exists() and not out.exists()
        tree.mkdir()
        # Git only assembles the source copy. Neither reproduced command uses it.
        archive = work / 'source.tar'
        with archive.open('wb') as stream:
            subprocess.run(['git', 'archive', 'HEAD'], cwd=c.ROOT, stdout=stream, check=True)
        with tarfile.open(archive) as stream: stream.extractall(tree, filter='data')
        archive.unlink()
        for folder in ('loader-chain', 'loader-fasl'):
            shutil.copytree(product.HERE.parent / folder, tree / 'tests/wasm/stage1' / folder,
                            dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
        (work / 'ccl-evidence').symlink_to(c.STORE, target_is_directory=True)
        assert not (tree / '.git').exists()
    for script in ('run.py', 'exercise.py'):
        c.command(['python3', tree / 'tests/wasm/stage1/loader-fasl' / script, out],
                  work / (script + '.log'), timeout=1200, cwd=tree)
    with storage.lease([work]):
        left, right = c.read(original / 'summary.json'), c.read(out / 'summary.json')
        for name in ('status', 'source_identity', 'runtime', 'native', 'runs', 'whole_file'):
            assert left[name] == right[name], name
        suffixes = ('.w32fsl', '.wat', '.wasm', '.bin')
        def artifacts(root):
            return {str(p.relative_to(root)): c.sha(p) for p in c.files(root)
                    if p.suffix in suffixes and p.name != 'nfcomp.dx64fsl'}
        before, after = artifacts(original), artifacts(out)
        assert before == after
        result = dict(status='PASS', source_identity=right['source_identity'],
                      whole_file=right['whole_file'], artifacts=len(after), digests=after,
                      git_free=True, different_root=True)
        c.save(work / 'replay.json', result)
        print({k: v for k, v in result.items() if k not in ('digests', 'source_identity')})
        # Keep the final run until packet retention verifies and removes it.
        shutil.rmtree(tree)
        (work / 'ccl-evidence').unlink()
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('work', type=Path)
    parser.add_argument('original', type=Path)
    args = parser.parse_args()
    run(args.work.resolve(), args.original.resolve())
