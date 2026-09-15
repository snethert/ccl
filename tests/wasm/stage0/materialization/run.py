#!/usr/bin/env python3
"""S0-LL21-c: D2 template materialization, import limits and profile suspension on hand-built Wasm."""
import argparse, copy, hashlib, json, platform, re, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from oracle import check, CONTROLS
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[3]; TOOLS = ROOT / 'doc/WASM/tools'
BOUNDARY = HERE.parent / 'runtime-boundary/binary.mjs'; MATRIX = HERE.parent / 'engine-matrix/features.json'
sys.path.insert(0, str(TOOLS))
from evidence_binding import bind_report, contract_hash
ID = 'S0-LL21-c'; VARIANTS = ['shared-template', 'unshared-template']
SCOPE = ('Hand-built wasm32 Lisp-code template on macOS Node/V8: one canonical unshared explicit-maximum template materialized into the '
         'shared and unshared profile binaries by a single flag byte, with recorded template/binary hashes, offset, limits, import and '
         'export inventories, disassembly-derived feature requirements and materializer version. Engine import-limit subtyping, growth to '
         'and beyond the maximum, cross-profile link rejection, and the same template executing under the full wait-based, single-thread '
         'JSPI and precompiled-callback runtimes with identical results. Wrong records, tampered bytes, non-canonical templates, unadmitted '
         'profiles, stale identities and wrong-profile runtimes are refused. No CCL object layout, generated B code, production module '
         'granularity, image or browser deployment is claimed.')
ABI = json.loads((HERE / 'abi.json').read_text())
FLAGS = ['--enable-threads', '--enable-tail-call']
MODULES = ['template', 'runtime-full', 'runtime-jspi', 'runtime-sync']
# case -> (mutated file, old text, new text, first failure named by the unchanged oracle)
MUTANTS = {
    'hash-check-omitted': ('materializer.mjs', "  if (sha256(bytes) !== record.template_sha256) fail('template hash mismatch');\n", '', 'CONTROL wrong-template-hash'),
    'offset-trusted': ('materializer.mjs', "  for (const key of ['offset', 'minimum', 'maximum']) if (actual[key] !== record[key]) fail('wrong structural ' + key);\n",
                       "  for (const key of ['minimum', 'maximum']) if (actual[key] !== record[key]) fail('wrong structural ' + key);\n  actual.offset = record.offset;\n", 'CONTROL wrong-offset'),
    'import-check-omitted': ('materializer.mjs', "  if (JSON.stringify(actual.imports) !== JSON.stringify(record.imports)) fail('import inventory mismatch');\n", '', 'CONTROL import-mismatch'),
    'feature-check-omitted': ('materializer.mjs', "  if (JSON.stringify([...classification.features].sort()) !== JSON.stringify(record.features)) fail('feature requirement mismatch');\n", '', 'CONTROL feature-mismatch'),
    'identity-check-omitted': ('materializer.mjs', "  if (sha256(bytes) !== record.binary_sha256) fail('installed binary hash mismatch');\n", '', 'CONTROL stale-binary-hash'),
    'wait-rule-omitted': ('materializer.mjs', "  if (classification.wait && !rules.wait_allowed) fail('runtime carries a wait path the profile prohibits');\n", '', 'CONTROL runtime-profile-mismatch'),
    'template-increment-omitted': ('template.wat', '(i32.add (i32.add (call $request (local.get $x)) (local.get $serial)) (i32.const 1))', '(i32.add (i32.add (call $request (local.get $x)) (local.get $serial)) (i32.const 0))', 'FULL results'),
}
TEXT_SOURCES = ['template.wat', 'runtime-full.wat', 'runtime-jspi.wat', 'runtime-sync.wat', 'materializer.mjs', 'worker.mjs']


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def save(p, x): p.write_text(json.dumps(x, indent=2) + '\n')
def require(x, reason):
    if not x: raise ValueError(reason)


def sources():
    own = ['run.py', 'oracle.py', 'execute.mjs', 'materializer.mjs', 'worker.mjs', 'abi.json'] + [m + '.wat' for m in MODULES]
    return [HERE / n for n in own] + sorted(HERE.glob('controls/*.wat')) + [BOUNDARY, MATRIX, TOOLS / 'gate.py', TOOLS / 'evidence_binding.py']


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


def classify(listing_x, listing_d):
    """Feature families and wait use from wasm-objdump section and code listings."""
    mnemonics = set()
    for line in listing_d.splitlines():
        if '|' in line:
            text = line.split('|', 1)[1].strip()
            if text: mnemonics.add(text.split()[0])
    features = set()
    if re.search(r'-> \([^)]*,', listing_x): features.add('multivalue')
    if any(m.startswith('return_call') for m in mnemonics): features.add('tailcall')
    if any('.atomic.' in m for m in mnemonics): features.add('atomics')
    if mnemonics & {'try_table', 'throw', 'throw_ref'}: features.add('exceptions')
    if mnemonics & {'memory.copy', 'memory.fill', 'memory.init', 'data.drop'}: features.add('bulk')
    wait = any(m.startswith('memory.atomic.wait') or m == 'memory.atomic.notify' for m in mnemonics)
    shared = any(line.strip().startswith('- memory[') and line.rstrip().split('<-')[0].rstrip().endswith('shared') for line in listing_x.splitlines())
    return dict(features=sorted(features), wait=wait, shared_memory=shared)


def exercise(out):
    require(platform.system() == 'Darwin', 'MACOS_REFERENCE'); out.mkdir(parents=True, exist_ok=False)
    node = Path(shutil.which('node')).resolve(); compiler = Path(shutil.which('wat2wasm')).resolve(); objdump = Path(shutil.which('wasm-objdump')).resolve()
    commands = []
    environment = dict(node=invoke([str(node), '--version'], commands, out).strip(), v8=invoke([str(node), '-p', 'process.versions.v8'], commands, out).strip(),
                       wabt=invoke([str(compiler), '--version'], commands, out).strip(), wasm_objdump=invoke([str(objdump), '--version'], commands, out).strip(),
                       executable_sha256={str(p): sha(p) for p in (node, compiler, objdump)}, python=sys.version, platform=platform.platform())
    save(out / 'environment.json', environment)
    matrix = json.loads(MATRIX.read_text()); admission = {name: row['expected_profiles'] for name, row in matrix['engines'].items()}
    observations = []; summary = None
    for case in ['complete', *MUTANTS]:
        b = out / 'bundles' / case; d = out / 'cases' / case; (b / 'controls').mkdir(parents=True); d.mkdir(parents=True)
        texts = {name: (HERE / name).read_text() for name in TEXT_SOURCES}
        if case in MUTANTS:
            name, old, new, first = MUTANTS[case]
            texts[name] = replace(texts[name], old, new, case)
            save(b / 'mutation.json', dict(case=case, file=name, old=old, new=new, first_failure=first))
        for name, text in texts.items(): (b / name).write_text(text)
        (b / 'binary.mjs').write_bytes(BOUNDARY.read_bytes()); (b / 'abi.json').write_bytes((HERE / 'abi.json').read_bytes())
        for p in sorted(HERE.glob('controls/*.wat')): (b / 'controls' / p.name).write_bytes(p.read_bytes())
        save(b / 'admission.json', admission)
        save(b / 'options.json', dict(assembler_flags=FLAGS, node_arguments=[], profiles=list(ABI['profiles']), engine='node', request_argument=21, calls_per_profile=2))
        save(b / 'host-compiler.json', dict(path=str(compiler), sha256=sha(compiler), version=environment['wabt'], disassembler=str(objdump), disassembler_sha256=sha(objdump)))
        binaries = [m + '.wat' for m in MODULES] + ['controls/' + p.name for p in sorted(HERE.glob('controls/*.wat'))]
        classification = {}
        for wat in binaries:
            wasm = wat[:-4] + '.wasm'
            invoke([str(compiler), *FLAGS, wat, '-o', wasm], commands, out, cwd=b)
            listing_x = invoke([str(objdump), '-x', wasm], commands, out, cwd=b); listing_d = invoke([str(objdump), '-d', wasm], commands, out, cwd=b)
            (b / (wasm + '.disassembly.txt')).write_text(listing_x + '\n' + listing_d)
            classification[wasm] = classify(listing_x, listing_d)
        save(b / 'classification.json', classification)
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
    save(out / 'summary.json', dict(version=1, id=ID, variants=VARIANTS, status='PASS', scope=SCOPE, review_disposition='NOT_REVIEWED',
                                     profiles_executed=3, import_limit_cases=9, growth_cases=2, rejection_controls=len(CONTROLS), execution_witnesses=1,
                                     semantic_mutants_rejected=len(MUTANTS), **summary))
    return observations


def retain(p, x, replay=False):
    if replay: require(read(p) == x, 'RETAINED ' + p.name)
    else: save(p, x)


def slot(out, replay=False):
    inv = read(out / 'inventory.json'); inv['tests'] = [t for t in inv['tests'] if t['id'] == ID]; retain(out / 'slot-inventory.json', inv, replay)
    p = subprocess.run([sys.executable, str(TOOLS / 'gate.py'), '--inventory', str(out / 'slot-inventory.json'), '--results', str(out / 'results.json')], capture_output=True, text=True, timeout=30)
    value = dict(exit_code=p.returncode, result=json.loads(p.stdout), stderr=p.stderr)
    require(value == dict(exit_code=2, result=dict(status='BLOCKED', reasons=['unreviewed ' + ID + ' [' + v + ']' for v in VARIANTS]), stderr=''), 'SLOT_GATE'); return value


def omissions(out, replay=False):
    inv = read(out / 'slot-inventory.json'); base = read(out / 'results.json'); results = []
    for role in list(dict.fromkeys(inv['required_record_roles'] + inv['tests'][0]['required_record_roles'])):
        report = copy.deepcopy(base)
        for r in report['results']: r['artifacts'] = [a for a in r['artifacts'] if a['role'] != role]
        p = out / ('omit-' + role + '.json'); retain(p, report, replay)
        run = subprocess.run([sys.executable, str(TOOLS / 'gate.py'), '--inventory', str(out / 'slot-inventory.json'), '--results', str(p)], capture_output=True, text=True, timeout=30)
        value = json.loads(run.stdout)
        expected = ['missing artifact roles: ' + ID + ' [' + v + ']' for v in VARIANTS] + ['unreviewed ' + ID + ' [' + v + ']' for v in VARIANTS]
        require(run.returncode == 1 and not run.stderr and value == dict(status='FAIL', reasons=expected), 'ROLE_OMISSION ' + role)
        results.append(dict(role=role, exit_code=run.returncode, result=value))
    retain(out / 'role-omissions.json', results, replay)


def role(out, p):
    rel = p.relative_to(out).parts
    if rel[0] == 'bundles' and rel[1] == 'complete':
        if p.name == 'template.wat': return 'template'
        if p.suffix == '.wat': return 'source'
        if p.suffix == '.wasm': return 'installed-binary'
        return {'abi.json': 'abi', 'admission.json': 'schema', 'options.json': 'options', 'host-compiler.json': 'host-compiler',
                'materializer.mjs': 'implementation', 'binary.mjs': 'implementation', 'worker.mjs': 'implementation'}.get(p.name, 'log')
    if rel[0] == 'cases' and rel[1] == 'complete' and p.suffix == '.wasm': return 'installed-binary'
    if rel[0] in ('bundles', 'cases') and rel[1] in MUTANTS: return 'negative_control'
    if rel[0] == 'source':
        if p.name in ('run.py', 'oracle.py', 'execute.mjs', 'gate.py', 'evidence_binding.py'): return 'test'
        if p.name == 'abi.json': return 'abi'
        if p.name == 'features.json': return 'schema'
        return 'implementation'
    return 'schema' if p.name == 'inventory.json' else 'log'


def run(out):
    require(ROOT not in out.parents and out != ROOT and not out.exists(), 'FRESH_OUTPUT_OUTSIDE_CHECKOUT')
    snapshots = {str(p.relative_to(ROOT)): p.read_bytes() for p in sources()}
    source_sha = {str(p.relative_to(ROOT)): sha(p) for p in sources()}
    record = dict(version=1, status='FAIL', command=[sys.executable, *sys.argv], timestamp=datetime.now(timezone.utc).isoformat(), source_sha256=source_sha)
    snapshot_name = lambda p: 'controls/' + p.name if p.parent.name == 'controls' else ('engine-matrix-' + p.name if p.parent.name == 'engine-matrix' else p.name)
    try:
        invpath = ROOT / 'doc/WASM/stage0/inventory.json'; inv = read(invpath); test = next(t for t in inv['tests'] if t['id'] == ID)
        require(test['runner'] == str(HERE.relative_to(ROOT) / 'run.py'), 'RUNNER_REGISTRATION')
        require(test['variants'] == VARIANTS, 'VARIANT_REGISTRATION')
        exercise(out); (out / 'inventory.json').write_bytes(invpath.read_bytes()); (out / 'source' / 'controls').mkdir(parents=True)
        for p in sources(): (out / 'source' / snapshot_name(p)).write_bytes(p.read_bytes())
        artifacts = [dict(path=p.relative_to(out).as_posix(), sha256=sha(p), role=role(out, p)) for p in sorted(out.rglob('*')) if p.is_file()]
        test_revision = hashlib.sha256(json.dumps(source_sha, sort_keys=True).encode()).hexdigest()
        results = []
        for variant in VARIANTS:
            results.append(dict(id=ID, variant=variant, source_revision=test['source_revision'], evidence_kind=test['evidence_kind'], status='PASS',
                assertions=[dict(id=a['id'], status='PASS') for a in test['assertions']], artifacts=artifacts, substitutions=[], skips=[], review_disposition='NOT_REVIEWED',
                command=record['command'], toolchain=read(out / 'environment.json'), engine='Node/V8 reference engine on macOS',
                timestamp=record['timestamp'], configuration=dict(scope=SCOPE, variant=variant, profile='full' if variant == 'shared-template' else 'single-thread JSPI and precompiled callback',
                materializer_version=ABI['materializer_version']), seed='deterministic single schedule; named materializer, runtime-check and template mutations', test_revision=test_revision))
        report = dict(version=1, source_revision=inv['source_revision'], inventory_sha256=sha(out / 'inventory.json'), scope=SCOPE, results=results)
        save(out / 'results.json', bind_report(report, inv, 'inventory.json', sha(out / 'inventory.json'))); save(out / 'slot-gate.json', slot(out)); omissions(out)
        require(record['source_sha256'] == {str(p.relative_to(ROOT)): sha(p) for p in sources()}, 'SOURCE_CHANGED')
        record.update(status='PASS', contract_sha256=contract_hash(inv, ID))
        print('PASS: LL21-c shared-template and unshared-template, three profiles, nine link cases, ' + str(len(CONTROLS)) + ' rejection controls, one execution witness, seven semantic mutants and ten role omissions. Review pending.')
    except BaseException as e:
        record['error'] = type(e).__name__ + ': ' + str(e); raise
    finally:
        if out.exists():
            save(out / 'run.json', record); (out / 'source' / 'controls').mkdir(parents=True, exist_ok=True)
            for name, data in snapshots.items(): (out / 'source' / snapshot_name(Path(name))).write_bytes(data)


def verify(packet):
    record = read(packet / 'run.json'); require(record['status'] == 'PASS', 'RUN_STATUS')
    for name, h in record['source_sha256'].items(): require(sha(ROOT / name) == h, 'SOURCE_PIN ' + name)
    for a in read(packet / 'results.json')['results'][0]['artifacts']: require(sha(packet / a['path']) == a['sha256'], 'ARTIFACT ' + a['path'])
    temp = Path(tempfile.mkdtemp(prefix='ccl-materialization-verify-'))
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
    print('PASS: fresh materialization and execution; ' + str(len(names)) + ' identical deterministic files, direct pins and role refusals.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output', type=Path); g.add_argument('--verify', type=Path); a = p.parse_args()
    if a.verify: verify(a.verify.resolve())
    else: run(a.output.resolve())
