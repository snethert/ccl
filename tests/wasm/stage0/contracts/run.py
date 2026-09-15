#!/usr/bin/env python3
"""S0-CONTRACTS-a: complete versioned layout schema, source-to-target ledger and runtime-contract join checked against executed fixtures."""
import argparse, copy, hashlib, json, platform, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
import schema as S, join as J
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[3]; TOOLS = ROOT / 'doc/WASM/tools'; DOCS = ROOT / 'doc/WASM'
sys.path.insert(0, str(TOOLS))
from evidence_binding import bind_report, contract_hash
ID = 'S0-CONTRACTS-a'; VARIANT = 'complete-report'
U1 = 'c994217adc56b3f8a564526cee4695893ac84d86'
SCOPE = ('Control execution on macOS: the wasm32 layout schema v1 is derived from the pinned U1 x8632 architecture source and cross-checked '
         'against the U1 C header; every derived row carries a source-to-target disposition; the initial contracts/layout.json subset agrees; '
         'the committed schema equals the regeneration. The runtime-contract join v1 verifies frames, roots, TCR fields, allocation/store '
         'protocols and C-boundary restoration against the accepted fixtures’ retained schemas and cases by artifact hash, and re-derives the '
         'link-derived memory/table ownership map from retained link metadata. Nine synthetic controls are refused. This reviews contracts '
         'against executed evidence; it executes no Wasm and confers no runtime acceptance of its own.')
COMMITTED_SCHEMA = DOCS / 'contracts/wasm32-layout.v1.json'; COMMITTED_JOIN = DOCS / 'contracts/runtime-contracts.v1.json'
LISP = ROOT / S.LISP_SOURCE; CHEADER = ROOT / S.C_SOURCE; LAYOUT = DOCS / 'contracts/layout.json'; FRAMES = DOCS / 'contracts/debug-frames.md'
LEDGER = DOCS / 'evidence/current-stage0-gate-result.json'; REPOSITORY = DOCS / 'evidence/repository.json'


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def save(p, x): p.write_text(json.dumps(x, indent=2, ensure_ascii=False) + '\n')
def canonical(x): return json.dumps(x, indent=2, ensure_ascii=False) + '\n'
def require(x, reason):
    if not x: raise ValueError(reason)


def sources():
    return [HERE / n for n in ('run.py', 'derive.py', 'schema.py', 'join.py', 'ownership.mjs', 'dispositions.json')] + [LISP, CHEADER, LAYOUT, FRAMES, COMMITTED_SCHEMA, COMMITTED_JOIN, TOOLS / 'gate.py', TOOLS / 'evidence_binding.py']


def u1_pin(path):
    """The working file must equal the pinned U1 blob; returns its hash."""
    blob = subprocess.run(['git', '-C', str(ROOT), 'cat-file', '-p', U1 + ':' + path.relative_to(ROOT).as_posix()], capture_output=True, timeout=60)
    require(blob.returncode == 0, 'U1_BLOB ' + str(path))
    digest = hashlib.sha256(blob.stdout).hexdigest()
    require(digest == sha(path), 'U1_PIN ' + str(path.relative_to(ROOT)))
    return digest


def build_schema(lisp_text, c_text, ledger, layout):
    return S.build(lisp_text, c_text, ledger, layout, U1, hashlib.sha256(lisp_text.encode()).hexdigest(), hashlib.sha256(c_text.encode()).hexdigest())


def build_join(evidence_root, aggregate, frames_text, node, base=None):
    return J.build(J.Evidence(evidence_root, aggregate, base=base), frames_text, node, str(HERE))


def controls(out, lisp_text, c_text, ledger, layout, built_schema, built_join, evidence_root, aggregate, frames_text, node):
    """Synthetic mutations of copies; each must be refused with its named reason."""
    q = out / 'quarantine'; q.mkdir()
    results = []
    def control(name, fn, expected):
        try: fn()
        except ValueError as e: reason = str(e)
        else: raise ValueError('CONTROL_ESCAPED ' + name)
        require(reason.startswith(expected), 'CONTROL_REASON ' + name + ': ' + reason)
        results.append(dict(control=name, refused=reason)); save(q / (name + '.json'), dict(control=name, refused=reason))
    bad_ledger = copy.deepcopy(ledger); del bad_ledger['constants']['fulltag-cons']
    control('disposition-omitted', lambda: build_schema(lisp_text, c_text, bad_ledger, layout), 'LEDGER constants fulltag-cons')
    control('lisp-constant-mutated', lambda: S.check(build_schema(lisp_text.replace('(defconstant fulltag-cons 1)', '(defconstant fulltag-cons 2)'), c_text, ledger, layout)), 'D1 fulltags')
    control('c-header-mutated', lambda: S.check(build_schema(lisp_text, c_text.replace('#define fulltag_misc 6', '#define fulltag_misc 7'), ledger, layout)), 'C_AGREEMENT')
    bad_layout = copy.deepcopy(layout); bad_layout['cons']['car_raw_offset'] = 0
    control('subset-mutated', lambda: S.check(build_schema(lisp_text, c_text, ledger, bad_layout)), 'SUBSET')
    bad_schema = copy.deepcopy(built_schema); bad_schema['objects'][0]['cells'][0]['disposition'] = 'inherited-ish'
    control('schema-vocabulary-mutated', lambda: S.check(bad_schema), 'LEDGER row cdr')
    control('frame-contract-mutated', lambda: build_join(evidence_root, aggregate, frames_text.replace('| 56 | mv_descriptor |', '| 52 | mv_descriptor |'), node), 'FRAME header')
    # Stale artifact hash inside a copy of the accepted aggregate.
    # The copy of the accepted aggregate with one stale hash is not retained
    # (it would duplicate a multi-megabyte accepted file); its patch is.
    agg = read(Path(aggregate)); target = next(r for r in agg['results'] if r['id'] == 'S0-LL13-c')
    victim = next(a for a in target['artifacts'] if a['path'].endswith('memory-ownership.json')); original = victim['sha256']; victim['sha256'] = '0' * 64
    with tempfile.TemporaryDirectory(prefix='ccl-contracts-stale-') as temp:
        stale = Path(temp) / 'stale-aggregate.json'; stale.write_text(canonical(agg))
        save(q / 'stale-aggregate.patch.json', dict(source=Path(aggregate).name, source_sha256=sha(Path(aggregate)), record='S0-LL13-c', artifact=victim['path'], original_sha256=original, replaced_with='0' * 64, copy_sha256=sha(stale)))
        control('stale-artifact-hash', lambda: build_join(evidence_root, stale, frames_text, node, base=Path(aggregate).parent), 'ARTIFACT hash')
    bad_join = copy.deepcopy(built_join); bad_join['ownership']['regions'][3]['start'] = bad_join['ownership']['regions'][2]['start']
    control('ownership-overlap', lambda: J.check(bad_join), 'OWNERSHIP overlap')
    bad_join2 = copy.deepcopy(built_join); bad_join2['tcr']['fixture_private_aliases']['80']['cleanup_effect'] = ['S0-LL20-a']
    control('tcr-alias-within-fixture', lambda: J.check(bad_join2), 'TCR aliased within one fixture')
    return results


def exercise(out):
    require(platform.system() == 'Darwin', 'MACOS_REFERENCE'); out.mkdir(parents=True, exist_ok=False)
    node = str(Path(shutil.which('node')).resolve())
    pins = {S.LISP_SOURCE: u1_pin(LISP), S.C_SOURCE: u1_pin(CHEADER)}
    environment = dict(node=subprocess.run([node, '--version'], capture_output=True, text=True).stdout.strip(), node_sha256=sha(Path(node)), python=sys.version, platform=platform.platform(), u1_pins=pins)
    save(out / 'environment.json', environment)
    lisp_text = LISP.read_text(); c_text = CHEADER.read_text(); ledger = read(HERE / 'dispositions.json'); layout = read(LAYOUT); frames_text = FRAMES.read_text()
    built = build_schema(lisp_text, c_text, ledger, layout); summary = S.check(built, expected_sources=pins)
    save(out / 'wasm32-layout.v1.json', built)
    require(canonical(built) == COMMITTED_SCHEMA.read_text(), 'COMMITTED_SCHEMA differs from the regeneration')
    ledger_state = read(LEDGER); evidence_root = read(REPOSITORY)['path']; aggregate = ledger_state['combined_results']
    require(Path(aggregate).resolve().is_relative_to(Path(evidence_root).resolve()), 'AGGREGATE outside the evidence repository')
    joined = build_join(evidence_root, aggregate, frames_text, node); jsummary = J.check(joined)
    save(out / 'runtime-contracts.v1.json', joined)
    require(canonical(joined) == COMMITTED_JOIN.read_text(), 'COMMITTED_JOIN differs from the regeneration')
    refusals = controls(out, lisp_text, c_text, ledger, layout, built, joined, evidence_root, aggregate, frames_text, node)
    save(out / 'controls.json', refusals)
    observations = dict(schema=summary, join=jsummary, counts=built['counts'], controls=[r['control'] for r in refusals], aggregate=Path(aggregate).name)
    save(out / 'observations.json', observations)
    save(out / 'summary.json', dict(version=1, id=ID, variant=VARIANT, status='PASS', scope=SCOPE, review_disposition='NOT_REVIEWED', **observations))
    return observations


def retain(p, x, replay=False):
    if replay: require(read(p) == x, 'RETAINED ' + p.name)
    else: save(p, x)


def slot(out, replay=False):
    inv = read(out / 'inventory.json'); inv['tests'] = [t for t in inv['tests'] if t['id'] == ID or t['id'] in J.PREREQUISITES]; retain(out / 'slot-inventory.json', inv, replay)
    p = subprocess.run([sys.executable, str(TOOLS / 'gate.py'), '--inventory', str(out / 'slot-inventory.json'), '--results', str(out / 'results.json')], capture_output=True, text=True, timeout=30)
    value = dict(exit_code=p.returncode, result=json.loads(p.stdout), stderr=p.stderr)
    expected = [('unreviewed ' if t['id'] == ID else 'missing ') + t['id'] + ' [' + v + ']' for t in inv['tests'] for v in t['variants']]
    require(value == dict(exit_code=2, result=dict(status='BLOCKED', reasons=expected), stderr=''), 'SLOT_GATE ' + json.dumps(value['result'])); return value


def omissions(out, replay=False):
    inv = read(out / 'slot-inventory.json'); base = read(out / 'results.json'); results = []; test = next(t for t in inv['tests'] if t['id'] == ID)
    for role in list(dict.fromkeys(inv['required_record_roles'] + test.get('required_record_roles', []))):
        report = copy.deepcopy(base); report['results'][0]['artifacts'] = [a for a in report['results'][0]['artifacts'] if a['role'] != role]
        p = out / ('omit-' + role + '.json'); retain(p, report, replay)
        run = subprocess.run([sys.executable, str(TOOLS / 'gate.py'), '--inventory', str(out / 'slot-inventory.json'), '--results', str(p)], capture_output=True, text=True, timeout=30)
        value = json.loads(run.stdout)
        require(run.returncode == 1 and not run.stderr and value['status'] == 'FAIL' and value['reasons'][0] == 'missing artifact roles: ' + ID + ' [' + VARIANT + ']', 'ROLE_OMISSION ' + role)
        results.append(dict(role=role, exit_code=run.returncode, result=value))
    retain(out / 'role-omissions.json', results, replay)


def role(out, p):
    rel = p.relative_to(out).parts
    if rel[0] == 'quarantine': return 'negative_control'
    if rel[0] == 'source':
        if p.name in ('run.py', 'gate.py', 'evidence_binding.py'): return 'test'
        if p.name in ('derive.py', 'schema.py', 'join.py', 'ownership.mjs'): return 'implementation'
        return 'schema'
    if p.name in ('wasm32-layout.v1.json', 'runtime-contracts.v1.json', 'inventory.json'): return 'schema'
    return 'log'


def run(out):
    require(ROOT not in out.parents and out != ROOT and not out.exists(), 'FRESH_OUTPUT_OUTSIDE_CHECKOUT')
    snapshots = {str(p.relative_to(ROOT)): p.read_bytes() for p in sources()}
    source_sha = {str(p.relative_to(ROOT)): sha(p) for p in sources()}
    record = dict(version=1, status='FAIL', command=[sys.executable, *sys.argv], timestamp=datetime.now(timezone.utc).isoformat(), source_sha256=source_sha)
    try:
        invpath = DOCS / 'stage0/inventory.json'; inv = read(invpath); test = next(t for t in inv['tests'] if t['id'] == ID)
        require(test['runner'] == str(HERE.relative_to(ROOT) / 'run.py'), 'RUNNER_REGISTRATION')
        require(test['variants'] == [VARIANT] and test['evidence_kind'] == 'CONTROL EXECUTION', 'CONTRACT_REGISTRATION')
        exercise(out); (out / 'inventory.json').write_bytes(invpath.read_bytes()); (out / 'source').mkdir()
        for p in sources(): (out / 'source' / p.name).write_bytes(p.read_bytes())
        artifacts = [dict(path=p.relative_to(out).as_posix(), sha256=sha(p), role=role(out, p)) for p in sorted(out.rglob('*')) if p.is_file()]
        test_revision = hashlib.sha256(json.dumps(source_sha, sort_keys=True).encode()).hexdigest()
        report = dict(version=1, source_revision=inv['source_revision'], inventory_sha256=sha(out / 'inventory.json'), scope=SCOPE, results=[dict(
            id=ID, variant=VARIANT, source_revision=test['source_revision'], evidence_kind=test['evidence_kind'], status='PASS',
            assertions=[dict(id=a['id'], status='PASS') for a in test['assertions']], artifacts=artifacts, substitutions=[], skips=[], review_disposition='NOT_REVIEWED',
            command=record['command'], toolchain=read(out / 'environment.json'), engine='Python control execution with Node re-derivation of the retained ownership map; no Wasm executed',
            timestamp=record['timestamp'], configuration=dict(scope=SCOPE, schema='wasm32-layout v1', join='runtime-contracts v1', synthetic_inputs='quarantined copies only'),
            seed='deterministic; nine named synthetic mutations', test_revision=test_revision)])
        save(out / 'results.json', bind_report(report, inv, 'inventory.json', sha(out / 'inventory.json'))); save(out / 'slot-gate.json', slot(out)); omissions(out)
        require(record['source_sha256'] == {str(p.relative_to(ROOT)): sha(p) for p in sources()}, 'SOURCE_CHANGED')
        record.update(status='PASS', contract_sha256=contract_hash(inv, ID))
        print('PASS: CONTRACTS-a, schema and join regenerated identically, nine synthetic controls refused, four role omissions refused. Review pending.')
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
    temp = Path(tempfile.mkdtemp(prefix='ccl-contracts-verify-'))
    try:
        fresh = temp / 'replay'; observations = exercise(fresh)
        require(observations == read(packet / 'observations.json'), 'REPLAY_OBSERVATIONS')
        names = [p.relative_to(fresh) for p in fresh.rglob('*') if p.is_file() and p.name != 'environment.json']
        for n in names: require((fresh / n).read_bytes() == (packet / n).read_bytes(), 'REPLAY_BYTES ' + str(n))
        require(read(fresh / 'environment.json')['u1_pins'] == read(packet / 'environment.json')['u1_pins'], 'U1_PINS')
        require(slot(packet, True) == read(packet / 'slot-gate.json'), 'RETAINED_SLOT'); omissions(packet, True)
    except BaseException as e:
        save(temp / 'failure.json', dict(status='FAIL', packet=str(packet), source_sha256=record['source_sha256'], error=str(e)))
        print('Original verification failure retained at ' + str(temp), file=sys.stderr); raise
    else:
        shutil.rmtree(temp)
    print('PASS: schema and join regenerated; ' + str(len(names)) + ' identical deterministic files, U1 pins, direct pins and role refusals.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output', type=Path); g.add_argument('--verify', type=Path); g.add_argument('--generate', action='store_true', help='write the committed schema and join files from the current sources')
    a = p.parse_args()
    if a.generate:
        node = str(Path(shutil.which('node')).resolve())
        built = build_schema(LISP.read_text(), CHEADER.read_text(), read(HERE / 'dispositions.json'), read(LAYOUT)); S.check(built)
        COMMITTED_SCHEMA.write_text(canonical(built))
        joined = build_join(read(REPOSITORY)['path'], read(LEDGER)['combined_results'], FRAMES.read_text(), node); J.check(joined)
        COMMITTED_JOIN.write_text(canonical(joined)); print('generated', COMMITTED_SCHEMA, COMMITTED_JOIN)
    elif a.verify: verify(a.verify.resolve())
    else: run(a.output.resolve())
