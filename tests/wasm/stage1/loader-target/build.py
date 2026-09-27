"""Compile a target bundle directly; never cross-load its level-1 inputs."""
from pathlib import Path
import importlib.util
import os
import shutil
import sys
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('target_product', HERE.parent / 'loader-level1/product.py')
product = importlib.util.module_from_spec(spec)
spec.loader.exec_module(product)
c = product.c


def runtime(out, reuse):
    paths = [p for p in (c.ROOT / 'runtime/wasm32').rglob('*')
             if p.suffix in ('.c', '.h', '.wat', '.py')]
    paths += [HERE.parent / 'loader/run.py', HERE.parent / 'loader-level1/product.py',
              Path('/usr/local/opt/llvm/bin/clang'), Path(c.WABT)]
    identity = {str(p.resolve()): c.sha(p) for p in paths}
    prior = Path(reuse) / 'runtime-binaries' if reuse else None
    if prior and (prior / 'build-identity.json').exists():
        saved = c.read(prior / 'build-identity.json')
        if saved['sources'] == identity:
            for name, digest in saved['binaries'].items():
                assert c.sha(prior / name) == digest, name
            shutil.copytree(prior, out)
            metadata = c.read(out / 'array-runtime.json')
            metadata['owner'] = c.sha(c.ROOT / 'runtime/wasm32/collector-owner.mjs')
            c.save(out / 'array-runtime.json', metadata)
            return
    product.runtime(out)
    c.save(out / 'build-identity.json', dict(sources=identity,
           binaries={p.name: c.sha(p) for p in out.glob('*.wasm')}))


def run(out, boot0=False, level1=False, reuse=None, modules=None, compile_only=False, postimage=None):
    if compile_only and not level1:
        raise ValueError('--compile-only requires --level1')
    out.mkdir(parents=True, exist_ok=True)
    kernel = out / 'dx86cl64'
    shutil.copyfile(c.KERNEL, kernel)
    kernel.chmod(0o755)
    with tempfile.TemporaryDirectory(prefix='source-', dir=out) as tmp:
        source = Path(tmp)
        for name in ('source.tar', 'bootstrap.tar.gz'):
            with tarfile.open(c.STORE / 'macos-u1-inputs' / name) as archive:
                archive.extractall(source, filter='data')
        bodies = product.sources()
        bodies['compiler/WASM32/wasm32-bundle.lisp'] = (c.ROOT / 'compiler/WASM32/wasm32-bundle.lisp').read_text()
        c.save(out / 'sources.json', {n: c.sha(c.ROOT / n) for n in bodies})
        for name, body in bodies.items():
            p = source / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body)
        fixture = source / HERE.relative_to(c.ROOT)
        fixture.mkdir(parents=True)
        shutil.copyfile(HERE / 'smoke.lisp', fixture / 'smoke.lisp')
        if postimage:
            # Bind an already materialized image before compiling this new file.
            c.save(out / 'postimage-parent.json', dict(
                image=str(postimage), manifest=c.sha(postimage / 'boot/artifacts/manifest.json'),
                sources={name: c.sha(HERE / name) for name in
                         ('postimage.lisp', 'instance-a.lisp', 'instance-b.lisp')}))
            for name in ('postimage.lisp', 'instance-a.lisp', 'instance-b.lisp'):
                shutil.copyfile(HERE / name, fixture / name)
        env = dict(os.environ, CCL_DEFAULT_DIRECTORY=str(source) + '/', LOADER_OUTPUT=str(out) + '/')
        if modules:
            env['LOADER_MODULES'] = '(' + ' '.join(modules.split(',')) + ')'
        prefix = [kernel, '-I', c.IMAGE, '--no-init', '--batch', '--eval',
            '(ccl::in-development-mode (load "ccl:lib;systems.lisp") '
            '(load "ccl:lib;compile-ccl.lisp") (load "ccl:xdump;faslenv.lisp") '
            '(load (compile-file "ccl:lib;nfcomp.lisp" :output-file "' + str(out / 'nfcomp.dx64fsl') + '")))',
            '--load', HERE.parent / 'registration/load.lisp']
        c.command(prefix + ['--load', HERE / ('postimage-compile.lisp' if postimage else 'bundles.lisp' if level1 else 'boot0.lisp' if boot0 else 'compile.lisp')],
                  out / 'compile.log', env, cwd=source, timeout=600)
    c.save(out / 'policy.json', c.read(c.STORE / '2026-09-20-stage1-materialization-r1/execution/policy.json'))
    c.save(out / 'versions.json', dict(abi=dict(name='B', version=1),
        layout=dict(version=1, sha256=c.sha(c.ROOT / 'doc/WASM/contracts/wasm32-layout.v1.json'))))
    shutil.copyfile(HERE.parent / 'loader/d2.mjs', out / 'd2.mjs')
    (out / 'runtime').symlink_to(c.ROOT / 'runtime/wasm32', target_is_directory=True)
    if level1 or postimage:
        if compile_only:
            print('Level-1 target compilation recorded:', out)
            return
        c.command([c.NODE, HERE / 'bundles.mjs', out, *([reuse] if reuse else []), *(['--v1'] if postimage else [])], out / 'materialize.log', timeout=1800)
        print('Level-1 target bundles materialized:', out)
        return
    if boot0:
        shutil.copyfile(HERE.parent / 'loader/write.mjs', out / 'write.mjs')
        c.command([c.NODE, HERE / 'materialize-boot.mjs', out, *([reuse] if reuse else [])],
                  out / 'materialize.log', timeout=600)
        runtime(out / 'runtime-binaries', reuse)
        c.command([c.WABT, '--enable-all', HERE / 'observe.wat', '-o', out / 'observe.wasm'], out / 'observer.log')
        c.command([c.WABT, '--enable-all', c.ROOT / 'runtime/wasm32/host-call-adapter.wat',
                   '-o', out / 'host-call-adapter.wasm'], out / 'host-adapter.log')
        print('Level-0 boot image materialized:', out)
        return
    c.command([c.NODE, HERE / 'materialize.mjs', out / 'records.json', out / 'smoke.w32fsl',
               out / 'modules', out / 'versions.json', out / 'policy.json', out / 'd2.mjs'], out / 'materialize.log')
    c.command([c.WABT, '--enable-all', c.ROOT / 'runtime/wasm32/target-code-adapter.wat',
               '-o', out / 'target-code-adapter.wasm'], out / 'adapter.log')
    print('Target reader and self-contained bundle compiled:', out)


if __name__ == '__main__':
    reuse = next((a.split('=', 1)[1] for a in sys.argv[2:] if a.startswith('--reuse=')), None)
    modules = next((a.split('=', 1)[1] for a in sys.argv[2:] if a.startswith('--modules=')), None)
    postimage = next((Path(a.split('=', 1)[1]).resolve() for a in sys.argv[2:] if a.startswith('--postimage=')), None)
    run(Path(sys.argv[1]).resolve(), '--boot0' in sys.argv[2:], '--level1' in sys.argv[2:], reuse, modules,
        '--compile-only' in sys.argv[2:], postimage)
