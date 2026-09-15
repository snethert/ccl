#!/usr/bin/env python3
"""S0-LL15-a: harness initializers bound to prerequisite state and completion; omitted modules and no-load paths refused."""
import argparse, copy, hashlib, json, platform, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from oracle import check, CASES, ORDER
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[3]; TOOLS = ROOT / 'doc/WASM/tools'
sys.path.insert(0, str(TOOLS))
from evidence_binding import bind_report, contract_hash
ID = 'S0-LL15-a'; VARIANT = 'full'
SCOPE = ('Hand-built bootstrap closure on macOS Node/V8: three phases, four wasm32 modules and nine required initializers. The loader validates '
         'the manifest against the supplied modules before instantiating anything, seeds its own dependencies before any bundle exists, binds '
         'every initializer to its prerequisites’ physical completion words and required service state, checks each completion physically '
         'after the initializer returns, and publishes ready only after every required initializer completed. Fourteen refusals cover omitted and '
         'wrong modules, manifest defects, wrong or unwritten completions, a raised initializer, a clobbered prerequisite and wrong service state; '
         'eight loader mutants including a no-load path are rejected by the unchanged oracle over the whole memory image. Not the qualified census '
         'closure, the production loader, image format or generated code.')
FLAGS = ['--enable-exceptions']
MODULES = ['loader-core', 'bundle-a', 'bundle-b', 'bundle-c']
CONTROL_MODULES = ['bundle-a-no-loader-imports', 'bundle-b-no-export', 'bundle-b-returns-only', 'bundle-b-throws', 'bundle-b-wrong-completion', 'bundle-c-clobbers']
BASE = {m: m + '.wasm' for m in MODULES}


def manifest_mutations():
    """Named manifest defects for the control cases; each returns a mutated copy."""
    def deferred(m): m['modules']['bundle-c']['deferred'] = True
    def unknown(m): next(i for i in m['initializers'] if i['id'] == 'init_compiler')['prerequisites'].append('init_ffi')
    def cycle(m): next(i for i in m['initializers'] if i['id'] == 'init_symbols')['prerequisites'].append('init_readers')
    def forward(m): next(i for i in m['initializers'] if i['id'] == 'init_compiler')['prerequisites'].append('activate_errors')
    def unseeded(m): next(i for i in m['initializers'] if i['id'] == 'init_install')['phase'] = 1
    def bundle_phase(m): m['modules']['bundle-a']['phase'] = 0
    def state(m): next(i for i in m['initializers'] if i['id'] == 'finalize')['requires_state'][0]['value'] = 1
    return {'deferred-required': deferred, 'unknown-prerequisite': unknown, 'cycle': cycle, 'forward-phase': forward, 'loader-unseeded': unseeded, 'bundle-in-loader-phase': bundle_phase, 'state-mismatch': state}


CASE_CONFIGS = {
    'complete': dict(modules=BASE),
    'omitted-module': dict(modules={**BASE, 'bundle-b': None}),
    'no-export': dict(modules={**BASE, 'bundle-b': 'controls/bundle-b-no-export.wasm'}),
    'import-mismatch': dict(modules={**BASE, 'bundle-a': 'controls/bundle-a-no-loader-imports.wasm'}),
    'deferred-required': dict(modules=BASE, manifest='manifests/deferred-required.json'),
    'unknown-prerequisite': dict(modules=BASE, manifest='manifests/unknown-prerequisite.json'),
    'cycle': dict(modules=BASE, manifest='manifests/cycle.json'),
    'forward-phase': dict(modules=BASE, manifest='manifests/forward-phase.json'),
    'loader-unseeded': dict(modules=BASE, manifest='manifests/loader-unseeded.json'),
    'bundle-in-loader-phase': dict(modules=BASE, manifest='manifests/bundle-in-loader-phase.json'),
    'wrong-completion': dict(modules={**BASE, 'bundle-b': 'controls/bundle-b-wrong-completion.wasm'}),
    'returns-only': dict(modules={**BASE, 'bundle-b': 'controls/bundle-b-returns-only.wasm'}),
    'throws': dict(modules={**BASE, 'bundle-b': 'controls/bundle-b-throws.wasm'}),
    'clobbered-prerequisite': dict(modules={**BASE, 'bundle-c': 'controls/bundle-c-clobbers.wasm'}),
    'state-mismatch': dict(modules=BASE, manifest='manifests/state-mismatch.json'),
}
# loader mutant -> (old text, new text, first failure named by the unchanged oracle)
MUTANTS = {
    'no-load-path': ("    for (const s of i.requires_state) {\n      if (words[s.address / 4] !== s.value) fail('STATE_MISMATCH ' + i.id + ' @' + s.address, 'prerequisites', { observed: words[s.address / 4], expected: s.value });\n    }\n    note(200 + i.ordinal);\n    if (core.exports.completed(i.ordinal) !== 0) fail('ALREADY_COMPLETED ' + i.id, 'run');\n    note(300 + i.ordinal);\n    let code;\n    try { code = instances[i.module].exports[i.id](); }\n    catch (e) { fail('INITIALIZER_FAILED ' + i.id, 'run', { error: e.constructor.name }); }\n",
                     "    note(200 + i.ordinal);\n    if (core.exports.completed(i.ordinal) !== 0) fail('ALREADY_COMPLETED ' + i.id, 'run');\n    note(300 + i.ordinal);\n    const code = i.completion; core.exports.complete(i.ordinal, i.completion);\n", 'PHYSICAL complete services'),
    'prerequisite-check-omitted': ("      if (observed !== q.completion) fail('COMPLETION_MISMATCH ' + i.id + ' <- ' + p, 'prerequisites', { observed, expected: q.completion });\n", '', 'RESULT clobbered-prerequisite COMPLETION_MISMATCH activate_errors'),
    'seed-order-omitted': ("    for (const i of plan.order.filter(i => i.phase === 0)) run(i);\n    for (const name of plan.moduleOrder.filter(n => manifest.modules[n].role !== 'loader')) instantiate(name);\n",
                           "    for (const name of plan.moduleOrder.filter(n => manifest.modules[n].role !== 'loader')) instantiate(name);\n    for (const i of plan.order.filter(i => i.phase === 0)) run(i);\n", 'EVENTS complete'),
    'completion-trusted': ("    if (word !== i.completion) fail('COMPLETION_NOT_WRITTEN ' + i.id, 'completion', { observed: word, expected: i.completion });\n    if (counter !== 1) fail('EXECUTION_COUNT ' + i.id, 'completion', { observed: counter });\n", '', 'RESULT returns-only COMPLETION_MISMATCH init_compiler <- init_errors'),
    'ready-before-complete': ("    for (const i of plan.order.filter(i => i.phase !== 0)) run(i);\n  } catch (e) { if (e.refusal) return refuse(e.refusal.reason, e.refusal.stage, e.refusal); throw e; }\n",
                              "    words[manifest.ready.generation_word / 4] = 1; note(700);\n    for (const i of plan.order.filter(i => i.phase !== 0)) run(i);\n  } catch (e) { if (e.refusal) return refuse(e.refusal.reason, e.refusal.stage, e.refusal); throw e; }\n", 'EVENTS complete'),
    'omission-check-omitted': ("    if (!supplied[name]) fail('REQUIRED_MODULE_OMITTED ' + name, 'modules');\n", '', 'RESULT omitted-module crashed'),
    'export-check-omitted': ("      if (exports.get(i.id) !== 'function') fail('MISSING_INITIALIZER_EXPORT ' + name + '.' + i.id, 'modules');\n", '', 'RESULT no-export INITIALIZER_FAILED init_errors'),
    'phase-rule-omitted': ("    if (m.role === 'loader' && i.phase !== 0) fail('LOADER_DEPENDENCY_NOT_SEEDED ' + i.id, 'manifest');\n", '', 'RESULT loader-unseeded None'),
}


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def save(p, x): p.write_text(json.dumps(x, indent=2) + '\n')
def require(x, reason):
    if not x: raise ValueError(reason)


def sources():
    return [HERE / n for n in ('run.py', 'oracle.py', 'execute.mjs', 'loader.mjs', 'closure.json', 'abi.json')] + [HERE / (m + '.wat') for m in MODULES] + [HERE / 'controls' / (m + '.wat') for m in CONTROL_MODULES] + [TOOLS / 'gate.py', TOOLS / 'evidence_binding.py']


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
    loader = (HERE / 'loader.mjs').read_text(); manifest = read(HERE / 'closure.json'); observations = []; summary = None
    for bundle_name in ['complete', *MUTANTS]:
        b = out / 'bundles' / bundle_name; (b / 'controls').mkdir(parents=True); (b / 'manifests').mkdir(); (b / 'cases').mkdir()
        text = loader
        if bundle_name in MUTANTS:
            old, new, first = MUTANTS[bundle_name]
            require(text.count(old) == 1, 'MUTANT_SITE ' + bundle_name); text = text.replace(old, new)
            save(b / 'mutation.json', dict(mutant=bundle_name, file='loader.mjs', old=old, new=new, first_failure=first))
        (b / 'loader.mjs').write_text(text)
        for name in ('closure.json', 'abi.json', 'execute.mjs'): (b / name).write_bytes((HERE / name).read_bytes())
        for name, mutate in manifest_mutations().items():
            m = copy.deepcopy(manifest); mutate(m); save(b / 'manifests' / (name + '.json'), m)
        for m in MODULES: (b / (m + '.wat')).write_bytes((HERE / (m + '.wat')).read_bytes())
        for m in CONTROL_MODULES: (b / 'controls' / (m + '.wat')).write_bytes((HERE / 'controls' / (m + '.wat')).read_bytes())
        save(b / 'options.json', dict(assembler_flags=FLAGS, node_arguments=[], memory_pages=2, cases=list(CASES), phases=[p['phase'] for p in manifest['phases']], initializers=ORDER))
        save(b / 'host-compiler.json', dict(path=str(compiler), sha256=sha(compiler), version=environment['wabt'], disassembler=str(objdump), disassembler_sha256=sha(objdump)))
        for wat in [m + '.wat' for m in MODULES] + ['controls/' + m + '.wat' for m in CONTROL_MODULES]:
            wasm = wat[:-4] + '.wasm'
            invoke([str(compiler), *FLAGS, wat, '-o', wasm], commands, out, cwd=b)
            (b / (wasm + '.disassembly.txt')).write_text(invoke([str(objdump), '-x', wasm], commands, out, cwd=b))
        save(b / 'manifest.json', dict(version=1, bundle=bundle_name, files={p.relative_to(b).as_posix(): sha(p) for p in sorted(b.rglob('*')) if p.is_file()}))
        observed = {}; snapshots = {}
        for case, config in CASE_CONFIGS.items():
            d = b / 'cases' / case; d.mkdir()
            save(d / 'config.json', dict(case=case, **config))
            invoke([str(node), str(b / 'execute.mjs'), str(b), str(d / 'config.json'), str(d)], commands, out)
            observed[case] = read(d / 'observed.json'); snapshots[case] = (d / 'memory.bin.gz').read_bytes()
            require(observed[case]['node'] == environment['node'], 'ENGINE_IDENTITY')
        if bundle_name in MUTANTS:
            try: check(observed, snapshots)
            except ValueError as e: require(str(e) == MUTANTS[bundle_name][-1], 'MUTANT_REASON ' + bundle_name + ': ' + str(e))
            else: raise ValueError('MUTANT_ESCAPED ' + bundle_name)
            observations.append(dict(bundle=bundle_name, status='REJECTED_MUTANT', reason=MUTANTS[bundle_name][-1])); continue
        summary = check(observed, snapshots)
        observations.append(dict(bundle=bundle_name, status='PASS', **summary, refusals={c: observed[c]['result']['refusal']['reason'] for c in CASES if c != 'complete'}))
    save(out / 'observations.json', observations)
    save(out / 'summary.json', dict(version=1, id=ID, variant=VARIANT, status='PASS', scope=SCOPE, review_disposition='NOT_REVIEWED',
                                     refusal_controls=len(CASES) - 1, loader_mutants_rejected=len(MUTANTS), **summary))
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
        if len(rel) > 3 and rel[2] in ('controls', 'manifests'): return 'negative_control'
        if len(rel) > 3 and rel[2] == 'cases' and rel[3] != 'complete': return 'negative_control'
        if p.name == 'loader-core.wat': return 'template'
        if p.suffix == '.wat': return 'source'
        if p.suffix == '.wasm': return 'installed-binary'
        return {'abi.json': 'abi', 'closure.json': 'schema', 'options.json': 'options', 'host-compiler.json': 'host-compiler', 'loader.mjs': 'implementation', 'execute.mjs': 'test'}.get(p.name, 'log')
    if rel[0] == 'bundles' and rel[1] in MUTANTS: return 'negative_control'
    if rel[0] == 'source':
        if p.name in ('run.py', 'oracle.py', 'execute.mjs', 'gate.py', 'evidence_binding.py'): return 'test'
        if p.name == 'abi.json': return 'abi'
        if p.name == 'closure.json': return 'schema'
        if p.name == 'loader-core.wat': return 'template'
        if p.suffix == '.wat': return 'source'
        return 'implementation'
    return 'schema' if p.name == 'inventory.json' else 'log'


def run(out):
    require(ROOT not in out.parents and out != ROOT and not out.exists(), 'FRESH_OUTPUT_OUTSIDE_CHECKOUT')
    snapshots = {str(p.relative_to(ROOT)): p.read_bytes() for p in sources()}
    source_sha = {str(p.relative_to(ROOT)): sha(p) for p in sources()}
    record = dict(version=1, status='FAIL', command=[sys.executable, *sys.argv], timestamp=datetime.now(timezone.utc).isoformat(), source_sha256=source_sha)
    name_of = lambda p: 'controls/' + p.name if p.parent.name == 'controls' else p.name
    try:
        invpath = ROOT / 'doc/WASM/stage0/inventory.json'; inv = read(invpath); test = next(t for t in inv['tests'] if t['id'] == ID)
        require(test['runner'] == str(HERE.relative_to(ROOT) / 'run.py'), 'RUNNER_REGISTRATION')
        require(test['variants'] == [VARIANT], 'VARIANT_REGISTRATION')
        exercise(out); (out / 'inventory.json').write_bytes(invpath.read_bytes()); (out / 'source' / 'controls').mkdir(parents=True)
        for p in sources(): (out / 'source' / name_of(p)).write_bytes(p.read_bytes())
        artifacts = [dict(path=p.relative_to(out).as_posix(), sha256=sha(p), role=role(out, p)) for p in sorted(out.rglob('*')) if p.is_file()]
        test_revision = hashlib.sha256(json.dumps(source_sha, sort_keys=True).encode()).hexdigest()
        report = dict(version=1, source_revision=inv['source_revision'], inventory_sha256=sha(out / 'inventory.json'), scope=SCOPE, results=[dict(
            id=ID, variant=VARIANT, source_revision=test['source_revision'], evidence_kind=test['evidence_kind'], status='PASS',
            assertions=[dict(id=a['id'], status='PASS') for a in test['assertions']], artifacts=artifacts, substitutions=[], skips=[], review_disposition='NOT_REVIEWED',
            command=record['command'], toolchain=read(out / 'environment.json'), engine='Node/V8 reference engine on macOS', timestamp=record['timestamp'],
            configuration=dict(scope=SCOPE, phases=3, modules=len(MODULES), initializers=len(ORDER), cases=list(CASES)),
            seed='deterministic single schedule; named manifest, module and loader mutations', test_revision=test_revision)])
        save(out / 'results.json', bind_report(report, inv, 'inventory.json', sha(out / 'inventory.json'))); save(out / 'slot-gate.json', slot(out)); omissions(out)
        require(record['source_sha256'] == {str(p.relative_to(ROOT)): sha(p) for p in sources()}, 'SOURCE_CHANGED')
        record.update(status='PASS', contract_sha256=contract_hash(inv, ID))
        print('PASS: LL15-a, one complete bootstrap, fourteen refusals, eight loader mutants and ten role omissions. Review pending.')
    except BaseException as e:
        record['error'] = type(e).__name__ + ': ' + str(e); raise
    finally:
        if out.exists():
            save(out / 'run.json', record); (out / 'source' / 'controls').mkdir(parents=True, exist_ok=True)
            for name, data in snapshots.items(): (out / 'source' / name_of(Path(name))).write_bytes(data)


def verify(packet):
    record = read(packet / 'run.json'); require(record['status'] == 'PASS', 'RUN_STATUS')
    for name, h in record['source_sha256'].items(): require(sha(ROOT / name) == h, 'SOURCE_PIN ' + name)
    for a in read(packet / 'results.json')['results'][0]['artifacts']: require(sha(packet / a['path']) == a['sha256'], 'ARTIFACT ' + a['path'])
    temp = Path(tempfile.mkdtemp(prefix='ccl-initializer-binding-verify-'))
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
    print('PASS: fresh bootstrap execution; ' + str(len(names)) + ' identical deterministic files, direct pins and role refusals.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output', type=Path); g.add_argument('--verify', type=Path); a = p.parse_args()
    if a.verify: verify(a.verify.resolve())
    else: run(a.output.resolve())
