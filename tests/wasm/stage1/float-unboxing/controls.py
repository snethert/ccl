"""Run four single-change mutants through ordinary target LOAD."""
import json
from pathlib import Path
import subprocess
import sys
from check import check, rows
from mutate import mutate

HERE = Path(__file__).resolve().parent
LOADER = HERE.parent/'loader-target'


def run(build, inputs, native, passing, out):
    check(native, passing, build)
    out.mkdir(parents=True)
    boot = inputs/'ready-inputs/boot-r8'
    expected = rows(native.read_text())
    result = []
    for kind in ['arithmetic', 'rounding', 'safety', 'type']:
        candidate = out/kind
        mutate(build, candidate, kind)
        report = candidate/'ready.json'
        argv = ['node', str(LOADER/'boot0.mjs'), str(boot), str(boot/'runtime-binaries'),
                '--bundles='+str(inputs/'bundles'), '--bundles='+str(candidate),
                '--startup-load=/ccl/bin/loader-benchmark.w32fsl', '--benchmark-events',
                '--layout={"spaceBytes":33554432}', '--report='+str(report)]
        with (candidate/'run.log').open('w') as log:
            subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
        (candidate/'command.json').write_text(json.dumps(argv, indent=2)+'\n')
        observed = json.loads(report.read_text())
        text = ''.join(r['text'] for r in observed['outputEvents'] if r['channel'] == 1)
        if kind == 'arithmetic':
            assert observed['ready'] and 'FU-PASS' in text
            assert rows(text) != expected
            reason = 'raw-bit mismatch'
        else:
            assert not observed['ready'] and observed['reason'] == 'checked 15'
            assert 'FU-PASS' not in text
            reason = 'Lisp assertion or condition witness rejects mutant'
        result.append(dict(mutation=kind, status='KILLED', reason=reason))
        print(kind, 'KILLED', flush=True)
    value = dict(status='PASS', mutations=result)
    (out/'controls.json').write_text(json.dumps(value, indent=2)+'\n')


if __name__ == '__main__':
    run(*[Path(p).resolve() for p in sys.argv[1:6]])
