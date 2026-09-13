#!/usr/bin/env python3
"""S0-LL01-b: real failed/killed/timed-out children of the unchanged native aggregate."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TOOLS = ROOT / 'doc/WASM/tools'
NATIVE = ROOT / 'tests/wasm/native-baseline'
sys.path.insert(0, str(TOOLS))
from evidence_binding import bind_report, contract_hash

ID = 'S0-LL01-b'
STEPS = ['uname', 'macos', 'hardware', 'compiler', 'sdk', 'linker', 'make', 'm4', 'python',
         'extract-source', 'extract-tests', 'extract-bootstrap'] + [
    f'run-{n}-{s}' for n in (1, 2) for s in
    ('restore-image', 'kernel-clean', 'kernel-build', 'clean-rebuild', 'rebuilt-start', 'tests-clean', 'tests')]
CASES = [dict(name='complete', step=None, mode='success')] + [
    dict(name=step+'-'+mode, step=step, mode=mode)
    for step in ('run-1-kernel-build', 'run-1-clean-rebuild', 'run-2-tests')
    for mode in ('exit', 'kill', 'timeout')] + [
    dict(name='zero-without-marker', step='run-1-clean-rebuild', mode='missing-marker')]
SCOPE = ('Command outcome propagation through native-baseline run() and command(), with synthetic child argv, '
         'build products and test summaries. Actual subprocess exit 23, SIGKILL and one-second timeout; '
         'no CCL build, test or Wasm execution. Inner native-labelled reports are quarantined stimuli only.')


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def save(p, v): p.write_text(json.dumps(v, indent=2) + '\n')
def require(ok, why):
    if not ok: raise ValueError(why)


def sources():
    return [HERE/'run.py', HERE/'adapter.py', TOOLS/'gate.py', TOOLS/'evidence_binding.py'] + sorted(
        p for p in NATIVE.iterdir() if p.is_file())


def inputs(directory):
    directory.mkdir()
    members = {'source.tar': {'source.lisp': b'; Synthetic source, not compiled\n'},
        'tests.tar': {'tests.txt': b'SYNTHETIC TEST INPUT\n'},
        'bootstrap.tar.gz': {'dx86cl64': b'SYNTHETIC KERNEL, NOT EXECUTABLE\n',
                             'dx86cl64.image': b'SYNTHETIC IMAGE, NEVER LOADED\n'}}
    for name, files in members.items():
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w') as stream:
            for path, data in files.items():
                info = tarfile.TarInfo(path); info.size = len(data)
                stream.addfile(info, io.BytesIO(data))
        data = buffer.getvalue()
        (directory/name).write_bytes(gzip.compress(data, mtime=0) if name.endswith('.gz') else data)
    save(directory/'pins.json', dict(source_revision='SYNTHETIC-NOT-U1', test_revision='SYNTHETIC-NOT-UPSTREAM',
        actual_origin='QUARANTINED COMMAND STIMULUS', inputs={n:sha(directory/n) for n in members}))


def analyze(directory, case):
    """Read original subprocess records, independent of the invocation adapter."""
    cfg = read(directory/'config.json')
    require({k:cfg[k] for k in ('name', 'step', 'mode')} == case, 'CASE_IDENTITY')
    outcome = read(directory/'process.json')
    report = read(directory/'output/results.json')
    commands = read(directory/'output/commands.json')
    invocations = read(directory/'invocations.json')
    expected_steps = STEPS if case['step'] is None else STEPS[:STEPS.index(case['step'])+1]
    require([c['name'] for c in commands] == expected_steps, 'COMMAND_PREFIX '+case['name'])
    require([c['name'] for c in invocations] == expected_steps, 'INVOCATION_PREFIX')
    for i, (command, call) in enumerate(zip(commands, invocations)):
        require(command['argv'] == call['effective_argv'] and command['cwd'] == call['cwd']
                and command['timeout_seconds'] == call['effective_timeout'], 'COMMAND_FORWARDING')
        require(call['original_timeout'] == 1800 and call['original_argv'], 'ORIGINAL_INVOCATION')
        selected_timeout = case['mode'] == 'timeout' and command['name'] == case['step']
        require(command['timeout_seconds'] == (1 if selected_timeout else 1800), 'TIMEOUT_SELECTION')
        log = directory/'output'/(command['name']+'.log')
        require(sha(log) == command['log_sha256'], 'COMMAND_LOG_HASH')
        terminal = case['mode'] if command['name'] == case['step'] else 'success'
        require('TERMINAL MODE '+terminal in log.read_text(), 'CHILD_DID_NOT_REACH_STIMULUS')
        if call['marker']:
            require((call['marker'] in log.read_text()) == (terminal != 'missing-marker'), 'CHILD_MARKER')
        if i < len(commands)-1 or case['mode'] == 'success':
            require(command.get('returncode') == 0 and 'error' not in command, 'EARLIER_COMMAND_FAILURE')
    for artifact in report['artifacts']:
        require(sha(directory/'output'/artifact['path']) == artifact['sha256'], 'INNER_ARTIFACT')
    last = commands[-1]
    if case['mode'] == 'success':
        require(outcome['exit_code'] == 0 and report['execution_status'] == 'PASS'
                and report['gate0_status'] == 'EXECUTED_NOT_ACCEPTED' and 'failure' not in report
                and len(report['runs']) == 2 and report['repeatability']['status'] == 'RAW_IDENTICAL', 'POSITIVE_AGGREGATE')
        failure_kind = None
    else:
        require(outcome['exit_code'] == 1 and report['execution_status'] == 'FAIL'
                and report['gate0_status'] == 'NOT_ACCEPTED', 'FAILURE_NOT_PROPAGATED')
        require(report['failure'] == last['error'] and case['step'] in report['failure'], 'FAILURE_STEP')
        require(len(report['runs']) == (1 if case['step'] == 'run-2-tests' else 0), 'PARTIAL_RUN_ACCOUNTING')
        mode = case['mode']
        if mode in ('exit', 'kill'):
            code = 23 if mode == 'exit' else -9
            require(last.get('returncode') == code and last['error'] ==
                    f"{case['step']} exited {code}; see {case['step']}.log", 'EXIT_DIAGNOSTIC')
        elif mode == 'timeout':
            require('returncode' not in last and last['error'] == str(subprocess.TimeoutExpired(last['argv'], 1)), 'TIMEOUT_DIAGNOSTIC')
        else:
            require(last.get('returncode') == 0 and last['error'] ==
                    case['step']+' did not emit its completion marker', 'MARKER_DIAGNOSTIC')
        failure_kind = mode
    return dict(case=case['name'], step=case['step'], mode=case['mode'], child_commands=len(commands),
        aggregate_exit=outcome['exit_code'], execution_status=report['execution_status'],
        gate0_status=report['gate0_status'], completed_runs=len(report['runs']),
        failure_kind=failure_kind, last_returncode=last.get('returncode'),
        failure_step_identified=case['step'] is not None, later_commands_run=False)


def exercise(q):
    q.mkdir(); inputs(q/'inputs')
    (q/'SYNTHETIC.txt').write_text(SCOPE+'\nInner reports MUST NOT be submitted as native execution evidence.\n')
    observed = []
    for case in CASES:
        directory = q/case['name']; directory.mkdir()
        save(directory/'config.json', dict(**case, inputs=str(q/'inputs'), work=str(directory/'work'),
            output=str(directory/'output'), producer=str(NATIVE/'run.py'), actual_origin='SYNTHETIC COMMAND STIMULUS'))
        argv = [sys.executable, str(HERE/'adapter.py'), '--config', str(directory/'config.json')]
        with (directory/'aggregate.log').open('wb') as log:
            try:
                p = subprocess.run(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=45)
            except subprocess.TimeoutExpired as e:
                save(directory/'process.json', dict(command=argv, error=str(e))); raise
        save(directory/'process.json', dict(command=argv, exit_code=p.returncode))
        observed.append(analyze(directory, case))
    return observed


def slot_gate(out):
    inv = read(out/'inventory.json'); inv['tests'] = [t for t in inv['tests'] if t['id'] == ID]
    if (out/'slot-inventory.json').exists():
        require(read(out/'slot-inventory.json') == inv, 'SLOT_INVENTORY')
    else:
        save(out/'slot-inventory.json', inv)
    p = subprocess.run([sys.executable, str(TOOLS/'gate.py'), '--inventory', str(out/'slot-inventory.json'),
        '--results', str(out/'results.json')], cwd=ROOT, capture_output=True, text=True, timeout=30)
    result = dict(exit_code=p.returncode, result=json.loads(p.stdout), stderr=p.stderr)
    require(result == dict(exit_code=2, result=dict(status='BLOCKED', reasons=['unreviewed '+ID+' [control]']),
                           stderr=''), 'REAL_SLOT_GATE '+repr(result))
    return result


def run(out):
    require(out != ROOT and ROOT not in out.parents, 'FRESH_OUTPUT_OUTSIDE_CHECKOUT_REQUIRED')
    out.mkdir(parents=True, exist_ok=False)
    record = dict(version=1, status='FAIL', command=[sys.executable, *sys.argv],
        timestamp=datetime.now(timezone.utc).isoformat(),
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources()})
    try:
        inv_path = ROOT/'doc/WASM/stage0/inventory.json'; inventory = read(inv_path)
        test = next(t for t in inventory['tests'] if t['id'] == ID)
        require(test['runner'] == str(HERE.relative_to(ROOT)/'run.py') and test['variants'] == ['control'], 'RUNNER_REGISTRATION')
        for p in sources():
            dest = out/'source'/p.relative_to(ROOT); dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(p.read_bytes())
        (out/'inventory.json').write_bytes(inv_path.read_bytes())
        observed = exercise(out/'quarantine')
        save(out/'observations.json', observed)
        save(out/'cases.json', dict(test_id=ID, scope=SCOPE, cases=CASES))
        save(out/'summary.json', dict(version=1, id=ID, status='PASS', positive_cases=1, rejected_cases=10,
            failure_modes=['exit 23', 'SIGKILL (-9)', 'one-second timeout', 'zero exit without marker'],
            production_aggregate='tests/wasm/native-baseline/run.py:run and command (unchanged)',
            scope=SCOPE, review_disposition='NOT_REVIEWED'))
        # Retain every original sandbox byte once, compressed; no copied baseline.
        with zipfile.ZipFile(out/'quarantine.zip', 'x', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for p in sorted((out/'quarantine').rglob('*')):
                if p.is_file(): z.write(p, p.relative_to(out/'quarantine'))
        # Keep the live original directory until archive contents are checked.
        with zipfile.ZipFile(out/'quarantine.zip') as z:
            for p in sorted((out/'quarantine').rglob('*')):
                if p.is_file(): require(z.read(str(p.relative_to(out/'quarantine'))) == p.read_bytes(), 'ARCHIVE_COPY')
        shutil.rmtree(out/'quarantine')
        env = dict(python=sys.version, executable=sys.executable,
                   executable_sha256=sha(Path(sys.executable).resolve()), platform=platform.platform())
        save(out/'environment.json', env)
        artifacts = [dict(path=str(p.relative_to(out)), sha256=sha(p), role=(
            'implementation' if p == out/'source/tests/wasm/native-baseline/run.py' else
            'test' if 'source' in p.relative_to(out).parts else
            'schema' if p.name in ('cases.json', 'inventory.json') else 'log'))
            for p in sorted(out.rglob('*')) if p.is_file()]
        report = dict(version=1, source_revision=inventory['source_revision'], inventory_sha256=sha(out/'inventory.json'),
            scope=SCOPE, results=[dict(id=ID, variant='control', source_revision=test['source_revision'],
                evidence_kind=test['evidence_kind'], status='PASS',
                assertions=[dict(id=a['id'], status='PASS') for a in test['assertions']], artifacts=artifacts,
                substitutions=[], skips=[], review_disposition='NOT_REVIEWED', command=record['command'],
                toolchain=env, engine='Python production native aggregate with real controlled subprocesses',
                timestamp=record['timestamp'], configuration=dict(scope=SCOPE, cases=CASES),
                seed='deterministic command steps and failure modes', test_revision=sha(HERE/'run.py'))])
        save(out/'results.json', bind_report(report, inventory, 'inventory.json', sha(out/'inventory.json')))
        save(out/'slot-gate.json', slot_gate(out))
        require(record['source_sha256'] == {str(p.relative_to(ROOT)):sha(p) for p in sources()}, 'SOURCE_CHANGED')
        record.update(status='PASS', contract_sha256=contract_hash(inventory, ID))
        print('PASS: S0-LL01-b; one complete aggregate, ten required-child refusals. Real slot blocked only for review.')
    except BaseException as e:
        record['error'] = type(e).__name__+': '+str(e); raise
    finally:
        save(out/'run.json', record)


def verify(packet, replay):
    require(replay != ROOT and ROOT not in replay.parents and replay != packet
            and packet not in replay.parents, 'FRESH_REPLAY_OUTSIDE_PACKET_AND_CHECKOUT')
    replay.mkdir(parents=True, exist_ok=False)
    verification = dict(status='FAIL', command=[sys.executable, *sys.argv],
        timestamp=datetime.now(timezone.utc).isoformat(), packet=str(packet))
    try:
        verify_into(packet, replay)
        verification['status'] = 'PASS'
    except BaseException as e:
        verification['error'] = type(e).__name__+': '+str(e); raise
    finally:
        save(replay/'verification.json', verification)


def verify_into(packet, replay):
    record = read(packet/'run.json'); require(record['status'] == 'PASS', 'RUN_STATUS')
    for name, digest in record['source_sha256'].items(): require(sha(ROOT/name) == digest, 'SOURCE_PIN '+name)
    require(read(packet/'cases.json') == dict(test_id=ID, scope=SCOPE, cases=CASES), 'CASE_SOURCE')
    with tempfile.TemporaryDirectory(prefix='ccl-child-verification-') as tmp:
        tmp = Path(tmp)
        with zipfile.ZipFile(packet/'quarantine.zip') as z:
            require(all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist()), 'ARCHIVE_PATH')
            z.extractall(tmp/'retained')
        retained = [analyze(tmp/'retained'/c['name'], c) for c in CASES]
        require(retained == read(packet/'observations.json'), 'RETAINED_OBSERVATIONS')
    fresh = exercise(replay/'quarantine')
    save(replay/'observations.json', fresh)
    require(fresh == retained, 'FRESH_OBSERVATIONS')
    require(slot_gate(packet) == read(packet/'slot-gate.json'), 'RETAINED_SLOT')
    print('PASS: original and fresh eleven aggregate cases; exact terminal diagnostics, source pins and real-slot envelope.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path)
    group.add_argument('--verify', type=Path)
    parser.add_argument('--replay-output', type=Path, help='Fresh directory retaining verification subprocess evidence')
    args = parser.parse_args()
    if args.verify:
        if not args.replay_output: parser.error('--verify requires --replay-output (originals are retained)')
        verify(args.verify.resolve(), args.replay_output.resolve())
    else: run(args.output.resolve())
