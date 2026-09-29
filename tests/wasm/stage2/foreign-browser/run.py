"""Execute the unchanged foreign Lisp witness through Node and browser providers."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT/'tests/wasm/stage1/bootstrap-validation'))
import common as c
import storage
spec = importlib.util.spec_from_file_location('foreign_api', HERE.parent/'foreign-api/run.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
command = api.command


def run(args):
    out = args.output.resolve()
    with storage.lease([out, args.boot, args.level1, args.checks]):
        storage.reset_run(out)
        execution_sources = list(HERE.glob('*.mjs')) + list(HERE.glob('*.py')) + [
            HERE.parent/'foreign-api'/name for name in ['run.py', 'extension.mjs', 'fixture.mjs', 'declaration.mjs', 'library.wat']
        ] + [ROOT/'tests/wasm/stage1/loader-target'/name for name in ['boot0.mjs', 'boot-worker.mjs']]
        source_identity = {str(p.relative_to(ROOT)): c.sha(p) for p in execution_sources}
        c.save(out/'execution-sources.json', source_identity)
        c.save(out/'tools.json', {name: dict(path=str(p), sha256=c.sha(p)) for name, p in [
            ('node', c.NODE), ('wat2wasm', c.WABT), ('python', Path(sys.executable))]})
        c.save(out/'browser-config.json', c.read(args.browser_config))
        source_paths = [ROOT/'runtime/wasm32/foreign-api.lisp'] + [
            HERE.parent/name/'checks.lisp' for name in
            ['foreign-api', 'foreign-finalizers', 'foreign-strings', 'foreign-lisp-callbacks']]
        combined = '\n'.join(p.read_text() for p in source_paths)
        import hashlib
        parent = c.read(args.checks/'postimage-parent.json')
        assert parent['source_sha256'] == hashlib.sha256(combined.encode()).hexdigest()
        assert parent['manifest'] == c.sha(args.boot/'boot/artifacts/manifest.json')
        # One retained native oracle for these exact Lisp inputs, reused by identity.
        previous = c.STORE/'2026-09-28-stage2-foreign-lisp-callbacks-r1'
        old_sources = c.read(previous/'final/sources.json')
        for p in source_paths:
            assert c.sha(p) == old_sources[str(p.relative_to(ROOT))]
        native = previous/'final/native.log'
        assert c.sha(native) == c.read(previous/'inventory.json')['final/native.log']
        c.save(out/'native-reference.json', dict(path=str(native), sha256=c.sha(native),
            sources={str(p.relative_to(ROOT)): c.sha(p) for p in source_paths}))
        c.save(out/'build-inputs.json', {str(p): dict(sha256=c.sha(p), recipe=c.read(p.parent/'build-recipe.json'))
            for p in [args.boot/'sources.json', args.level1/'sources.json', args.checks/'sources.json']})
        try:
            command([c.NODE, HERE/'numeric-node.mjs', args.boot/'runtime-binaries', out/'numeric-node.json'], out, 'numeric-node.log')
            command([c.WABT, HERE.parent/'foreign-api/library.wat', '--enable-all', '-o', out/'library.wasm'], out, 'assembly.log')
            c.save(out/'library.json', dict(sha256=c.sha(out/'library.wasm')))
            command([c.NODE, ROOT/'tests/wasm/stage1/loader-target/boot0.mjs', args.boot, args.boot/'runtime-binaries',
                '--bundles='+str(args.level1), '--bundles='+str(args.checks),
                '--post-ready-load=/ccl/bin/loader-benchmark.w32fsl', '--expect-ready',
                '--host-extension='+str(HERE.parent/'foreign-api/extension.mjs'),
                '--extension-config='+json.dumps(dict(library=str(out/'library.wasm'))),
                '--layout='+json.dumps(dict(freeTarget=0)), '--report='+str(out/'node.json')], out, 'node.log')
            results = {'node': api.compare(native, c.read(out/'node.json'))}
            assert results['node'] == c.read(previous/'final/lisp-check.json')
            command([c.NODE, HERE/'browser.mjs', args.boot, args.level1, args.checks, out/'library.wasm', out/'browsers',
                args.playwright, args.browser_config], out, 'browser.log', timeout=2000)
            for engine in ['chromium', 'firefox', 'webkit']:
                report = c.read(out/'browsers'/f'{engine}.json')
                results[engine] = api.compare(native, report)
                assert results[engine] == results['node'], engine
                assert report['browserProvider']['requests'] > 0
                assert report['browserProvider']['archives'] == 2
                assert report['environment']['crossOriginIsolated']
                assert report['numericAdmission']['rows'] == c.read(out/'numeric-node.json')['rows']
                assert report['inputRefusals'] == ['HTTP', 'SIZE', 'DIGEST']
            for relative, digest in source_identity.items():
                assert c.sha(ROOT/relative) == digest, relative
            c.save(out/'comparison.json', results)
            c.save(out/'summary.json', dict(status='PASS', engines=list(results),
                native_matched_rows=results['node']['native_matched_rows'], foreign_entries=results['node']['foreign_entries'],
                moving_collections=results['node']['moving_collections'], callback_collections=results['node']['callback_collections'],
                review='NOT_REVIEWED', criterion_credit=False, product_lisp_lines_changed=0,
                skips=['compiler corpus deferred until whole FFI layer complete',
                       'mounted directories, multi-Worker D5, nested foreign calls, automatic finalizer pumping',
                       'browser calendar and CPU accounting capabilities']))
            (out/'library.wasm').unlink()
            c.save(out/'.run.json', dict(status='PASS'))
            print(json.dumps(c.read(out/'summary.json')))
        except Exception as error:
            c.save(out/'failure.json', dict(status='FAIL', error=str(error)))
            c.save(out/'failure-inputs.json', [p.name for p in out.glob('*.wasm')])
            c.save(out/'.run.json', dict(status='FAIL'))
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ['boot', 'level1', 'checks', 'playwright', 'browser-config']:
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('/private/tmp/ccl-work/codex/foreign-browser-tests/run'))
    run(parser.parse_args())
