#!/usr/bin/env python3
"""S0-LL19-a: exception transfer through nested emitted frames with cleanup that throws."""
import argparse, copy, hashlib, json, platform, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from oracle import check, EXPECTED
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[3]; TOOLS = ROOT / 'doc/WASM/tools'
sys.path.insert(0, str(TOOLS))
from evidence_binding import bind_report, contract_hash
ID = 'S0-LL19-a'; VARIANT = 'full'
SCOPE = ('Hand-built emitted wasm32 frames on macOS Node/V8 under the B entry shape: ten cases carry a nonlocal exit with zero, one and six '
         'values through nested frames with dynamic bindings, root records and cleanup, including a cleanup that raises a second exit, a '
         'chain of nine cleanup frames, a missing handler that reaches the host after full restoration, a recoverable check resumed by a '
         'use-value handler without unwinding, a declined handler that becomes an error, and a nested debugger exit inside the handler. '
         'VSP, TSP, CSP, the binding, the root head and the handler depth are restored after every case; inside every cleanup the departed '
         'inner frames are already gone (own binding, own root record, own stacks witnessed at cleanup entry) and before every handler delivers '
         'values, enters the debugger or propagates it observes only its own frame with no cleanup record, every expected address derived from '
         'the frame model rather than from saved fields; cleanups run exactly once; post-exit effects are absent; every value is checked. '
         'No production TCR, condition system, debugger, GC or C boundary is claimed.')
FLAGS = ['--enable-exceptions', '--enable-tail-call']
# case -> (old text, new text, first failure named by the unchanged oracle)
MUTANTS = {
    'special-restore-omitted': ("    (call $st (i32.const 12) (i32.load offset=4 (local.get $frame)))\n", '', 'STATE normal special'),
    'vsp-restore-omitted': ("    (call $st (i32.const 0) (i32.load (local.get $frame)))\n", '', 'STATE normal vsp'),
    'root-restore-omitted': ("    (call $st (i32.const 16) (i32.load offset=8 (local.get $frame)))\n", '', 'STATE normal root_head'),
    'cleanup-twice': ("    (call $unwind_to (local.get $frame))\n    (call $cleanup (local.get $frame))\n    (call $pop_frame (local.get $frame))\n    (if (i32.eq (call $arg (i32.const 0)) (i32.const 2))",
                      "    (call $unwind_to (local.get $frame))\n    (call $cleanup (local.get $frame))\n    (call $cleanup (local.get $frame))\n    (call $pop_frame (local.get $frame))\n    (if (i32.eq (call $arg (i32.const 0)) (i32.const 2))", 'STATE exit-0-values cleanup_count'),
    'exit-swallowed': ("    (throw_ref (local.get $e)))\n  (func $f2", "    (return (i32.const 65) (i32.const 0)))\n  (func $f2", 'STATE exit-0-values post_exit_effects'),
    'post-exit-in-cleanup': ("    (call $unwind_to (local.get $frame))\n    (call $cleanup (local.get $frame))\n    (call $pop_frame (local.get $frame))\n    (if (i32.eq (call $arg (i32.const 0)) (i32.const 2))",
                             "    (call $unwind_to (local.get $frame))\n    (call $effect (i32.const 3))\n    (call $cleanup (local.get $frame))\n    (call $pop_frame (local.get $frame))\n    (if (i32.eq (call $arg (i32.const 0)) (i32.const 2))", 'STATE exit-0-values post_exit_effects'),
    'transit-clobbered': ("(i32.add (local.get $frame) (i32.const 24))", "(call $ld (i32.const 40))", 'VALUES normal transit'),
    'secure-after-debugger': ("    (call $deliver_transit) (local.set $n) (local.set $v0)\n    (if (i32.eq (call $arg (i32.const 0)) (i32.const 5)) (then (call $debugger)))",
                              "    (if (i32.eq (call $arg (i32.const 0)) (i32.const 5)) (then (call $debugger)))\n    (call $deliver_transit) (local.set $n) (local.set $v0)", 'RESULT nested-debugger'),
    'restart-unwinds': ("(throw $use_value (i32.const 8)))", "(call $exit_with_values (i32.const 1)))", 'RESULT recoverable-use-value'),
    'unwind-omitted': ("    (local.set $e)\n    (call $unwind_to (local.get $frame))\n    (call $cleanup (local.get $frame))\n    (call $pop_frame (local.get $frame))\n    (if (i32.eq (call $arg (i32.const 0)) (i32.const 2))",
                       "    (local.set $e)\n    (call $cleanup (local.get $frame))\n    (call $pop_frame (local.get $frame))\n    (if (i32.eq (call $arg (i32.const 0)) (i32.const 2))", 'CLEANUP exit-0-values depth 3 special'),
    # the R2 review's defect: unwinding restores the state of a frame that pushed a cleanup, so the handler-only frame sees an invented record
    'handler-invents-cleanup-record': ("    (call $st (i32.const 8) (i32.load offset=20 (local.get $frame))))\n", "    (call $st (i32.const 8) (i32.sub (i32.load offset=12 (local.get $frame)) (i32.const 8))))\n", 'HANDLER exit-0-values 63 csp'),
    'cleanup-record-unowned': ("    (i32.store offset=20 (local.get $frame) (local.get $csp))\n", '', 'CLEANUP exit-0-values depth 2 csp'),
    'handler-witness-after-delivery': ("    (call $handler_witness (i32.const 63))\n    (call $event (i32.const 63))\n    (call $deliver_transit) (local.set $n) (local.set $v0)\n",
                                       "    (call $event (i32.const 63))\n    (call $deliver_transit) (local.set $n) (local.set $v0)\n    (call $handler_witness (i32.const 63))\n", 'HANDLER exit-0-values 63 event_count'),
}


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def save(p, x): p.write_text(json.dumps(x, indent=2) + '\n')
def require(x, reason):
    if not x: raise ValueError(reason)


def sources():
    return [HERE / n for n in ('run.py', 'oracle.py', 'execute.mjs', 'frames.wat', 'abi.json')] + [TOOLS / 'gate.py', TOOLS / 'evidence_binding.py']


def invoke(argv, commands, out, cwd=None, timeout=120):
    try:
        p = subprocess.run(argv, cwd=cwd or ROOT, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        commands.append(dict(argv=argv, error=str(e))); save(out / 'commands.json', commands); raise
    commands.append(dict(argv=argv, cwd=str(cwd or ROOT), exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr))
    save(out / 'commands.json', commands)
    require(p.returncode == 0, 'COMMAND_EXIT ' + repr(commands[-1]))
    return p.stdout


def exercise(out):
    require(platform.system() == 'Darwin', 'MACOS_REFERENCE'); out.mkdir(parents=True, exist_ok=False)
    node = Path(shutil.which('node')).resolve(); compiler = Path(shutil.which('wat2wasm')).resolve(); objdump = Path(shutil.which('wasm-objdump')).resolve()
    commands = []
    environment = dict(node=invoke([str(node), '--version'], commands, out).strip(), v8=invoke([str(node), '-p', 'process.versions.v8'], commands, out).strip(),
                       wabt=invoke([str(compiler), '--version'], commands, out).strip(), wasm_objdump=invoke([str(objdump), '--version'], commands, out).strip(),
                       executable_sha256={str(p): sha(p) for p in (node, compiler, objdump)}, python=sys.version, platform=platform.platform())
    save(out / 'environment.json', environment)
    source = (HERE / 'frames.wat').read_text(); observations = []; summary = None
    for case in ['complete', *MUTANTS]:
        b = out / 'bundles' / case; d = out / 'cases' / case; b.mkdir(parents=True); d.mkdir(parents=True)
        text = source
        if case in MUTANTS:
            old, new, first = MUTANTS[case]
            require(text.count(old) == 1, 'MUTANT_SITE ' + case); text = text.replace(old, new)
            save(b / 'mutation.json', dict(case=case, file='frames.wat', old=old, new=new, first_failure=first))
        (b / 'frames.wat').write_text(text); (b / 'abi.json').write_bytes((HERE / 'abi.json').read_bytes())
        save(b / 'options.json', dict(assembler_flags=FLAGS, node_arguments=[], memory_pages=1, cases=[c['name'] for c in json.loads((HERE / 'abi.json').read_text())['cases']]))
        save(b / 'host-compiler.json', dict(path=str(compiler), sha256=sha(compiler), version=environment['wabt'], disassembler=str(objdump), disassembler_sha256=sha(objdump)))
        invoke([str(compiler), *FLAGS, 'frames.wat', '-o', 'frames.wasm'], commands, out, cwd=b)
        (b / 'frames.wasm.disassembly.txt').write_text(invoke([str(objdump), '-x', 'frames.wasm'], commands, out, cwd=b) + '\n' + invoke([str(objdump), '-d', 'frames.wasm'], commands, out, cwd=b))
        save(b / 'manifest.json', dict(version=1, case=case, files={p.relative_to(b).as_posix(): sha(p) for p in sorted(b.rglob('*')) if p.is_file()}))
        invoke([str(node), str(HERE / 'execute.mjs'), str(b), str(d / 'node')], commands, out)
        observed = read(d / 'node' / 'observed.json')
        require(observed['engine'] == dict(node=environment['node'], v8=environment['v8']), 'ENGINE_IDENTITY')
        if case in MUTANTS:
            try: check(observed)
            except ValueError as e: require(str(e) == MUTANTS[case][-1], 'MUTANT_REASON ' + case + ': ' + str(e))
            else: raise ValueError('MUTANT_ESCAPED ' + case)
            observations.append(dict(case=case, status='REJECTED_MUTANT', reason=MUTANTS[case][-1])); continue
        summary = check(observed); observations.append(dict(case=case, status='PASS', **summary))
    save(out / 'observations.json', observations)
    save(out / 'summary.json', dict(version=1, id=ID, variant=VARIANT, status='PASS', scope=SCOPE, review_disposition='NOT_REVIEWED',
                                     semantic_mutants_rejected=len(MUTANTS), **summary))
    return observations


def retain(p, x, replay=False):
    if replay: require(read(p) == x, 'RETAINED ' + p.name)
    else: save(p, x)


def slot(out, replay=False):
    inv = read(out / 'inventory.json'); inv['tests'] = [t for t in inv['tests'] if t['id'] == ID]; retain(out / 'slot-inventory.json', inv, replay)
    p = subprocess.run([sys.executable, str(TOOLS / 'gate.py'), '--inventory', str(out / 'slot-inventory.json'), '--results', str(out / 'results.json')], capture_output=True, text=True, timeout=30)
    value = dict(exit_code=p.returncode, result=json.loads(p.stdout), stderr=p.stderr)
    require(value == dict(exit_code=2, result=dict(status='BLOCKED', reasons=['unreviewed ' + ID + ' [' + VARIANT + ']']), stderr=''), 'SLOT_GATE'); return value


def omissions(out, replay=False):
    inv = read(out / 'slot-inventory.json'); base = read(out / 'results.json'); results = []
    for role in list(dict.fromkeys(inv['required_record_roles'] + inv['tests'][0]['required_record_roles'])):
        report = copy.deepcopy(base); report['results'][0]['artifacts'] = [a for a in report['results'][0]['artifacts'] if a['role'] != role]
        p = out / ('omit-' + role + '.json'); retain(p, report, replay)
        run = subprocess.run([sys.executable, str(TOOLS / 'gate.py'), '--inventory', str(out / 'slot-inventory.json'), '--results', str(p)], capture_output=True, text=True, timeout=30)
        value = json.loads(run.stdout)
        require(run.returncode == 1 and not run.stderr and value == dict(status='FAIL', reasons=['missing artifact roles: ' + ID + ' [' + VARIANT + ']', 'unreviewed ' + ID + ' [' + VARIANT + ']']), 'ROLE_OMISSION ' + role)
        results.append(dict(role=role, exit_code=run.returncode, result=value))
    retain(out / 'role-omissions.json', results, replay)


def role(out, p):
    rel = p.relative_to(out).parts
    if rel[0] == 'bundles' and rel[1] == 'complete':
        return {'frames.wat': 'template', 'frames.wasm': 'installed-binary', 'abi.json': 'abi', 'options.json': 'options', 'host-compiler.json': 'host-compiler'}.get(p.name, 'log')
    if rel[0] in ('bundles', 'cases') and rel[1] in MUTANTS: return 'negative_control'
    if rel[0] == 'source':
        if p.name in ('run.py', 'oracle.py', 'gate.py', 'evidence_binding.py'): return 'test'
        if p.name == 'abi.json': return 'abi'
        if p.name == 'frames.wat': return 'source'
        return 'implementation'
    return 'schema' if p.name == 'inventory.json' else 'log'


def run(out):
    require(ROOT not in out.parents and out != ROOT and not out.exists(), 'FRESH_OUTPUT_OUTSIDE_CHECKOUT')
    snapshots = {str(p.relative_to(ROOT)): p.read_bytes() for p in sources()}
    source_sha = {str(p.relative_to(ROOT)): sha(p) for p in sources()}
    record = dict(version=1, status='FAIL', command=[sys.executable, *sys.argv], timestamp=datetime.now(timezone.utc).isoformat(), source_sha256=source_sha)
    try:
        invpath = ROOT / 'doc/WASM/stage0/inventory.json'; inv = read(invpath); test = next(t for t in inv['tests'] if t['id'] == ID)
        require(test['runner'] == str(HERE.relative_to(ROOT) / 'run.py'), 'RUNNER_REGISTRATION')
        require(test['variants'] == [VARIANT], 'VARIANT_REGISTRATION')
        exercise(out); (out / 'inventory.json').write_bytes(invpath.read_bytes()); (out / 'source').mkdir()
        for p in sources(): (out / 'source' / p.name).write_bytes(p.read_bytes())
        artifacts = [dict(path=p.relative_to(out).as_posix(), sha256=sha(p), role=role(out, p)) for p in sorted(out.rglob('*')) if p.is_file()]
        test_revision = hashlib.sha256(json.dumps(source_sha, sort_keys=True).encode()).hexdigest()
        report = dict(version=1, source_revision=inv['source_revision'], inventory_sha256=sha(out / 'inventory.json'), scope=SCOPE, results=[dict(
            id=ID, variant=VARIANT, source_revision=test['source_revision'], evidence_kind=test['evidence_kind'], status='PASS',
            assertions=[dict(id=a['id'], status='PASS') for a in test['assertions']], artifacts=artifacts, substitutions=[], skips=[], review_disposition='NOT_REVIEWED',
            command=record['command'], toolchain=read(out / 'environment.json'), engine='Node/V8 reference engine on macOS', timestamp=record['timestamp'],
            configuration=dict(scope=SCOPE, entry_shape='B (self, nargs) -> (value0, nvalues)', exception_encoding='final try_table/throw_ref with exnref', cases=len(EXPECTED)),
            seed='deterministic single schedule; named frame, cleanup, handler and value-securing mutations', test_revision=test_revision)])
        save(out / 'results.json', bind_report(report, inv, 'inventory.json', sha(out / 'inventory.json'))); save(out / 'slot-gate.json', slot(out)); omissions(out)
        require(record['source_sha256'] == {str(p.relative_to(ROOT)): sha(p) for p in sources()}, 'SOURCE_CHANGED')
        record.update(status='PASS', contract_sha256=contract_hash(inv, ID))
        print('PASS: LL19-a, ten nested-exit cases with cleanup-entry and handler-entry witnesses, thirteen semantic mutants and ten role omissions. Review pending.')
    except BaseException as e:
        record['error'] = type(e).__name__ + ': ' + str(e); raise
    finally:
        if out.exists():
            save(out / 'run.json', record); (out / 'source').mkdir(exist_ok=True)
            for name, data in snapshots.items(): (out / 'source' / Path(name).name).write_bytes(data)


def verify(packet):
    record = read(packet / 'run.json'); require(record['status'] == 'PASS', 'RUN_STATUS')
    for name, h in record['source_sha256'].items(): require(sha(ROOT / name) == h, 'SOURCE_PIN ' + name)
    for a in read(packet / 'results.json')['results'][0]['artifacts']: require(sha(packet / a['path']) == a['sha256'], 'ARTIFACT ' + a['path'])
    temp = Path(tempfile.mkdtemp(prefix='ccl-nested-eh-verify-'))
    try:
        fresh = temp / 'replay'; observations = exercise(fresh)
        require(read(fresh / 'environment.json') == read(packet / 'environment.json'), 'ENGINE_CHANGED')
        require(observations == read(packet / 'observations.json'), 'REPLAY_OBSERVATIONS')
        names = [p.relative_to(fresh) for p in fresh.rglob('*') if p.is_file() and p.name != 'commands.json']
        for n in names: require((fresh / n).read_bytes() == (packet / n).read_bytes(), 'REPLAY_BYTES ' + str(n))
        require(slot(packet, True) == read(packet / 'slot-gate.json'), 'RETAINED_SLOT'); omissions(packet, True)
    except BaseException as e:
        save(temp / 'failure.json', dict(status='FAIL', packet=str(packet), source_sha256=record['source_sha256'], error=str(e)))
        print('Original verification failure retained at ' + str(temp), file=sys.stderr); raise
    else:
        shutil.rmtree(temp)
    print('PASS: fresh nested-exit execution; ' + str(len(names)) + ' identical deterministic files, direct pins and role refusals.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output', type=Path); g.add_argument('--verify', type=Path); a = p.parse_args()
    if a.verify: verify(a.verify.resolve())
    else: run(a.output.resolve())
