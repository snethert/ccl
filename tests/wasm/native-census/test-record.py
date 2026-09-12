#!/usr/bin/env python3
"""Reject corrupted real evidence before a native acceptance envelope is emitted."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
from record import record
from reversible import digest, save


def controls(root, inventory):
    original = json.loads((root / 'results.json').read_text()); results = []
    with tempfile.TemporaryDirectory(prefix='ccl-native-record-controls-') as name:
        target = Path(name) / 'run'
        # Hard links are read-only inputs. Every mutated file is unlinked first;
        # never write through a link into the original evidence.
        shutil.copytree(root, target, copy_function=os.link)
        for n in ['gate-results.json', 'analysis.json', 'inventory.json']:
            (target / n).unlink(missing_ok=True)
        if (target / 'producer').exists(): shutil.rmtree(target / 'producer')
        def reject(label, mutate):
            report = copy.deepcopy(original); mutate(report)
            save(target / 'results.json', report)
            try: record(target.resolve(), inventory)
            except ValueError as exc: reason = str(exc)
            else: raise AssertionError('corrupt evidence accepted: ' + label)
            assert not (target / 'gate-results.json').exists() and not (target / 'producer').exists()
            results.append({'name': label, 'status': 'REJECTED', 'reason': reason})
        reject('missing executed observer identity', lambda r: r.update(
            artifacts=[a for a in r['artifacts'] if a['path'] != 'runner/observer.lisp']))
        reject('duplicate artifact identity', lambda r: r['artifacts'].append(r['artifacts'][0]))
        reject('escaping artifact path', lambda r: r['artifacts'][0].update(path='../outside'))
        reject('incomplete native tests', lambda r: r['observed_tests'].update(failed=1))
        reject('boot image absent from restoration', lambda r: r['clean_output_restoration'].update(files=166))
        mutated = target / 'observed-snapshot.jsonl'; rows = [json.loads(l) for l in mutated.read_text().splitlines()]
        rows[0]['payload']['operators'][1]['flags'] += 1
        mutated.unlink(); mutated.write_text(''.join(json.dumps(r) + '\n' for r in rows))
        reject('evaluated flags corrupted with matching artifact digest', lambda r: next(
            a for a in r['artifacts'] if a['path'] == 'observed-snapshot.jsonl').update(sha256=digest(mutated)))
    return {'status': 'PASS', 'controls': results, 'original_run_sha256': digest(root / 'results.json')}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True); p.add_argument('--inventory', type=Path, required=True)
    a = p.parse_args(); print(json.dumps(controls(a.run.resolve(), a.inventory.resolve()), indent=2))
