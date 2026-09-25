"""Replay integrated execution in a Git-free extraction at a different path."""
from pathlib import Path
import os
import importlib.util
import shutil
import subprocess
import sys
import tarfile
import check

spec = importlib.util.spec_from_file_location('stack_integration_run', check.HERE / 'run.py')
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)

c = check.c


def replay(out, original):
    tree, archive = out / 'tree', out / 'source.tar'
    with run.storage.lease([out]):
        out.mkdir(parents=True, exist_ok=True)
        with archive.open('wb') as stream:
            subprocess.run(['git', '-C', str(c.ROOT), 'archive', c.read(check.RECORD)['review']['commit']],
                           stdout=stream, check=True)
        tree.mkdir()
        with tarfile.open(archive) as stream:
            stream.extractall(tree, filter='data')
        # Overlay the complete bound input set, including integrated product and
        # final follow-up drivers, onto the reviewed source tree.
        names = set(run.drivers()) | set(check.check()['source_identity']) | set(check.check()['runtime_identity'])
        for name in names:
            target = tree / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(c.ROOT / name, target)
        (out / 'ccl-evidence').symlink_to(c.STORE, target_is_directory=True)
    execution = out / 'replay'
    env = {k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    c.command([sys.executable, tree / 'tests/wasm/stage1/loader-stack-acceptance/run.py', execution],
              out / 'run.log', env, cwd=tree, timeout=900)
    with run.storage.lease([out, original]):
        assert c.read(execution / 'integration.json') == c.read(original / 'integration.json')
        assert c.read(execution / 'execution/summary.json') == c.read(original / 'execution/summary.json')
        assert c.read(execution / 'finished.json') == c.read(original / 'finished.json')
        artifacts = {}
        for path in c.files(original):
            if path.suffix in ('.w32fsl', '.bin', '.wasm', '.wat'):
                name = str(path.relative_to(original))
                assert c.sha(path) == c.sha(execution / name), name
                artifacts[name] = c.sha(path)
        report = dict(status='PASS', git_free=True, different_root=True,
                      drivers=run.drivers(), source_archive=c.sha(archive), artifacts=artifacts)
        c.save(out / 'summary.json', report)
        shutil.rmtree(tree)
        archive.unlink()
        (out / 'ccl-evidence').unlink()
    print(dict(status='PASS', artifacts=len(artifacts)))


if __name__ == '__main__':
    replay(*(Path(p).resolve() for p in sys.argv[1:]))
