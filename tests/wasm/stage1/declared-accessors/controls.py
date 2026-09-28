"""Require semantic rejection of each mutant after successful target LOAD."""
import json
from pathlib import Path
import subprocess
import sys
from check import check, rows
from mutate import mutate, KINDS

HERE = Path(__file__).resolve().parent


def run(build, inputs, native, passing, out):
    check(native, passing, build)
    out.mkdir(parents=True)
    boot = inputs/'ready-inputs/boot-r8'
    expected = rows(native.read_text())
    results = []
    for kind in KINDS:
        candidate = out/kind
        mutate(build, candidate, kind)
        report = candidate/'ready.json'
        argv = ['node', str(HERE.parent/'loader-target/boot0.mjs'), str(boot), str(boot/'runtime-binaries'),
                '--bundles='+str(inputs/'bundles'), '--bundles='+str(candidate),
                '--startup-load=/ccl/bin/loader-benchmark.w32fsl', '--benchmark-events',
                '--layout={"spaceBytes":33554432}', '--report='+str(report)]
        with (candidate/'run.log').open('w') as log:
            subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
        (candidate/'command.json').write_text(json.dumps(argv, indent=2)+'\n')
        observed = json.loads(report.read_text())
        text = ''.join(r['text'] for r in observed['outputEvents'] if r['channel'] == 1)
        assert observed['ready'] and 'DA-PASS' in text, (kind, observed.get('reason'))
        assert len(rows(text)) == len(expected) and rows(text) != expected
        results.append(dict(mutation=kind, status='KILLED', reason='native/target accessor mismatch',
                            differences=[dict(native=a, target=b) for a,b in zip(expected, rows(text)) if a != b]))
        print(kind, 'KILLED', flush=True)
    (out/'controls.json').write_text(json.dumps(dict(status='PASS', mutations=results), indent=2)+'\n')


if __name__ == '__main__':
    run(*[Path(p).resolve() for p in sys.argv[1:6]])
