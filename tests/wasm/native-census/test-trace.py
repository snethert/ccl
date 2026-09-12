#!/usr/bin/env python3
"""Check the reconciler against an actual trace and retained coverage mutants."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
from reversible import digest, save

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('reconcile_trace', HERE / 'reconcile-trace.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


def run(source, output):
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()): raise ValueError('output must be new and empty')
    shutil.copyfile(__file__, output / 'test-trace.py')
    shutil.copyfile(HERE / 'reconcile-trace.py', output / 'reconcile-trace.py')
    original = json.loads((source / 'trace.json').read_text()); results = []
    for control in ['unchanged', 'missing-image-open', 'missing-native-read-open', 'image-errno', 'wrong-native-pid', 'unparsed-loss']:
        dest = output / control; shutil.copytree(source, dest)
        d = json.loads(json.dumps(original).replace(str(source), str(dest)))
        raw = (dest / 'fs_usage.log').read_text().replace(str(source), str(dest))
        image = d['client_command'][d['client_command'].index('--image-name') + 1]
        if control == 'missing-image-open': raw = '\n'.join(l for l in raw.splitlines() if not (' open ' in l and image in l)) + '\n'
        if control == 'missing-native-read-open': raw = '\n'.join(l for l in raw.splitlines() if not (' open ' in l and 'native-control-read.txt' in l)) + '\n'
        if control == 'image-errno': raw = '\n'.join(l.replace('F=3', '[  2]') if ' open ' in l and image in l else l for l in raw.splitlines()) + '\n'
        if control == 'wrong-native-pid': d['native_pid'] += 1
        if control == 'unparsed-loss': raw += 'LOST 42 EVENTS\n'
        (dest / 'fs_usage.log').write_text(raw)
        # Keep artifact identities valid so each control tests the semantic
        # coverage check, not merely its file digest.
        for a in d['artifacts']: a['sha256'] = digest(dest / a['path'])
        save(dest / 'trace.json', d)
        try:
            report = module.reconcile(dest); save(dest / 'reconciliation.json', report)
        except ValueError as exc:
            if control == 'unchanged': raise
            result = {'control': control, 'status': 'REJECTED', 'reason': str(exc)}
        else:
            if control != 'unchanged': raise ValueError('coverage control escaped: ' + control)
            result = {'control': control, 'status': 'PASS'}
        save(dest / 'control.json', result); results.append(result)
    save(output / 'results.json', {'status': 'PASS', 'controls': results, 'source_trace_sha256': digest(source / 'trace.json')})
    return results


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trace', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); print(json.dumps(run(a.trace.resolve(), a.output.resolve()), indent=2))
