"""One ordered producer; packets supply sources and append witness files."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent


def run(out, product, witnesses, inputs):
    c = product.c
    out.mkdir(parents=True, exist_ok=True)
    bodies = product.sources()
    pins = {n: hashlib.sha256(b.encode()).hexdigest() for n, b in bodies.items()}
    c.save(out / 'identity.json', dict(source_identity=pins))
    c.save(out / 'proposal-inputs.json', inputs)
    kernel = out / 'dx86cl64'
    shutil.copyfile(c.KERNEL, kernel); kernel.chmod(0o755)
    (out / 'packages.lisp').write_text('\n'.join(p.read_text() for p in witnesses))
    for filename, source in [('array-boundary.lisp', 'level-0/WASM32/w32-lap.lisp'),
                             ('bignum-boundary.lisp', 'level-0/l0-bignum32.lisp')]:
        (out / filename).write_text(bodies[source])
    with tempfile.TemporaryDirectory(prefix='u1-', dir=out) as tmp:
        source = Path(tmp)
        for name in ('source.tar', 'bootstrap.tar.gz'):
            with tarfile.open(c.STORE / 'macos-u1-inputs' / name) as archive:
                archive.extractall(source, filter='data')
        for name, body in bodies.items():
            path = source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(body)
        env = dict(os.environ, CCL_DEFAULT_DIRECTORY=str(source) + '/',
                   LOADER_OUTPUT=str(out) + '/', LOADER_SOURCE=str(out) + '/')
        prefix = [kernel, '-I', c.IMAGE, '--no-init', '--batch', '--eval',
            '(ccl::in-development-mode (load "ccl:lib;systems.lisp") '
            '(load "ccl:lib;compile-ccl.lisp") (load "ccl:xdump;faslenv.lisp") '
            '(load (compile-file "ccl:lib;nfcomp.lisp" :output-file "' + str(out / 'nfcomp.dx64fsl') + '")))',
            '--load', HERE.parent / 'registration/load.lisp']
        def invoke(driver, log):
            c.command(prefix + ['--load', driver], out / log, env, cwd=source, timeout=600)
        invoke(HERE / 'ordered.lisp', 'ordered.log')
        invoke(HERE.parent / 'loader-level0/prefix.lisp', 'prefix.log')
        ordered, target = c.read(out / 'ordered.json'), c.read(out / 'prefix.json')
        assert target['stop'] is None
        completed = target['compiled'] + [r for r in ordered['attempts'] if r.get('fasl') and not r['failure']]
        fixture = source / 'tests/wasm/stage1/loader-level0'
        fixture.mkdir(parents=True, exist_ok=True)
        for name in ('package-first.lisp', 'package-second.lisp'):
            shutil.copyfile(HERE.parent / 'loader-level0' / name, fixture / name)
        invoke(HERE / 'support.lisp', 'support.log')
        shutil.copyfile(fixture / 'package-support.lisp', out / 'package-support.source.lisp')
        # Do not rely on sources, an instrumented boot image, or the producer's heap.
        fasls = []
        for row in completed:
            assert row['fasl'] and not row['failure']
            name = Path(row['fasl']).name
            shutil.copyfile(source / row['fasl'], out / name)
            (source / row['file']).unlink()
            fasls.append(name)
        for name in ('package-support', 'package-first', 'package-second'):
            (fixture / (name + '.lisp')).unlink()
            fasls.append(name + '.w32fsl')
        (out / 'load-order.lisp').write_text('(' + ' '.join(json.dumps(x) for x in fasls) + ')\n')
        invoke(HERE / 'load.lisp', 'load.log')
        assert 'PREFIX-CROSS-LOAD-PASS' in (out / 'load.log').read_text()
        c.save(out / 'whole-file.json', dict(whole_file=[len(completed), len(completed), 0],
            files=completed, sources_removed=True, stop=ordered['stop']))
    return c.read(out / 'whole-file.json')
