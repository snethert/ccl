"""One bounded P-0 run; append-only journals and timing.json survive timeout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(out, run):
    rows = []
    for thread in ('main', 'worker'):
        path = out / ('events.' + thread + '.jsonl')
        if path.exists():
            lines = path.read_text().splitlines()
            for i, line in enumerate(lines):
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    if i != len(lines) - 1:
                        raise
    memory = [r for r in rows if r['kind'] == 'memory']
    worker = [r for r in memory if r['thread'] == 'worker']
    ready = next((r for r in worker if r['label'] == 'READY'), None)
    lisp = next((r for r in worker if r['label'] == 'lisp-start'), None)
    totals, files, inclusive = {}, {}, {}
    for row in rows:
        if row['kind'] == 'checkpoint':
            for part in row['exclusive']:
                key = row['thread'] + ':' + part['phase']
                totals[key] = totals.get(key, 0) + part['ms']
                file = files.setdefault(part['path'], {})
                file[key] = file.get(key, 0) + part['ms']
        if row['kind'] == 'span':
            key = row['thread'] + ':' + row['phase']
            item = inclusive.setdefault(key, dict(calls=0, ms=0))
            item['calls'] += 1
            item['ms'] += row['ms']
    report = json.loads((out / 'ready.json').read_text()) if (out / 'ready.json').exists() else None
    write(out / 'timing.json', dict(version=1, run=run,
        status='READY' if ready and report and report.get('ready') else 'PARTIAL',
        launchToReadyMs=ready['epochMs'] - run['startEpochMs'] if ready else None,
        lispToReadyMs=ready['epochMs'] - lisp['epochMs'] if ready and lisp else None,
        rssAtReadyBytes=ready['memory']['rss'] if ready else None,
        peakRssBytes=run['maxRssBytes'],
        exclusiveMs=totals, inclusiveSpans=inclusive, perFileExclusiveMs=files,
        memoryMilestones=[r for r in memory if r['label'] != 'periodic'],
        collections=[r for r in rows if r['kind'] == 'event' and r['label'] == 'collection'],
        fileEvents=[r for r in rows if r['kind'] == 'event' and r['label'] in ('file-open', 'file-close')],
        readyReport=report,
        interpretation=[
            'Exclusive time partitions each thread; main and Worker run concurrently and must not be added.',
            'Inclusive spans overlap their nested spans. Use exclusiveMs for attribution.',
            'worker:lisp.run is time outside timed services, including Lisp, other host work and observer/instrumentation overhead.',
            'Per-file attribution follows the innermost open file; admission/decode spans name their requested file explicitly.',
            'Partial runs retain completed spans; work after the last checkpoint can be absent from exclusive totals.',
            'RSS and peak RSS are process-wide. heapUsed/heapTotal/external/arrayBuffers are per thread.',
            'arrayBuffers is included in external. Linear memory and JS counters are not additive RSS components.',
            'allocatedHeapBytes includes garbage since the last GC. lastCollection.liveHeapBytes is live at that earlier timestamp.',
            'storage describes allocated extents, not resident pages. No forced GC is added at READY.',
            'worker-send to worker thread-start includes structured clone, thread startup and imports; it is not pure transfer time.'
        ]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('boot', type=Path)
    parser.add_argument('bundles', type=Path)
    parser.add_argument('--timeout', type=float, default=600)
    parser.add_argument('--layout', default=None)
    parser.add_argument('--space', type=int, choices=(16,32,64))
    args = parser.parse_args()
    assert platform.system() == 'Darwin', 'P-0 baseline reference is macOS'
    assert 0 < args.timeout <= 600, 'bounded baseline must not exceed ten minutes'
    # Both mounts must belong to a RAM image, not merely exist as directories.
    disks = subprocess.check_output(['hdiutil', 'info'], text=True).split('================================================')
    ram = next(d for d in disks if 'image-path      : ram://' in d and
               '/private/tmp/ccl-work' in d and '/Users/buildsomething/Library/Caches/ccl-wasm-validation' in d)
    for path in (args.out, args.boot, args.bundles):
        assert path.resolve().is_relative_to(Path('/private/tmp/ccl-work')), path
    args.out.mkdir(parents=True, exist_ok=False)
    out, boot, bundles = (p.resolve() for p in (args.out, args.boot, args.bundles))
    node = shutil.which('node')
    command = [node, str(ROOT / 'tests/wasm/stage1/loader-target/boot0.mjs'), str(boot),
        str(boot / 'runtime-binaries'), '--bundles=' + str(bundles),
        '--report=' + str(out / 'ready.json'), '--timing=' + str(out / 'events'), '--expect-ready']
    if args.layout:
        command.append('--layout=' + args.layout)
    if args.space:
        command.append('--layout=' + json.dumps(dict(spaceBytes=args.space*1048576)))
    sources = [*ROOT.glob('runtime/wasm32/*.mjs'), *Path(__file__).parent.glob('*.mjs'), Path(__file__)]
    write(out / 'inputs.json', dict(command=command, timeoutSeconds=args.timeout,
        commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        node=json.loads(subprocess.check_output([node, '-p', 'JSON.stringify(process.versions)'], text=True)),
        platform=platform.platform(), ramMount=ram,
        sources={str(p.relative_to(ROOT)): digest(p) for p in sources},
        inputs={str(p): digest(p) for p in [boot / 'boot/artifacts/manifest.json',
            boot / 'policy.json', boot / 'versions.json', bundles / 'bundle-manifest.json']},
        artifactOrigin='/Users/buildsomething/Source/ccl-evidence/2026-09-26-stage1-loader-completion-r1'))
    (out / 'instrumentation.patch').write_bytes(subprocess.check_output(['git', 'diff', '--',
        'runtime/wasm32', 'tests/wasm/stage1/loader-target'], cwd=ROOT))
    start, monotonic = time.time() * 1000, time.monotonic()
    with (out / 'stdout.log').open('wb') as stdout, (out / 'stderr.log').open('wb') as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
        write(out / 'running.json', dict(pid=process.pid, startEpochMs=start, timeoutSeconds=args.timeout))
        print(f'P-0 PID {process.pid}; timeout {args.timeout:g}s; journal {out}', flush=True)
        timed_out = False
        try:
            while True:
                pid, status, usage = os.wait4(process.pid, os.WNOHANG)
                if pid:
                    process.returncode = os.waitstatus_to_exitcode(status)
                    break
                if time.monotonic() - monotonic >= args.timeout:
                    timed_out = True
                    os.killpg(process.pid, signal.SIGKILL)
                    _, status, usage = os.wait4(process.pid, 0)
                    process.returncode = os.waitstatus_to_exitcode(status)
                    break
                time.sleep(0.25)
        except BaseException:
            os.killpg(process.pid, signal.SIGKILL)
            os.wait4(process.pid, 0)
            raise
    run = dict(startEpochMs=start, endEpochMs=time.time() * 1000, wallSeconds=time.monotonic() - monotonic,
        timeoutSeconds=args.timeout, timedOut=timed_out, exitCode=process.returncode,
        maxRssBytes=usage.ru_maxrss, userSeconds=usage.ru_utime, systemSeconds=usage.ru_stime,
        peakSource='macOS wait4 rusage for the Node child; ru_maxrss in bytes')
    write(out / 'run.json', run)
    summarize(out, run)
    print(json.dumps(run), flush=True)
    return process.returncode if not timed_out else 124


if __name__ == '__main__':
    sys.exit(main())
