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
    # Authenticate the retained input once. Controls then alter semantic input
    # in memory; they do not copy or rehash the baseline image/trace pack.
    baseline = module.reconcile(source)
    original = json.loads((source / 'trace.json').read_text())
    original_raw = (source / 'fs_usage.log').read_text()
    results = []
    controls = ['unchanged', 'missing-image-open', 'missing-native-read-open',
                'image-errno', 'wrong-native-pid', 'unparsed-loss',
                'wrong-base-fd', 'wrong-dyld-fd', 'different-thread',
                'lisp-path-in-chain', 'failed-directory-open',
                'missing-dyld-prefix', 'missing-cache-witness',
                'missing-descriptor-close', 'after-image-open',
                'unrelated-anonymous-open']
    for control in controls:
        d = json.loads(json.dumps(original)); raw = original_raw
        image = d['client_command'][d['client_command'].index('--image-name') + 1]
        if control == 'missing-image-open': raw = '\n'.join(l for l in raw.splitlines() if not (' open ' in l and image in l)) + '\n'
        if control == 'missing-native-read-open': raw = '\n'.join(l for l in raw.splitlines() if not (' open ' in l and 'native-control-read.txt' in l)) + '\n'
        if control == 'image-errno': raw = '\n'.join(l.replace('F=3', '[  2]') if ' open ' in l and image in l else l for l in raw.splitlines()) + '\n'
        if control == 'wrong-native-pid': d['native_pid'] += 1
        if control == 'unparsed-loss': raw += 'LOST 42 EVENTS\n'
        if control == 'wrong-base-fd': raw = raw.replace('[3]/../../System/', '[9]/../../System/')
        if control == 'wrong-dyld-fd': raw = raw.replace('[4]/System/Library/dyld', '[9]/System/Library/dyld', 1)
        witness = baseline['dyld_directory_contexts'][0]
        lines = raw.splitlines()
        base, cryptex, stat, directory = [n - 1 for n in witness['classified_lines']]
        if control == 'different-thread': lines[stat] = lines[stat].rsplit('.', 1)[0] + '.9999999'
        if control == 'lisp-path-in-chain': lines[directory] = lines[directory].replace('/System/Library/dyld', '/application/startup.lisp')
        if control == 'failed-directory-open': lines[directory] = lines[directory].replace('F=6', '[  2]')
        if control == 'missing-dyld-prefix': lines[base - 1] = lines[base - 1].replace('/usr/lib/dyld', '/application/data')
        if control == 'missing-cache-witness': lines[base + 9] = lines[base + 9].replace('dyld_shared_cache_x86_64h', 'unrelated-file')
        if control == 'missing-descriptor-close': lines.pop(base + 8)
        if control == 'after-image-open':
            image_index = next(i for i, l in enumerate(lines) if ' open ' in l and image in l)
            lines.insert(base - 1, lines.pop(image_index))
        if control == 'unrelated-anonymous-open': lines.append(lines[base])
        raw = '\n'.join(lines) + '\n'
        try:
            report = module.reconcile_events(source, d, raw)
        except ValueError as exc:
            if control not in controls[1:6]: raise
            result = {'control': control, 'status': 'REJECTED', 'reason': str(exc)}
        else:
            if control in controls[1:6]: raise ValueError('coverage control escaped: ' + control)
            unresolved = report['unresolved_path_contexts']
            classified = report['classification_counts'].get('host-dyld-directory-context', 0)
            if control == 'unchanged':
                if unresolved or classified != 4: raise ValueError('retained loader chain not reconciled')
                save(output / 'reconciliation.json', report)
                result = {'control': control, 'status': 'PASS', 'classified_loader_operations': classified}
            else:
                expected = 4 if control == 'unrelated-anonymous-open' else 0
                if not unresolved or classified != expected:
                    raise ValueError('loader context control escaped: ' + control)
                if control == 'lisp-path-in-chain' and not any(r['path'].endswith('/application/startup.lisp') for r in unresolved if r['path']):
                    raise ValueError('application path was concealed')
                result = {'control': control, 'status': 'REJECTED',
                          'reason': 'Unresolved pathname context retained',
                          'unresolved_contexts': len(unresolved),
                          'classified_loader_operations': classified}
        results.append(result)
    save(output / 'results.json', {'status': 'PASS', 'controls': results, 'source_trace_sha256': digest(source / 'trace.json')})
    return results


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trace', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); print(json.dumps(run(a.trace.resolve(), a.output.resolve()), indent=2))
