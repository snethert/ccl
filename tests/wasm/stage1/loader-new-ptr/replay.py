"""Rebuild and execute from a Git-free extraction at a different path."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tarfile
import product

c = product.c


def run(out, original):
    out.mkdir(parents=True, exist_ok=True)
    tree, archive = out / 'tree', out / 'source.tar'
    with archive.open('wb') as stream:
        subprocess.run(['git', '-C', str(c.ROOT), 'archive', 'e2de2fd9'], stdout=stream, check=True)
    tree.mkdir()
    with tarfile.open(archive) as stream:
        stream.extractall(tree, filter='data')
    shutil.copytree(product.HERE, tree / 'tests/wasm/stage1/loader-new-ptr',
                    ignore=shutil.ignore_patterns('__pycache__'))
    (out / 'ccl-evidence').symlink_to(c.STORE, target_is_directory=True)
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    execution = out / 'execution'
    for name in ('run', 'exercise'):
        c.command([sys.executable, tree / 'tests/wasm/stage1/loader-new-ptr' / (name + '.py'), execution],
                  out / (name + '.log'), env, cwd=tree, timeout=900)
    result = c.read(execution / 'summary.json')
    assert result == c.read(original / 'summary.json')
    assert c.read(execution / 'proposal-inputs.json') == c.read(original / 'proposal-inputs.json')
    assert c.read(execution / 'literal-controls.json') == c.read(original / 'literal-controls.json')
    artifacts = {}
    for path in c.files(original):
        name = path.relative_to(original)
        if path.suffix in ('.w32fsl', '.bin', '.wat', '.wasm'):
            assert c.sha(path) == c.sha(execution / name), str(name)
            artifacts[str(name)] = c.sha(path)
    report = dict(status='PASS', source_identity=result['source_identity'],
                  source_archive=c.sha(archive), git_free=True, different_root=True,
                  artifacts=artifacts, drivers=c.read(execution / 'proposal-inputs.json'))
    c.save(out / 'summary.json', report)
    shutil.rmtree(tree)
    archive.unlink()
    (out / 'ccl-evidence').unlink()
    print(dict(status='PASS', artifacts=len(artifacts)))
    return report


if __name__ == '__main__':
    run(*(Path(p).resolve() for p in sys.argv[1:]))
