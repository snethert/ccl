#!/usr/bin/env python3
"""Materialize the existing B desk decision; reuse accepted runtime evidence."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TOOLS = ROOT/'doc/WASM/tools'
sys.path.insert(0, str(TOOLS))
from evidence_binding import bind_report, binding_errors, contract_hash, safe_path

ID = 'S0-ABI-selection'


def read(p): return json.loads(p.read_text())
def save(p, x): p.write_text(json.dumps(x, indent=2, ensure_ascii=False)+'\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(value, reason):
    if not value: raise ValueError(reason)


def dependencies(inventory):
    tests = {t['id']: t for t in inventory['tests']}
    found = set()
    def visit(i):
        if i in found: return
        found.add(i)
        for dep in tests[i]['prerequisites']: visit(dep)
    visit(ID)
    return {(i, v) for i in found if i != ID for v in tests[i]['variants']}


def check_records(inventory, records):
    expected = dependencies(inventory)
    require(len(records) == len(expected) and {(r['id'], r['variant']) for r in records} == expected,
            'PREREQUISITE_SET')
    tests = {t['id']: t for t in inventory['tests']}
    for r in records:
        t = tests[r['id']]
        require(r['status'] == 'PASS' and r['review_disposition'] == 'ACCEPTED' and r['review_record'],
                'PREREQUISITE_ACCEPTANCE')
        require(r['source_revision'] == t['source_revision'] and r['evidence_kind'] == t['evidence_kind'] and
                r['substitutions'] == [] and r['skips'] == [], 'PREREQUISITE_SCOPE')
        require(r['assertions'] == [dict(id=a['id'], status='PASS') for a in t['assertions']],
                'PREREQUISITE_ASSERTIONS')
        require(r['contract_binding']['contract_sha256'] == contract_hash(inventory, r['id']),
                'PREREQUISITE_CONTRACT')


def check(d, inventory, records, inputs):
    check_records(inventory, records)
    policy, old, timing, bounds = (inputs[k] for k in ('policy', 'old_policy', 'exploratory', 'bounds'))
    require(d['version'] == 1 and d['id'] == ID and d['selected_abi'] == policy['selected_abi'] == 'B' and
            d['basis'] == 'PROJECT_DECISION' and d['decision_date'] == '2026-09-12' and
            d['rationale'] and d['user_direction'] and d['direction_provenance'], 'PROJECT_DIRECTION')
    require(d['abi'] == dict(parameters=['self:i32', 'nargs:i32'], results=['value0:i32', 'nvalues:i32'],
        tagged_values=['self', 'arguments', 'value0'], counts='raw unsigned i32', argument_parameter_count=0,
        argument_address='incoming_VSP + 4*i, for 0 <= i < nargs', argument_extent='align16(4*nargs)',
        argument_owner='caller; callee restores incoming VSP before the caller releases it', zero_values='(NIL, 0)',
        extra_values='caller-owned rooted VSP region referenced by the TCR multiple-value descriptor; lifetime ends on owner reuse or release',
        nested_values='copy earlier retained results to owned rooted storage before reusing the output region',
        result_scanners='exactly one scanner per physical result slot; ownership handoffs occur without polling'), 'B_PROTOCOL')
    require(d['performance'] == dict(policy_v2_rule_applied=False, policy_v2_minima_met=False,
        demonstrated_speed_superiority=False, comparative_timing='DEFERRED',
        sensitivity_and_comparison_instrumentation='DEFERRED', required_before_B_implementation=False) and
        policy['version'] == 3 and policy['comparative_measurements_required_for_implementation'] is False,
        'NO_MEASUREMENT_SELECTION')
    require(old['version'] == 2 and all(r['selection'] == 'NO_SELECTION' and
        r['paired_trials'] < old['minimum_independent_trials'] for r in timing['summaries'].values()) and
        set(timing['summaries']) == {'direct', 'same-instance', 'cross-instance'}, 'ORIGINAL_NO_SELECTION')
    require(d['alternatives'] == ['C', 'C4'] and d['optional_future_enhancement'] == 'H(G)' and
        d['retained_basis'] == ['accepted', 'exploratory', 'old_policy', 'policy_change'], 'ALTERNATIVES_AND_RETENTION')
    expected = {k: bounds['bounds'][k] for k in ('maximum_arguments', 'maximum_values', 'frame_bytes', 'stack_bytes', 'tail_iterations')}
    expected.update({k: bounds[k] for k in ('memory_bytes', 'live_workers', 'ownership_slots')})
    expected['scope'] = 'HAND_BUILT_CORRECTNESS_ONLY'
    require(d['fixture_limits'] == expected and d['runtime_execution_claimed'] is False and
            d['compiler_authorization_changed'] is False and d['review_disposition'] == 'NOT_REVIEWED', 'BOUNDED_SCOPE')
    require(d['module_granularity'] == dict(
        correctness_fixture='one callable definition per module plus support/runtime; cross-instance indirect dispatch',
        initial_generated_bootstrap='proposed small number of coherent, eagerly installed bundles',
        production_partition='OPEN_STAGE1_DECISION', measured_advantage=False), 'GRANULARITY')
    require(d['continuing_obligations'] == [
        'publish live roots at stopping boundaries; reload moved values and rederive addresses',
        'preserve logical debugger frames, source identity and declared availability policy',
        'preserve VSP/TSP/CSP, result ownership, bindings, handlers and cleanup across tails, callbacks and exceptions',
        'validate code versions, entry roles, signatures and installation before publication',
        'confirm the selected B protocol through real compiler-generated code',
        'complete the independent engine matrix, census and contracts join',
        'measure startup, scale and memory with useful generated code'] and
        d['publication_limit'] == 'S0-LL21-a publishes a generation and code/version digest; every Worker already holds the bytes. It proves neither byte delivery nor Wasm-side acquire.', 'CONTINUING_OBLIGATIONS')
    require(d['reopen_for'] == ['demonstrated generated-code correctness problem attributable to B',
        'representative performance problem attributable to B'] and d['future_comparison_requires'] == [
        'positive sensitivity control', 'representative workload weights', 'declared granularity and engine tier',
        'required trials and metrics'], 'REVERSAL_CRITERIA')
    return [dict(id=ID+':'+str(i), status='PASS') for i in range(1, 5)]


def controls(d, inventory, records, inputs):
    cases = [
        ('omitted-prerequisite', 'PREREQUISITE_SET', lambda d, r: r.pop()),
        ('duplicate-masks-prerequisite', 'PREREQUISITE_SET', lambda d, r: r.__setitem__(-1, copy.deepcopy(r[0]))),
        ('unaccepted-prerequisite', 'PREREQUISITE_ACCEPTANCE', lambda d, r: r[0].update(review_disposition='NOT_REVIEWED')),
        ('wrong-prerequisite-contract', 'PREREQUISITE_CONTRACT', lambda d, r: r[0]['contract_binding'].update(contract_sha256='0'*64)),
        ('argument-split', 'B_PROTOCOL', lambda d, r: d['abi'].update(argument_parameter_count=3)),
        ('benchmark-rule-claim', 'NO_MEASUREMENT_SELECTION', lambda d, r: d['performance'].update(policy_v2_rule_applied=True)),
        ('speed-superiority-claim', 'NO_MEASUREMENT_SELECTION', lambda d, r: d['performance'].update(demonstrated_speed_superiority=True)),
        ('unbounded-capacity-claim', 'BOUNDED_SCOPE', lambda d, r: d['fixture_limits'].update(maximum_arguments='unbounded')),
        ('production-partition-freeze', 'GRANULARITY', lambda d, r: d['module_granularity'].update(production_partition='FROZEN')),
        ('omitted-generated-code-obligation', 'CONTINUING_OBLIGATIONS', lambda d, r: d['continuing_obligations'].pop(4))]
    result = []
    for name, reason, mutate in cases:
        changed, rows = copy.deepcopy(d), copy.deepcopy(records)
        mutate(changed, rows)
        try: check(changed, inventory, rows, inputs)
        except ValueError as e: require(str(e) == reason, 'WRONG_CONTROL_REASON '+name)
        else: raise ValueError('CONTROL_ESCAPED '+name)
        result.append(dict(name=name, status='REJECTED', reason=reason))
    return result


def collect(store, inventory):
    pins = read(HERE/'inputs.json')
    values = {}
    for row in pins['local']:
        path = safe_path(row['path'])
        data = (subprocess.check_output(['git', 'show', row['revision']+':'+path], cwd=ROOT)
                if 'revision' in row else (ROOT/path).read_bytes())
        require(hashlib.sha256(data).hexdigest() == row['sha256'], 'LOCAL_INPUT '+path)
    for name, row in pins['evidence'].items():
        p = store/safe_path(row['path']); require(sha(p) == row['sha256'], 'RETAINED_INPUT '+name)
        values[name] = read(p)
    values.update(policy=read(ROOT/'doc/WASM/stage0/benchmarks.json'), bounds=read(ROOT/'doc/WASM/evidence/dynamic-call-summary.json'))
    require(values['policy_change']['policy_old_sha256'] == pins['evidence']['old_policy']['sha256'] and
            values['policy_change']['policy_new_sha256'] == sha(ROOT/'doc/WASM/stage0/benchmarks.json') and
            values['exploratory']['policy_sha256'] == pins['evidence']['old_policy']['sha256'], 'POLICY_IDENTITY')
    report = values.pop('accepted')
    # Read metadata and original inventory snapshots, not runtime artifact payloads.
    errors = binding_errors(inventory, report, lambda name: (store/safe_path(name)).read_bytes())
    require(not errors, 'ACCEPTED_BINDINGS '+str(errors))
    keys = [(r['id'], r['variant']) for r in report['results']]
    require(len(keys) == len(set(keys)) and all(r['status'] == 'PASS' and r['review_disposition'] == 'ACCEPTED' and
            r.get('review_record') for r in report['results']), 'ACCEPTED_LEDGER')
    wanted = dependencies(inventory)
    rows = [{k: r[k] for k in ('id', 'variant', 'status', 'review_disposition', 'review_record', 'source_revision',
        'evidence_kind', 'assertions', 'substitutions', 'skips', 'contract_binding', 'configuration', 'timestamp', 'engine')}
        for r in report['results'] if (r['id'], r['variant']) in wanted]
    check_records(inventory, rows)
    basis = dict(accepted_envelope=pins['evidence']['accepted'], records=rows,
        accepted_pairs=[list(k) for k in keys], accepted_record_count=len(keys), all_accepted_bindings_current=True,
        prior_runtime_verification='Reused; no runtime payload rescan or re-execution.')
    return values, basis


def run(out, store):
    require(out != ROOT and ROOT not in out.parents and out != store and store not in out.parents,
            'USE_NEW_OUTPUT_OUTSIDE_REPOSITORIES')
    out.mkdir(parents=True, exist_ok=False)
    record = dict(version=1, operation='MATERIALIZE_DESK_DECISION_NO_RUNTIME_EXECUTION', status='FAIL',
                  command=[sys.executable, *sys.argv], timestamp=datetime.now(timezone.utc).isoformat())
    try:
        inventory = read(ROOT/'doc/WASM/stage0/inventory.json')
        test = next(t for t in inventory['tests'] if t['id'] == ID)
        require(test['runner'] == str(HERE.relative_to(ROOT)/'run.py') and test['evidence_kind'] == 'DESK DECISION' and
                test['variants'] == ['complete-report'], 'REGISTERED_DESK_CONTRACT')
        sources = [HERE/p for p in ('run.py', 'decision.json', 'inputs.json')] + [TOOLS/'gate.py', TOOLS/'evidence_binding.py']
        record['source_sha256'] = {str(p.relative_to(ROOT)): sha(p) for p in sources}
        (out/'source').mkdir()
        for p in sources: (out/'source'/p.name).write_bytes(p.read_bytes())
        (out/'inventory.json').write_bytes((ROOT/'doc/WASM/stage0/inventory.json').read_bytes())
        d = read(HERE/'decision.json'); inputs, basis = collect(store, inventory)
        assertions = check(d, inventory, basis['records'], inputs)
        require(assertions == [dict(id=a['id'], status='PASS') for a in test['assertions']], 'DESK_ASSERTION_SET')
        save(out/'basis.json', basis); save(out/'controls.json', controls(d, inventory, basis['records'], inputs))
        save(out/'decision.json', d)
        save(out/'summary.json', dict(status='PASS', evidence_kind='DESK DECISION', assertions=assertions,
            prerequisite_variants=len(basis['records']), accepted_bindings_checked=basis['accepted_record_count'],
            negative_controls=10, runtime_executions=0, review_disposition='NOT_REVIEWED'))
        env = dict(python=sys.version, executable=sys.executable, executable_sha256=sha(Path(sys.executable).resolve()),
                   platform=platform.platform())
        save(out/'environment.json', env)
        artifacts = [dict(path=str(p.relative_to(out)), sha256=sha(p), role=(
            'implementation' if p.name in ('decision.json', 'evidence_binding.py') else 'test' if p.name in ('run.py', 'gate.py') else
            'schema' if p.name in ('inventory.json', 'inputs.json') else 'log')) for p in sorted(out.rglob('*')) if p.is_file()]
        result = dict(id=ID, variant='complete-report', source_revision=test['source_revision'], evidence_kind='DESK DECISION',
            status='PASS', assertions=assertions, artifacts=artifacts, substitutions=[], skips=[], review_disposition='NOT_REVIEWED',
            command=record['command'], toolchain=env, engine='Not applicable: desk decision; no engine execution', timestamp=record['timestamp'],
            configuration='Existing 12 September B project choice; accepted correctness reused at original bounds; no measurement selection',
            seed='Not applicable: deterministic desk checks', test_revision=sha(HERE/'run.py'))
        report = bind_report(dict(version=1, source_revision=inventory['source_revision'], inventory_sha256=sha(out/'inventory.json'),
            results=[result]), inventory, 'inventory.json', sha(out/'inventory.json'))
        save(out/'results.json', report)
        argv = [sys.executable, str(TOOLS/'gate.py'), '--inventory', str(out/'inventory.json'), '--results', str(out/'results.json')]
        p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=30)
        result = json.loads(p.stdout)
        save(out/'gate-command.json', dict(argv=argv, exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr))
        expected = [('unreviewed' if t['id'] == ID else 'missing')+' '+t['id']+' ['+v+']'
                    for t in inventory['tests'] for v in t['variants']]
        require(p.returncode == 2 and not p.stderr and result == dict(status='BLOCKED', reasons=expected), 'NEW_RECORD_GATE')
        # Compose only status metadata with the pinned accepted set; original envelopes are untouched.
        accepted = {tuple(pair) for pair in basis['accepted_pairs']}
        missing = ['missing '+t['id']+' ['+v+']' for t in inventory['tests'] for v in t['variants']
                   if (t['id'], v) not in accepted and t['id'] != ID]
        save(out/'gate-result.json', dict(version=1, assessment='SCOPED_DESK_RECORD',
            basis='Production gate validates new record and its artifacts; pinned accepted envelope and current bindings reused. No full combined artifact rescan.',
            result=dict(status='BLOCKED', reasons=missing+['unreviewed '+ID+' [complete-report]']),
            counts=dict(accepted=len(accepted), missing=len(missing), unreviewed=1, required=len(expected))))
        require(record['source_sha256'] == {str(p.relative_to(ROOT)): sha(p) for p in sources}, 'SOURCE_CHANGED_DURING_RUN')
        record.update(status='PASS', contract_sha256=contract_hash(inventory, ID))
        print('PASS: B desk decision, '+str(len(basis['records']))+' accepted prerequisite variants, 10 rejected controls; no runtime execution.')
    except BaseException as e:
        record['error'] = type(e).__name__+': '+str(e)
        raise
    finally: save(out/'run.json', record)


def verify(packet, store):
    record = read(packet/'run.json'); require(record['status'] == 'PASS', 'RUN_STATUS')
    for name, expected in record['source_sha256'].items(): require(sha(ROOT/name) == expected, 'SOURCE_PIN '+name)
    report = read(packet/'results.json')
    for a in report['results'][0]['artifacts']: require(sha(packet/safe_path(a['path'])) == a['sha256'], 'ARTIFACT '+a['path'])
    inventory = read(ROOT/'doc/WASM/stage0/inventory.json')
    inputs, basis = collect(store, inventory); require(basis == read(packet/'basis.json'), 'BASIS')
    d = read(packet/'decision.json')
    require(check(d, inventory, basis['records'], inputs) == report['results'][0]['assertions'], 'ASSERTIONS')
    require(controls(d, inventory, basis['records'], inputs) == read(packet/'controls.json'), 'CONTROLS')
    require(not binding_errors(inventory, report, lambda name: (packet/safe_path(name)).read_bytes()), 'RESULT_BINDING')
    p = subprocess.run([sys.executable, str(TOOLS/'gate.py'), '--inventory', str(packet/'inventory.json'),
                        '--results', str(packet/'results.json')], cwd=ROOT, capture_output=True, text=True, timeout=30)
    retained = read(packet/'gate-command.json')
    require(p.returncode == retained['exit_code'] == 2 and not p.stderr and p.stdout == retained['stdout'], 'RETAINED_GATE')
    print('PASS: retained B desk decision, accepted prerequisite metadata, direct bindings and 10 controls; no runtime rescan.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence-root', type=Path, required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output', type=Path); g.add_argument('--verify', type=Path)
    a = p.parse_args()
    if a.verify: verify(a.verify.resolve(), a.evidence_root.resolve())
    else: run(a.output.resolve(), a.evidence_root.resolve())
