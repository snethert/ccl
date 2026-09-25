"""Observe the actual ordered level-0 entry point in a disposable U1 tree."""
from pathlib import Path
import hashlib
import os
import shutil
import sys
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'loader'))
import proposal
import common as c
import storage
import product as unit


def run(out, baseline=False):
    out.mkdir(parents=True, exist_ok=True)
    bodies = proposal.sources() if baseline else unit.sources()
    c.save(out / 'identity.json', dict(
        source_identity={n: hashlib.sha256(b.encode()).hexdigest() for n, b in bodies.items()},
        kernel=c.sha(c.KERNEL), image=c.sha(c.IMAGE),
        drivers={str(p.relative_to(HERE)): c.sha(p) for p in c.files(HERE)
                 if '__pycache__' not in p.parts and p.suffix in ('.py', '.lisp', '.json', '.mjs')},
        packaging={n: c.sha(HERE.parent / 'loader' / n) for n in ('write.mjs', 'd2.mjs')}))
    kernel = out / 'dx86cl64'
    shutil.copyfile(c.KERNEL, kernel)
    kernel.chmod(0o755)
    with tempfile.TemporaryDirectory(prefix='u1-', dir=out) as temp:
        source = Path(temp)
        inputs = c.STORE / 'macos-u1-inputs'
        pins = c.read(inputs / 'pins.json')['inputs']
        for name in ('source.tar', 'bootstrap.tar.gz'):
            assert c.sha(inputs / name) == pins[name]
            with tarfile.open(inputs / name) as archive:
                archive.extractall(source, filter='data')
        for name, body in bodies.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
        env = dict(os.environ, CCL_DEFAULT_DIRECTORY=str(source) + '/',
                   LOADER_OUTPUT=str(out) + '/', LOADER_SOURCE=str(HERE) + '/')
        prefix = [kernel, '-I', c.IMAGE, '--no-init', '--batch', '--eval',
                  '(ccl::in-development-mode (load "ccl:lib;systems.lisp") '
                  '(load "ccl:lib;compile-ccl.lisp") (load "ccl:xdump;faslenv.lisp") '
                  '(load (compile-file "ccl:lib;nfcomp.lisp" :output-file "' +
                  str(out / 'nfcomp.dx64fsl') + '")))', '--load',
                  HERE.parent / 'registration/load.lisp']
        c.command(prefix + ['--load', HERE / 'ordered.lisp'], out / 'ordered.log',
                  env, cwd=source, timeout=600)
        assert 'ORDERED-OBSERVATION-COMPLETE' in (out / 'ordered.log').read_text()
        c.command(prefix + ['--load', HERE / 'prefix.lisp'], out / 'prefix.log',
                  env, cwd=source, timeout=600)
        assert 'PREFIX-OBSERVATION-COMPLETE' in (out / 'prefix.log').read_text()
        c.save(out / 'upstream.json', pins)
        result = c.read(out / 'prefix.json')
        if not baseline:
            assert result['stop'] is None, result
            (out / 'inputs').mkdir()
            fasls = {}
            for row in result['compiled']:
                assert row['fasl'] and not row['failure'], row
                path = source / row['fasl']
                shutil.copyfile(path, out / 'inputs' / path.name)
                fasls[path.name] = c.sha(path)
                (source / row['file']).unlink()
            c.save(out / 'fasls.json', fasls)
            fixture_dir = source / 'tests/wasm/stage1/loader-level0'
            fixture_dir.mkdir(parents=True, exist_ok=True)
            for name in ('package-first.lisp', 'package-second.lisp'):
                shutil.copyfile(HERE / name, fixture_dir / name)
            c.command(prefix + ['--load', HERE / 'packages-produce.lisp'], out / 'packages-produce.log',
                      env, cwd=source, timeout=600)
            for name in ('package-first.lisp', 'package-second.lisp'):
                (fixture_dir / name).unlink()
            shutil.copyfile(fixture_dir / 'package-support.lisp', out / 'package-support.source.lisp')
            (fixture_dir / 'package-support.lisp').unlink()
            c.command(prefix + ['--load', HERE / 'load-prefix.lisp'], out / 'load.log',
                      env, cwd=source, timeout=600)
            assert 'PREFIX-CROSS-LOAD-PASS' in (out / 'load.log').read_text()
            fixture = source / 'tests/wasm/stage1/loader-level0/keywords.lisp'
            fixture.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(HERE / 'keywords.lisp', fixture)
            c.command(prefix + ['--load', HERE / 'keywords-produce.lisp'],
                      out / 'keywords-produce.log', env, cwd=source, timeout=600)
            assert 'KEYWORD-FASLS-PASS' in (out / 'keywords-produce.log').read_text()
            fixture.unlink()
            c.command(prefix + ['--load', HERE / 'keywords-load.lisp'],
                      out / 'keywords-load.log', env, cwd=source, timeout=600)
            assert 'KEYWORD-CROSS-LOAD-PASS' in (out / 'keywords-load.log').read_text()
            for row in c.read(out / 'keyword-controls.json')['rows']:
                assert not (out / ('refused-' + row['name'])).exists()
    print((out / 'ordered.json').read_text())
    print((out / 'prefix.json').read_text())


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve(), '--baseline' in sys.argv)
