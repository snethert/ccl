"""Bind new executions to whole-file modules and final proposed sources."""
from pathlib import Path
import hashlib
import json
import sys
import tarfile
import backend

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def originals(rows):
    return {r['definition'] for r in rows if not r.get('targetOnly')
            and not r.get('nativeCounterpart') and not r['definition'].startswith('CORE-')
            and r['definition'] not in {'EQL', 'FULLTAG', 'LISPTAG', 'TYPECODE', 'ASSQ'}}


def summarize(numeric, environment, native):
    with tarfile.open(backend.PACKET / 'artifacts.tar.gz') as archive:
        previous = originals(json.load(archive.extractfile('numeric/compiled/native.json')))
    rows = read(numeric / 'compiled/native.json')
    current = originals(rows)
    assert previous <= current, sorted(previous - current)
    required = {'MINUSP', 'MULTIPLY-BIGNUM-AND-FIXNUM', '%BIGNUM-BIGNUM-GCD',
                '%POSITIVE-BIGNUM-BIGNUM-GCD', 'BIGNUM-FIXNUM-GCD',
                'INVOKE-RESTART', 'FIND-RESTART', 'RESTART-NAME',
                'APPLICABLE-RESTART-P', '%ACTIVE-RESTART'}
    assert required <= current, sorted(required - current)
    probes = {r['definition'] for r in rows if r['definition'].startswith('CORE-')}
    assert {'CORE-CONDITION-CONSTRUCTION', 'CORE-RESTART-ASSOCIATION',
            'CORE-RESTART-EXTRA-ARGUMENT', 'CORE-NUMERIC-RESTART-CAUGHT',
            'CORE-NUMERIC-RESTART-USE', 'CORE-NUMERIC-RESTART-TWICE',
            'CORE-NUMERIC-RESTART-HOOK'} <= probes
    workers = read(numeric / 'execution.json')['rows']
    assert len(workers) == 2 and sum(w['comparisons'] for w in workers) == 4 * len(rows)
    report = read(native / 'run.json')
    assert report['status'] == 'PASS' and report['registered_tests']['passed'] == 21843
    assert report['restored_fasls'] == 164 and report['source_restored']
    for name, text in {backend.BACKEND: backend.generate(), backend.ARCH: backend.arch(),
                       **backend.source_files(ROOT)}.items():
        for directory in (native / 'proposal', numeric / 'compiled/proposal', environment / 'proposal'):
            assert (directory / 'files' / name).read_text() == text, (name, directory)
    for source in HERE.glob('*.lisp'):
        copied = numeric / 'driver' / source.name
        if copied.exists():
            assert copied.read_bytes() == source.read_bytes(), source.name
    # Removing exactly the Wasm-only arm and its complementary guard restores
    # the integrated source text, hence every existing reader sees the same forms.
    name = 'level-1/l1-error-signal.lisp'
    proposal = backend.source_files(ROOT)[name]
    needle = '  #+wasm32-target (%wasm-kernel-restart error-type args)\n  #-wasm32-target\n'
    assert proposal.count(needle) == 1
    assert proposal.replace(needle, '') == (ROOT / name).read_text()
    save(numeric / 'reader-proof.json', dict(status='PASS', path=name,
        method='Removing the sole wasm32-target arm and its complementary guard restores the integrated file byte for byte.',
        existing_targets='Every reader feature assignment without wasm32-target.',
        integrated_sha256=hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
        decoded_native=read(native / 'l1-error-signal-comparison.json')))
    whole = read(numeric / 'compiled/whole-file.json')
    installed = {m['name'] for m in read(numeric / 'compiled/modules.json')}
    proof = []
    for name in sorted(current - previous):
        matches = [r for r in whole if r['name'] == name and r['module'] in installed]
        assert len(matches) == 1, (name, matches)
        proof.append(dict(name=name, file=matches[0]['file'], module=matches[0]['module'],
                          cases=sum(r['definition'] == name for r in rows)))
    save(numeric / 'source-proof.json', proof)
    admitted = read(environment / 'summary.json')['old_cohort']
    with tarfile.open(backend.PACKET / 'artifacts.tar.gz') as archive:
        prior_files = json.load(archive.extractfile('environment/results.json'))
    before = {(f['file'], d['name']): d for f in prior_files for d in f['definitions']}
    after = {(f['file'], d['name']): d for f in read(environment / 'results.json')
             for d in f['definitions']}
    changes = [dict(file=k[0], name=k[1], before=before[k]['outcome'], after=after[k]['outcome'])
               for k in sorted(before.keys() & after.keys())
               if before[k]['outcome'] != after[k]['outcome']]
    save(numeric / 'admission-changes.json', changes)
    result = dict(status='PASS', original_definitions_executed=len(current),
                  non_nil_witness=len({r['definition'] for r in rows if r['definition'] in current
                    and not r.get('caught') and any(v is not None for v in r['values'])}),
                  new_executions=sorted(current - previous), admitted=admitted['admitted'],
                  denominator=admitted['definitions'], native_rows=len(rows),
                  comparisons=sum(w['comparisons'] for w in workers),
                  collections_during_calls=sum(w['internalCollections'] for w in workers),
                  retry_collections=sum(w['retryCollections'] for w in workers),
                  structural_collector_checks=read(numeric / 'istruct-checks.json')['checks'],
                  direct_digit_checks=sum(len(w['bignums']) for w in workers),
                  constructor_controls=5,
                  native_tests=21843, restored_fasls=164,
                  scope='Original CCL bignum GCD and numeric type-error restart execution. Generic GCD/ABS is still not closed. Native restart functions and their condition associations execute; the target has no machine frame pointer and custom kernel-restart hooks receive NIL. The fallback supports canonical numeric type names only. The excluded read-time EXIT still stops l1-error-signal after the selected definitions. Method selection, real condition CPL tests, image startup and READY remain owed. No LL15 credit.')
    save(numeric / 'summary.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    summarize(*(Path(p).resolve() for p in sys.argv[1:]))
