"""New generic functions may mutate; never substitute their final entry code."""
from copy import deepcopy
from pathlib import Path
from payloads import read, rows, save, require
from seed_bodies import final_reads


def run(native, bodies, output):
    changes = read(bodies / 'final-read-changes.json')
    ident = next(r['function'] for r in changes if not r['initial_object'] and r['execution_changed'])
    selected = []
    for row in rows(native / 'observed/registries.jsonl.gz'):
        if row['kind'] in ('registry-checkpoint', 'compiler-materialization') or row['kind'] in ('mutation-enter', 'mutation-leave') and row['gf']['gf'] == ident:
            selected.append(row)
        elif row['kind'] in ('function', 'final-function') and row['id'] == ident: selected.append(row)
    original = next(r for r in selected if r['kind'] == 'function')
    functions = {ident: original}
    result, changed = final_reads(functions, selected, set(), set())
    require(result[ident] == original and changed[0]['execution_changed'], 'REGISTRY_FIRST_STATE_REPLACED')
    checks = []

    def reject(name, fs, events, seeds):
        try: final_reads(fs, events, set(), seeds)
        except ValueError as error: require(str(error) == 'SEED_FINAL_EXECUTION_CHANGED', 'REGISTRY_CONTROL_REASON')
        else: raise ValueError('REGISTRY_CONTROL_ESCAPED ' + name)
        checks.append(dict(name=name, status='REJECTED'))

    reject('missing-registry-witness', functions,
           [r for r in selected if r['kind'] not in ('registry-checkpoint', 'mutation-enter', 'mutation-leave')], set())
    reject('claim-as-compiler-output', functions,
           selected + [dict(kind='compiler-materialization', functions=[dict(function=ident)])], set())
    reject('changed-selected-startup-entry', functions, selected, {ident})
    bad = deepcopy(functions); bad[ident]['bits'] &= ~(1 << 27)
    reject('ordinary-function-promoted-to-registry', bad, selected, set())
    save(output, dict(status='PASS', first_state_preserved=True, controls=checks))
    print('PASS: registry first state preserved,', len(checks), 'controls rejected')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('native', 'bodies', 'output'): p.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args(); run(a.native, a.bodies, a.output)
