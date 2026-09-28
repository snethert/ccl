"""Compile once, then measure serially in fresh processes on the macOS reference."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LOADER = HERE.parent / 'loader-target'
STORE = ROOT.parent / 'ccl-evidence'
IMAGE = STORE / '2026-09-16-stage1-1a-r2/native/baseline.image'
NODE = '/usr/local/bin/node'
TIERS = {'default': [], 'liftoff': ['--liftoff-only'],
         'turbofan': ['--no-liftoff', '--no-wasm-tier-up']}
CASES = {
    'EB-LOOP': (3, 0), 'EB-CALL': (3, 0), 'EB-REFERENCE-CALL': (0, 7),
    'EB-LIVE-REFERENCE': (3, 7), 'EB-OPTIONAL-LOOP': (10, 0),
    'EB-REST-LOOP': (10, 0), 'EB-KEYWORD-LOOP': (10, 0),
    'EB-CAR': (7, 0), 'EB-CAR-TYPED': (7, 0), 'EB-SVREF': (2, 0),
    'EB-SVREF-TYPED': (2, 0), 'EB-EQ': (1, 0), 'EB-FIXNUM-GENERIC': (3, 0),
    'EB-DOUBLE-GENERIC': (.5, 0), 'EB-DOUBLE-TYPED': (.5, 0), 'EB-SINGLE-TYPED': (.5, 0)}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def command(args, log, timeout=600, env=None):
    args = list(map(str, args))
    start = time.time()
    print('Running', log.name, flush=True)
    with log.open('w') as f:
        result = subprocess.run(args, cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
    save(log.with_suffix('.command.json'), dict(argv=args, exitCode=result.returncode,
         startEpoch=start, wallSeconds=time.time()-start))
    if result.returncode:
        raise RuntimeError(f'{log}: exit {result.returncode}')


def ram(out):
    assert platform.system() == 'Darwin'
    assert out.is_relative_to(Path('/private/tmp/ccl-work'))
    disks = subprocess.check_output(['hdiutil', 'info'], text=True).split('================================================')
    return next(d for d in disks if 'image-path      : ram://' in d and
                '/private/tmp/ccl-work' in d and '/Users/buildsomething/Library/Caches/ccl-wasm-validation' in d)


def parse(text):
    rows = []
    assert text.count('EB-PASS 16 9') == 1
    assert text.count('EB-GC-PASS 4 44') == 1
    for line in text.splitlines():
        if not line.startswith('EB-END '):
            continue
        _, name, trial, n, ticks, units, value = line.split()
        trial, n, ticks, units, value = map(int, (trial, n, ticks, units, value))
        slope, offset = CASES[name]
        assert n > 0 and n % 4 == 0 and n <= 4194304
        assert value == n * slope + offset, (name, n, value)
        assert ticks > 0 and units > 0, (name, ticks, units)
        rows.append(dict(name=name, trial=trial, iterations=n, ticks=ticks,
                         units=units, checksum=value, nsPerIteration=ticks*1e9/(units*n)))
    assert len(rows) == len(CASES)*9
    assert {(r['name'], r['trial']) for r in rows} == {(n,t) for n in CASES for t in range(9)}
    return rows


def assess(out):
    runs = []
    for path in sorted(out.glob('samples-*.json')):
        run = json.loads(path.read_text())
        runs.append(run)
    groups = {}
    for run in runs:
        for name in CASES:
            rows = [r for r in run['samples'] if r['name'] == name]
            groups.setdefault((run['mode'], name), []).append(statistics.median(r['nsPerIteration'] for r in rows))
    results = [dict(mode=mode, name=name, processMediansNs=values,
                    medianNs=statistics.median(values), minNs=min(values), maxNs=max(values))
               for (mode,name),values in sorted(groups.items())]
    save(out/'summary.json', dict(status='MEASURED', results=results,
         interpretation='Median of per-process medians. Ranges are observed process ranges, not confidence intervals. Typed Lisp is whatever the accepted compiler emitted; reference.wat is separately hand-written. Differences are workload contrasts, not additive percentages of READY.'))
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare','measure','assess'])
    p.add_argument('out', type=Path)
    p.add_argument('--inputs', type=Path)
    p.add_argument('--build', type=Path)
    p.add_argument('--replicas', type=int, default=3)
    p.add_argument('--tiers', default='default,liftoff,turbofan')
    p.add_argument('--ready-runs', type=int, default=3)
    args = p.parse_args(); out = args.out.resolve(); mount = ram(out)
    if args.action == 'assess':
        assess(out); return
    out.mkdir(parents=True, exist_ok=True)
    inputs = (args.inputs or out/'inputs').resolve()
    build = (args.build or out/'build').resolve()
    boot = inputs/'ready-inputs/boot-r8'
    if args.action == 'prepare':
        command([sys.executable, STORE/'2026-09-27-direct-call-r1/restore-inputs.py', inputs], out/'restore.log')
        command([sys.executable, LOADER/'build.py', build, '--postimage='+str(boot),
                 '--source='+str(HERE/'benchmarks.lisp')], out/'build.log')
        return
    assert 1 <= args.replicas <= 10 and 0 <= args.ready_runs <= 10
    tiers = args.tiers.split(','); assert all(t in TIERS for t in tiers)
    assert not (out/'inputs.json').exists(), 'use a fresh measurement directory'
    parent = json.loads((build/'postimage-parent.json').read_text())
    assert parent['source_sha256'] == sha(HERE/'benchmarks.lisp'), 'stale benchmark build'
    assert parent['manifest'] == sha(boot/'boot/artifacts/manifest.json'), 'different boot parent'
    build_sources = json.loads((build/'sources.json').read_text())
    for name, digest in build_sources.items():
        assert sha(ROOT/name) == digest, 'changed compiler input: '+name
    from code_shapes import inspect
    inspect(build, out/'code')
    versions = json.loads(subprocess.check_output([NODE, '-p', 'JSON.stringify(process.versions)'], text=True))
    sources = [*HERE.glob('*.*'), LOADER/'build.py', LOADER/'source-compile.lisp', LOADER/'boot0.mjs',
               ROOT/'compiler/WASM32/wasm32-backend.lisp']
    save(out/'inputs.json', dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
         sources={str(s.relative_to(ROOT)):sha(s) for s in sources if s.is_file()},
         binaries={str(s):sha(s) for s in [Path(NODE), build/'dx86cl64', IMAGE, build/'benchmark.dx64fsl', build/'benchmark.w32bundle']},
         host=platform.platform(), cpu=subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True).strip(),
         node=versions, tiers={t:TIERS[t] for t in tiers}, ramMount=mount,
         bootManifest=sha(boot/'boot/artifacts/manifest.json'), bundleManifest=sha(inputs/'bundles/bundle-manifest.json'),
         buildSources=json.loads((build/'sources.json').read_text()), sourceParent=json.loads((build/'postimage-parent.json').read_text())))
    command(['/usr/local/bin/wat2wasm', HERE/'reference.wat', '-o', out/'reference.wasm'], out/'reference-build.log')
    env = dict(os.environ, CCL_DEFAULT_DIRECTORY=str(ROOT)+'/')
    for replica in range(args.replicas):
        modes = ['native', *tiers]
        modes = modes[replica % len(modes):] + modes[:replica % len(modes)]
        for mode in modes:
            name = f'{mode}-{replica+1}'
            if mode == 'native':
                disassembly = out/f'native-{replica+1}.disassembly.txt'
                form = '(with-open-file (*standard-output* #P'+json.dumps(str(disassembly))+' :direction :output :if-exists :supersede) (dolist (name (quote ('+' '.join('ccl::'+n for n in CASES)+'))) (format t "~%~s~%" name) (disassemble name)))'
                command([build/'dx86cl64','-I',IMAGE,'--no-init','--batch','--load',build/'benchmark.dx64fsl',
                         '--eval',form,'--eval','(ccl:quit)'], out/(name+'.log'), env=env)
                text = (out/(name+'.log')).read_text()
                observation = None
            else:
                report = out/(name+'.ready.json')
                command([NODE,*TIERS[mode],LOADER/'boot0.mjs',boot,boot/'runtime-binaries',
                         '--bundles='+str(inputs/'bundles'),'--bundles='+str(build),
                         '--startup-load=/ccl/bin/loader-benchmark.w32fsl','--benchmark-events',
                         '--layout={"spaceBytes":33554432}','--expect-ready','--report='+str(report)],out/(name+'.log'))
                report = json.loads(report.read_text())
                assert report['ready'] and report['targetLoadedFiles'] == 82
                assert not report['openFiles'] and not report['abandonedSessions']
                text = ''.join(r['text'] for r in report['outputEvents'] if r['channel'] == 1)
                observation = report['benchmark']
                assert len(observation['forced']) == 4
                assert len(observation['samples']) == len(CASES)*9
                assert all(s['allocatedBytes'] >= 0 for s in observation['samples'])
                command([NODE,*TIERS[mode],HERE/'reference.mjs',out/'reference.wasm',out/(name+'.reference.json')],out/(name+'.reference.log'))
            save(out/('samples-'+name+'.json'), dict(mode=mode, replica=replica+1, samples=parse(text), observation=observation))
    for replica in range(args.ready_runs):
        command([sys.executable,LOADER/'startup-baseline.py',out/f'ready-{replica+1}',boot,inputs/'bundles','--space','32'],out/f'ready-{replica+1}.log')
        report = json.loads((out/f'ready-{replica+1}/ready.json').read_text())
        assert report['ready'] and report['targetLoadedFiles'] == 81
        assert report['productModules'] == 7 and report['productInstances'] == 11
    assess(out)
    print('BENCHMARK PASS', out, flush=True)


if __name__ == '__main__':
    main()
