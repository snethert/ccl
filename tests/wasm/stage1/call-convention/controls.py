"""Check checker sensitivity, guarded public entries and moving-root mutants."""
import copy
import json
from pathlib import Path
import subprocess
import sys
from check import check, rows
from mutate import mutate

HERE = Path(__file__).resolve().parent


def run(build, inputs, native, passing, out, resume=False):
    check(native, passing)
    out.mkdir(parents=True, exist_ok=resume)
    good = json.loads(passing.read_text())
    controls = []
    for kind in ['wrong-answer', 'missing-collection', 'missing-row']:
        report = copy.deepcopy(good)
        if kind == 'missing-collection':
            report['benchmark']['forced'].pop()
        else:
            event = next(e for e in report['outputEvents'] if 'CC-ROW' in e['text'])
            event['text'] = event['text'].replace('CC-ROW', 'BAD-ROW' if kind == 'missing-row' else 'CC-ROW :WRONG', 1)
        path = out/(kind+'.json'); path.write_text(json.dumps(report))
        try:
            check(native, path)
        except AssertionError:
            controls.append(dict(kind=kind, status='KILLED'))
        else:
            raise AssertionError(kind)
    boot = inputs/'ready-inputs/boot-r8'
    expected = rows(native.read_text())
    for kind in ['public-entry', 'argument-roots', 'pool-root']:
        candidate = out/kind
        report = candidate/'ready.json'
        reuse = resume and report.exists()
        if reuse:
            assert (candidate/'benchmark.w32fsl').read_bytes() == (build/'benchmark.w32fsl').read_bytes()
        else:
            mutate(build, candidate, kind)
        argv = ['node', str(HERE.parent/'loader-target/boot0.mjs'), str(boot), str(boot/'runtime-binaries'),
                '--bundles='+str(inputs/'bundles'), '--bundles='+str(candidate),
                '--startup-load=/ccl/bin/loader-benchmark.w32fsl', '--benchmark-events',
                '--layout={"spaceBytes":33554432}', '--report='+str(report)]
        if not reuse:
            with (candidate/'run.log').open('w') as log:
                subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
            (candidate/'command.json').write_text(json.dumps(argv, indent=2)+'\n')
        else:
            assert json.loads((candidate/'command.json').read_text()) == argv
        observed = json.loads(report.read_text())
        text = ''.join(r['text'] for r in observed['outputEvents'] if r['channel'] == 1)
        if kind == 'public-entry':
            check(native, report)
            controls.append(dict(kind=kind, status='PASS', witness='all fixture public entries trap; compiled calls complete'))
        else:
            assert len(observed['benchmark']['forced']) >= 1, (kind, 'must reach moving collection')
            assert observed['ready'], (kind, 'must complete rather than trap')
            differences = [dict(native=a, target=b) for a,b in zip(expected, rows(text)) if a!=b]
            witness = {'argument-roots': ':ARGUMENT', 'pool-root': ':POOL'}[kind]
            assert len(rows(text)) == len(expected)
            assert any(d['native'].startswith('CC-ROW '+witness+' ') for d in differences), kind
            controls.append(dict(kind=kind, status='KILLED', reason=observed.get('reason'),
                                 differences=differences))
        print(kind, controls[-1]['status'], flush=True)
    (out/'controls.json').write_text(json.dumps(dict(status='PASS', controls=controls), indent=2)+'\n')


if __name__ == '__main__':
    run(*[Path(p).resolve() for p in sys.argv[1:6]], resume='--resume' in sys.argv[6:])
