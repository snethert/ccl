"""Comparable sequential Chromium/Firefox timings on the same compiled inputs."""
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


def run(args):
    out = args.output.resolve()
    with storage.lease([out, args.boot, args.level1, args.checks]):
        storage.reset_run(out)
        c.save(out/'tools.json', {name: dict(path=str(p), sha256=c.sha(p)) for name, p in [('node', c.NODE), ('wat2wasm', c.WABT), ('python', Path(sys.executable))]})
        c.save(out/'execution-sources.json', {str(p.relative_to(ROOT)): c.sha(p)
            for p in list(HERE.glob('*.mjs')) + [Path(__file__).resolve()]})
        c.save(out/'build-inputs.json', {name: dict(sources=c.read(path/'sources.json'),
            recipe=c.read(path/'build-recipe.json')) for name, path in
            [('boot', args.boot), ('level1', args.level1), ('checks', args.checks)]})
        api.command([c.WABT, HERE.parent/'foreign-api/library.wat', '--enable-all', '-o', out/'library.wasm'], out, 'assembly.log')
        api.command([c.NODE, HERE/'browser.mjs', args.boot, args.level1, args.checks, out/'library.wasm',
            out/'browsers', args.playwright, args.browser_config, '--startup-timing'], out, 'browser.log', timeout=1500)
        previous = c.STORE/'2026-09-28-stage2-foreign-lisp-callbacks-r1'
        native = previous/'final/native.log'
        assert c.sha(native) == c.read(previous/'inventory.json')['final/native.log']
        c.save(out/'native-reference.json', dict(path=str(native), sha256=c.sha(native)))
        rows = {}
        for engine in ['chromium', 'firefox']:
            report = c.read(out/'browsers'/f'{engine}.json')
            assert api.compare(native, report) == c.read(previous/'final/lisp-check.json')
            timing = report['startupTiming']
            events = timing['events']
            startup, = [e for e in events if e['event'] == 'lisp.run']
            finished, = [e for e in events if e['event'] == 'finished']
            assert timing['startedAt'] < startup['start'] < startup['at'] < finished['at'] < timing['receivedAt']
            rows[engine] = dict(
                preparation_seconds=(startup['start']-timing['startedAt'])/1000,
                lisp_initialization_seconds=startup['ms']/1000,
                startup_to_ready_seconds=(startup['at']-timing['startedAt'])/1000,
                post_ready_ffi_seconds=(finished['at']-startup['at'])/1000,
                startup_and_ffi_seconds=(finished['at']-timing['startedAt'])/1000,
                runtime_archive_materialization_compile_seconds=sum(e['ms'] for e in events
                    if e['event']=='archive.compile' and e['stage']=='startup')/1000,
                native_matched_rows=61, runtime_loads=81, post_ready_loads=1)
        summary = dict(status='PASS', startup_performance='UNRESOLVED', runs_per_engine=1,
            sequential=True, rows=rows, boundaries=dict(
                startup='host run(config) entry, including input preload and Worker creation, to ProcessReady exit',
                preparation='host run(config) entry to Lisp top-level entry',
                lisp_initialization='Lisp top-level entry to ProcessReady exit',
                post_ready_ffi='ProcessReady exit to completion of post-READY witness and runner cleanup',
                runtime_archive_materialization_compile='subset of preparation; includes archive checks, hashes and Wasm compilation; excludes boot archive',
                excluded='Lisp source builds, browser process launch, initial page navigation and directed input-refusal checks'),
            caveats=['single run per engine, not a statistical benchmark',
                     'local HTTP inputs from verified RAM disk; sparse timing hooks enabled in both engines',
                     'no concurrent project build, browser test or diagnostic probe during measurement'])
        c.save(out/'summary.json', summary)
        (out/'library.wasm').unlink()
        c.save(out/'.run.json', dict(status='PASS'))
        print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ['boot', 'level1', 'checks', 'playwright', 'browser-config']:
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('/private/tmp/ccl-work/codex/browser-startup/run'))
    run(parser.parse_args())
