"""Rebuild the repair in a Git-free source tree at a different path."""
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import product
import storage

c = product.c


def run(work, original):
    tree, out = work / 'ccl', work / 'run'
    with storage.lease([work]):
        assert not tree.exists() and not out.exists()
        tree.mkdir()
        archive = work / 'source.tar'
        with archive.open('wb') as stream:
            subprocess.run(['git', 'archive', 'HEAD'], cwd=c.ROOT, stdout=stream, check=True)
        with tarfile.open(archive) as stream: stream.extractall(tree, filter='data')
        archive.unlink()
        for folder in ('loader-chain', 'loader-gc', 'bootstrap-validation'):
            shutil.copytree(product.HERE.parent / folder, tree / 'tests/wasm/stage1' / folder,
                            dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
        (work / 'ccl-evidence').symlink_to(c.STORE, target_is_directory=True)
        assert not (tree / '.git').exists()
    for script in ('run.py', 'exercise.py'):
        c.command(['python3', tree / 'tests/wasm/stage1/loader-gc' / script, out],
                  work / (script + '.log'), timeout=1200, cwd=tree)
    with storage.lease([work]):
        left, right = c.read(original / 'summary.json'), c.read(out / 'summary.json')
        for name in ('status', 'source_identity', 'runtime', 'native', 'runs', 'whole_file', 'ordered', 'artifacts'):
            assert left[name] == right[name], name
        def artifacts(root):
            return {str(p.relative_to(root)): c.sha(p) for p in c.files(root)
                    if p.suffix in ('.w32fsl', '.wat', '.wasm', '.bin', '.dx64fsl', '.image') or p.name == 'dx86cl64'}
        before, after = artifacts(original), artifacts(out)
        assert before == after
        result = dict(status='PASS', source_identity=right['source_identity'],
                      runtime=right['runtime'], whole_file=right['whole_file'],
                      artifacts=len(after), digests=after, git_free=True, different_root=True)
        c.save(work / 'replay.json', result)
        print({k: v for k, v in result.items() if k not in ('digests', 'source_identity')})
        shutil.rmtree(tree)
        (work / 'ccl-evidence').unlink()


if __name__ == '__main__':
    run(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
