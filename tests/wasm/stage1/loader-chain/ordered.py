"""Stop-preserving ordered compilation in an isolated pristine U1 tree."""
from pathlib import Path
import hashlib
import os
import shutil
import sys
import tarfile
import tempfile
import storage

HERE = Path(__file__).resolve().parent


def run(out, product, level1=False):
    c = product.c
    out.mkdir(parents=True, exist_ok=True)
    bodies = product.sources()
    c.save(out / 'identity.json', {n: hashlib.sha256(b.encode()).hexdigest() for n, b in bodies.items()})
    kernel = out / 'dx86cl64'
    shutil.copyfile(c.KERNEL, kernel)
    kernel.chmod(0o755)
    with tempfile.TemporaryDirectory(prefix='u1-', dir=out) as tmp:
        source = Path(tmp)
        for name in ('source.tar', 'bootstrap.tar.gz'):
            with tarfile.open(c.STORE / 'macos-u1-inputs' / name) as archive:
                archive.extractall(source, filter='data')
        for name, body in bodies.items():
            p = source / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body)
        env = dict(os.environ, CCL_DEFAULT_DIRECTORY=str(source) + '/',
                   LOADER_OUTPUT=str(out) + '/', LOADER_SOURCE=str(HERE) + '/')
        if level1:
            if level1 == 'only':
                env['LOADER_LEVEL_1'] = 'only'
        command = [kernel, '-I', c.IMAGE, '--no-init', '--batch', '--eval',
                   '(ccl::in-development-mode (load "ccl:lib;systems.lisp") '
                   '(load "ccl:lib;compile-ccl.lisp") (load "ccl:xdump;faslenv.lisp") '
                   '(load (compile-file "ccl:lib;nfcomp.lisp" :output-file "' +
                   str(out / 'nfcomp.dx64fsl') + '")))', '--load',
                   HERE.parent / 'registration/load.lisp', '--load', HERE / 'ordered.lisp']
        c.command(command, out / 'ordered.log', env, cwd=source, timeout=600)
        result = c.read(out / 'ordered.json')
        if level1 is True and result['stop'] is None:
            c.save(out / 'ordered-level0.json', result)
            env['LOADER_LEVEL_1'] = 'only'
            c.command(command, out / 'ordered-level1.log', env, cwd=source, timeout=600)
            second = c.read(out / 'ordered.json')
            c.save(out / 'ordered-level1.json', second)
            result = dict(attempts=result['attempts'] + second['attempts'],
                          stop=second['stop'], host_state_restored=bool(
                              result['host_state_restored'] and second['host_state_restored']))
            c.save(out / 'ordered.json', result)
        (out / 'fasls').mkdir()
        for row in result['attempts']:
            if row.get('fasl'):
                shutil.copyfile(source / row['fasl'], out / 'fasls' / Path(row['fasl']).name)
        print(result, flush=True)
    return result
