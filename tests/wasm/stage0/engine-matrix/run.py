#!/usr/bin/env python3
"""S0-ENGINE-a: engine feature, version and profile suspension matrix on hand-built Wasm."""
import argparse, copy, hashlib, json, platform, plistlib, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from oracle import check, encoding_pin, PROBES
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[3]; TOOLS = ROOT / 'doc/WASM/tools'
sys.path.insert(0, str(TOOLS))
from evidence_binding import bind_report, contract_hash
ID = 'S0-ENGINE-a'; VARIANT = 'complete-report'
SCOPE = ('Hand-built wasm32 modules executed on macOS by Node/V8 as the reference engine and by Chrome, Firefox and Safari '
         'pages served over loopback with and without COOP/COEP. Records engine identity, feature detection, executed '
         'multivalue, tail-call, final exception-handling, bulk-memory and atomics semantics, the encoding pin, and the '
         'full, single-thread JSPI and precompiled-callback suspension paths. No CCL object layout, generated B code, GC, '
         'production runtime or hosting deployment is claimed.')
FEATURES = json.loads((HERE / 'features.json').read_text())
BROWSERS = json.loads((HERE / 'browsers.json').read_text())
BROWSER_NAMES = ['chrome', 'firefox', 'safari']
INVALID = bytes.fromhex('0061736d01000000010401600000030201000a05010300ff0b')  # one function whose body is opcode 0xff
MAIN_MODULES = ['features', 'features-shared', 'suspend']
# case -> (mutated file, old text, new text, first failure named by the unchanged oracle)
MUTANTS = {
    'tail-as-call': ('features.wat', '(return_call $tail (', '(call $tail (', 'TAIL direct'),
    'rethrow-omitted': ('features.wat', '    (throw_ref (local.get $e)))', '    (i32.const -3))', 'EH nested'),
    'multivalue-swapped': ('features.wat', '(local.get $a) (i32.add (local.get $a) (i32.const 1)))', '(i32.add (local.get $a) (i32.const 1)) (local.get $a))', 'MULTIVALUE pair'),
    'wait-omitted': ('features.wat', '(memory.atomic.wait32 (local.get $a) (local.get $expected) (local.get $timeout))', '(i32.const 0)', 'FULL woken'),
    'copy-omitted': ('features.wat', '(memory.copy (i32.const 160) (i32.const 128) (i32.const 23))', '(nop)', 'BULK bytes'),
    'jspi-local-clobbered': ('suspend.wat', '(i32.add (local.get $keep) (call $io (local.get $x)))', '(i32.add (i32.const 0) (call $io (local.get $x)))', 'JSPI run'),
    'detection-bypassed': ('matrix.mjs', 'const validates = bytes => WebAssembly.validate(bytes);', 'const validates = bytes => true;', 'DETECTION invalid'),
}
TEXT_SOURCES = ['features.wat', 'suspend.wat', 'matrix.mjs', 'wait-worker.mjs']


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def save(p, x): p.write_text(json.dumps(x, indent=2) + '\n')
def require(x, reason):
    if not x: raise ValueError(reason)


def sources():
    own = ['run.py', 'oracle.py', 'execute.mjs', 'browse.mjs', 'matrix.mjs', 'wait-worker.mjs', 'features.wat', 'suspend.wat', 'features.json', 'browsers.json']
    return [HERE / n for n in own] + sorted(HERE.glob('probes/*.wat')) + [TOOLS / 'gate.py', TOOLS / 'evidence_binding.py']


def invoke(argv, commands, out, cwd=None, timeout=120):
    try:
        p = subprocess.run(argv, cwd=cwd or ROOT, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        commands.append(dict(argv=argv, error=str(e))); save(out / 'commands.json', commands); raise
    commands.append(dict(argv=argv, cwd=str(cwd or ROOT), exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr))
    save(out / 'commands.json', commands)
    require(p.returncode == 0, 'COMMAND_EXIT ' + repr(commands[-1]))
    return p.stdout


def replace(text, old, new, name):
    require(text.count(old) == 1, 'MUTANT_SITE ' + name); return text.replace(old, new)


def browser_identity(name):
    info = BROWSERS[name]
    with open(Path(info['application']) / 'Contents/Info.plist', 'rb') as f:
        plist = plistlib.load(f)
    executable = Path(info['application']) / 'Contents/MacOS' / plist['CFBundleExecutable']
    return dict(application=info['application'], version=plist['CFBundleShortVersionString'], bundle_version=plist.get('CFBundleVersion'),
                executable=str(executable), executable_sha256=sha(executable), launcher=info['executable'], launcher_sha256=sha(Path(info['executable'])))


def identity_matches(name, observed, environment):
    engine = observed.get('engine') or {}
    if name == 'node':
        return engine.get('node') == environment['node'] and engine.get('v8') == environment['v8']
    major = environment['browsers'][name]['version'].split('.')[0]
    token = {'chrome': 'Chrome/' + major + '.', 'firefox': 'Firefox/' + major + '.', 'safari': 'Version/' + major + '.'}[name]
    return engine.get('name') == name and token in (engine.get('userAgent') or '')


def exercise(out):
    require(platform.system() == 'Darwin', 'MACOS_REFERENCE'); out.mkdir(parents=True, exist_ok=False)
    node = Path(shutil.which('node')).resolve(); compiler = Path(shutil.which('wat2wasm')).resolve(); objdump = Path(shutil.which('wasm-objdump')).resolve()
    commands = []
    v8 = invoke([str(node), '-p', 'process.versions.v8'], commands, out).strip()
    environment = dict(node=invoke([str(node), '--version'], commands, out).strip(), v8=v8,
                       wabt=invoke([str(compiler), '--version'], commands, out).strip(), wasm_objdump=invoke([str(objdump), '--version'], commands, out).strip(),
                       executable_sha256={str(p): sha(p) for p in (node, compiler, objdump)},
                       browsers={name: browser_identity(name) for name in BROWSER_NAMES}, python=sys.version, platform=platform.platform())
    save(out / 'environment.json', environment)
    profiles = Path(tempfile.mkdtemp(prefix='ccl-engine-matrix-profiles-'))
    observations = []; rows = []
    try:
        for case in ['complete', *MUTANTS]:
            b = out / 'bundles' / case; d = out / 'cases' / case; (b / 'probes').mkdir(parents=True); d.mkdir(parents=True)
            texts = {name: (HERE / name).read_text() for name in TEXT_SOURCES}
            if case in MUTANTS:
                name, old, new, first = MUTANTS[case]
                texts[name] = replace(texts[name], old, new, case)
                save(b / 'mutation.json', dict(case=case, file=name, old=old, new=new, first_failure=first))
            texts['features-shared.wat'] = replace(texts['features.wat'], '(memory 1 4))', '(memory 1 4 shared))', 'shared-variant')
            for name, text in texts.items(): (b / name).write_text(text)
            for name in ('features.json', 'browsers.json'): (b / name).write_bytes((HERE / name).read_bytes())
            for p in sorted(HERE.glob('probes/*.wat')): (b / 'probes' / p.name).write_bytes(p.read_bytes())
            (b / 'invalid.wasm').write_bytes(INVALID)
            options = dict(assembler_flags=FEATURES['assembler_flags'], probe_assembler_flags=FEATURES['probe_assembler_flags'], node_arguments=[],
                           browsers={n: BROWSERS[n]['arguments'] for n in BROWSER_NAMES}, page_variants=['isolated', 'plain'],
                           isolation_headers={'Cross-Origin-Opener-Policy': 'same-origin', 'Cross-Origin-Embedder-Policy': 'require-corp'},
                           tail_depth=FEATURES['tail_depth'], mutants_execute_on=['node'])
            save(b / 'options.json', options)
            save(b / 'host-compiler.json', dict(path=str(compiler), sha256=sha(compiler), version=environment['wabt'], disassembler=str(objdump), disassembler_sha256=sha(objdump)))
            for name in MAIN_MODULES:
                invoke([str(compiler), *FEATURES['assembler_flags'], name + '.wat', '-o', name + '.wasm'], commands, out, cwd=b)
            for p in sorted(HERE.glob('probes/*.wat')):
                invoke([str(compiler), *FEATURES['probe_assembler_flags'], 'probes/' + p.name, '-o', 'probes/' + p.stem + '.wasm'], commands, out, cwd=b)
            pin = {}
            for binary in [b / (n + '.wasm') for n in MAIN_MODULES] + sorted((b / 'probes').glob('*.wasm')):
                rel = binary.relative_to(b).as_posix()
                listing = invoke([str(objdump), '-d', rel], commands, out, cwd=b)
                (b / (rel + '.disassembly.txt')).write_text(listing)
                try: pin[rel] = encoding_pin(listing, require_final=rel in ('features.wasm', 'features-shared.wasm'))
                except ValueError as e: pin[rel] = dict(refused=str(e))
            require(set(k for k, v in pin.items() if 'refused' in v) == {'probes/legacy-eh.wasm'}, 'ENCODING_PIN')
            require(pin['probes/legacy-eh.wasm']['refused'] == 'ENCODING legacy catch try', 'ENCODING_PIN_REASON')
            save(b / 'encoding-pin.json', pin)
            save(b / 'manifest.json', dict(version=1, case=case, files={p.relative_to(b).as_posix(): sha(p) for p in sorted(b.rglob('*')) if p.is_file()}))
            invoke([str(node), str(HERE / 'execute.mjs'), str(b), str(d / 'node')], commands, out)
            node_observed = read(d / 'node' / 'observed.json'); require(identity_matches('node', node_observed, environment), 'ENGINE_IDENTITY node')
            if case in MUTANTS:
                try: check(node_observed, 'node')
                except ValueError as e: require(str(e) == MUTANTS[case][-1], 'MUTANT_REASON ' + case + ': ' + str(e))
                else: raise ValueError('MUTANT_ESCAPED ' + case)
                observations.append(dict(case=case, status='REJECTED_MUTANT', reason=MUTANTS[case][-1])); continue
            rows.append(check(node_observed, 'node'))
            for name in BROWSER_NAMES:
                for variant, isolated in (('isolated', '1'), ('plain', '0')):
                    target = d / (name + '-' + variant)
                    invoke([str(node), str(HERE / 'browse.mjs'), str(b), str(target), name, isolated, str(profiles)], commands, out)
                    observed = read(target / 'observed.json'); require(identity_matches(name, observed, environment), 'ENGINE_IDENTITY ' + name)
                    rows.append(check(observed, name, isolated == '1'))
            observations.append(dict(case=case, status='PASS', rows=len(rows)))
    finally:
        shutil.rmtree(profiles, ignore_errors=True)
    save(out / 'matrix.json', dict(version=1, engines=BROWSER_NAMES + ['node'], rows=rows))
    save(out / 'observations.json', observations)
    save(out / 'summary.json', dict(version=1, id=ID, variant=VARIANT, status='PASS', scope=SCOPE, review_disposition='NOT_REVIEWED',
                                     engines=4, node_executions=1 + len(MUTANTS), browser_pages=2 * len(BROWSER_NAMES), matrix_rows=len(rows),
                                     required_features=6, informational_probes=2, invalid_binary_detected=True, encoding_pin_binaries=len(MAIN_MODULES) + len(PROBES),
                                     encoding_pin_refusals=1, semantic_mutants_rejected=len(MUTANTS)))
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
        if p.name == 'features.wat': return 'template'
        if p.suffix == '.wat': return 'source'
        if p.suffix == '.wasm': return 'installed-binary'
        return {'features.json': 'schema', 'options.json': 'options', 'browsers.json': 'options', 'host-compiler.json': 'host-compiler',
                'matrix.mjs': 'implementation', 'wait-worker.mjs': 'implementation'}.get(p.name, 'log')
    if rel[0] in ('bundles', 'cases') and rel[1] in MUTANTS: return 'negative_control'
    if rel[0] == 'source':
        if p.name in ('run.py', 'oracle.py', 'execute.mjs', 'browse.mjs', 'gate.py', 'evidence_binding.py'): return 'test'
        if p.name == 'features.json': return 'schema'
        if p.name == 'browsers.json': return 'options'
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
        exercise(out); (out / 'inventory.json').write_bytes(invpath.read_bytes()); (out / 'source' / 'probes').mkdir(parents=True)
        for p in sources(): (out / 'source' / ('probes/' + p.name if p.parent.name == 'probes' else p.name)).write_bytes(p.read_bytes())
        artifacts = [dict(path=p.relative_to(out).as_posix(), sha256=sha(p), role=role(out, p)) for p in sorted(out.rglob('*')) if p.is_file()]
        test_revision = hashlib.sha256(json.dumps(source_sha, sort_keys=True).encode()).hexdigest()
        report = dict(version=1, source_revision=inv['source_revision'], inventory_sha256=sha(out / 'inventory.json'), scope=SCOPE, results=[dict(
            id=ID, variant=VARIANT, source_revision=test['source_revision'], evidence_kind=test['evidence_kind'], status='PASS',
            assertions=[dict(id=a['id'], status='PASS') for a in test['assertions']], artifacts=artifacts, substitutions=[], skips=[], review_disposition='NOT_REVIEWED',
            command=record['command'], toolchain=read(out / 'environment.json'), engine='Node/V8 reference engine plus Chrome, Firefox and Safari pages on macOS',
            timestamp=record['timestamp'], configuration=dict(scope=SCOPE, engines=['node', *BROWSER_NAMES], page_variants=['isolated', 'plain'], encoding=FEATURES['exception_encoding']['required']),
            seed='deterministic single schedule per engine; named module and driver mutations on the reference engine', test_revision=test_revision)])
        save(out / 'results.json', bind_report(report, inv, 'inventory.json', sha(out / 'inventory.json'))); save(out / 'slot-gate.json', slot(out)); omissions(out)
        require(record['source_sha256'] == {str(p.relative_to(ROOT)): sha(p) for p in sources()}, 'SOURCE_CHANGED')
        record.update(status='PASS', contract_sha256=contract_hash(inv, ID))
        print('PASS: ENGINE-a, four engines, seven matrix pages plus the reference run, one encoding-pin refusal, seven semantic mutants and nine role omissions. Review pending.')
    except BaseException as e:
        record['error'] = type(e).__name__ + ': ' + str(e); raise
    finally:
        if out.exists():
            save(out / 'run.json', record); (out / 'source' / 'probes').mkdir(parents=True, exist_ok=True)
            for name, data in snapshots.items():
                p = Path(name); (out / 'source' / ('probes/' + p.name if p.parent.name == 'probes' else p.name)).write_bytes(data)


def verify(packet):
    record = read(packet / 'run.json'); require(record['status'] == 'PASS', 'RUN_STATUS')
    for name, h in record['source_sha256'].items(): require(sha(ROOT / name) == h, 'SOURCE_PIN ' + name)
    for a in read(packet / 'results.json')['results'][0]['artifacts']: require(sha(packet / a['path']) == a['sha256'], 'ARTIFACT ' + a['path'])
    temp = Path(tempfile.mkdtemp(prefix='ccl-engine-matrix-verify-'))
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
    print('PASS: fresh execution on all four engines; ' + str(len(names)) + ' identical deterministic files, direct pins and role refusals.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output', type=Path); g.add_argument('--verify', type=Path); a = p.parse_args()
    if a.verify: verify(a.verify.resolve())
    else: run(a.output.resolve())
