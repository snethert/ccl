"""Restore each property-order bug in an isolated copy; the focused test must fail."""
from pathlib import Path
import argparse
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT/'tests/wasm/stage1/bootstrap-validation'))
import common as c
import storage


def run(args):
    out = args.output.resolve()
    with storage.lease([out]):
        storage.reset_run(out)
        runtime = out/'source/runtime/wasm32'
        fixture = out/'source/tests/wasm/stage2/foreign-browser'
        runtime.mkdir(parents=True)
        fixture.mkdir(parents=True)
        sources = [ROOT/'runtime/wasm32'/name for name in
            ['collector-owner.mjs', 'bytes.mjs', 'sha256.mjs', 'layout.mjs', 'integer-service.mjs', 'float-service.mjs']]
        sources += [HERE/name for name in ['numeric-check.mjs', 'numeric-node.mjs', 'numeric-controls.py']]
        c.save(out/'sources.json', {str(p.relative_to(ROOT)): c.sha(p) for p in sources})
        for p in sources:
            shutil.copyfile(p, out/'source'/p.relative_to(ROOT))
        rows = []
        for file, variable, reason in [('integer-service.mjs', 'mod', 'integer imports'),
                                       ('float-service.mjs', 'detector', 'FLOAT_IMPORTS')]:
            path = runtime/file
            original = path.read_text()
            before = f"JSON.stringify(WebAssembly.Module.imports({variable}).map(i=>[i.module,i.name,i.kind]))!==JSON.stringify([['env','memory','memory']])"
            after = f"JSON.stringify(WebAssembly.Module.imports({variable}))!==JSON.stringify([{{module:'env',name:'memory',kind:'memory'}}])"
            assert original.count(before) == 1
            try:
                path.write_text(original.replace(before, after))
                result = subprocess.run([str(c.NODE), str(fixture/'numeric-node.mjs'), str(args.runtime), str(out/'unexpected.json')],
                    capture_output=True, text=True, timeout=30)
                if not (result.returncode and ('Error: '+reason) in result.stderr):
                    c.save(out/'failure.json', dict(status='FAIL', source=file, stderr=result.stderr, stdout=result.stdout))
                    raise AssertionError('unexpected control result; see failure.json')
                rows.append(dict(name=file, status='KILLED', case='reordered import descriptor',
                    source_sha256=c.sha(path), error=result.stderr))
            finally:
                path.write_text(original)
        c.save(out/'result.json', dict(status='PASS', mutants=rows,
            binaries={name: c.sha(args.runtime/name) for name in ['collector.wasm', 'integer.wasm', 'float.wasm', 'detector.wasm']}))
        shutil.rmtree(out/'source')
        c.save(out/'.run.json', dict(status='PASS'))
        print('PASS: both property-order regressions killed')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--runtime', type=Path, required=True)
    p.add_argument('--output', type=Path, default=Path('/private/tmp/ccl-work/codex/foreign-browser-numeric/run'))
    run(p.parse_args())
