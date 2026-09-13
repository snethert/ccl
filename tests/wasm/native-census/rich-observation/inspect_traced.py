#!/usr/bin/env python3
"""Inspect the exact externally traced clean image and its existing foreign tables."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def import_joins(rows, source):
    body = source.split('import_ptrs_start:', 1)[1].split('.globl C(import_ptrs_base)', 1)[0]
    symbols = []
    for line in body.splitlines():
        if not line.strip(): continue
        match = re.fullmatch(r'\s*defimport\((\w+)\)\s*', line)
        if not match: raise ValueError('unrecognized native import-table source row')
        symbols.append(match[1])
    if len(rows) != len(symbols) or [r['offset'] for r in rows] != list(range(0, 8 * len(symbols), 8)):
        raise ValueError('evaluated import offsets differ from the native table')
    if len({r['name'] for r in rows}) != len(rows): raise ValueError('duplicate import name')
    return [{**row, 'kernel_symbol': name} for row, name in zip(rows, symbols)]


def run(trace_path, previous_image, output):
    output.mkdir(parents=True, exist_ok=False)
    trace = json.loads(trace_path.read_text()); kernel = Path(trace['client_command'][0]); image = Path(trace['client_command'][2])
    if trace['client_command'][1] != '--image-name' or not trace['image_path_observed'] or trace['event_loss_reported']:
        raise ValueError('requires a trace with the exact retained image and no reported event loss')
    for path in (kernel, image):
        if sha(path) != trace['inputs_sha256'][str(path)]: raise ValueError('changed traced input: ' + str(path))
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin', 'LANG': 'C', 'LC_ALL': 'C',
           'CCL_DEFAULT_DIRECTORY': str(ROOT)}
    report = {'status': 'PASS', 'trace_record': str(trace_path), 'trace_sha256': sha(trace_path),
              'native_inputs_sha256': {str(p): trace['inputs_sha256'][str(p)] for p in (kernel, image)},
              'commands': [], 'inspector_sha256': {},
              'scope': 'Read-only inspection of the exact externally traced native image. Diagnostic functions are included. No new file trace, foreign resolution or library opening is claimed.'}
    for name, inspector, function in [('image', HERE.parent / 'startup-closure/image-inventory.lisp', 'ccl-image-inventory::inspect-image'),
                                       ('foreign', HERE / 'foreign-inventory.lisp', 'ccl-startup-census::inspect-foreign-surface')]:
        path = output / (name + '.json'); loads = [HERE.parent / 'observer.lisp', inspector]
        argv = [str(kernel), '--image-name', str(image), '--no-init', '--batch']
        for p in loads:
            argv += ['--load', str(p)]; report['inspector_sha256'][str(p)] = sha(p)
        argv += ['--eval', '(progn (' + function + ' ' + json.dumps(str(path)) + ') (ccl:quit))']
        with (output / (name + '.log')).open('wb') as log:
            result = subprocess.run(argv, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60)
        if result.returncode: raise ValueError(name + ' inspection failed; see log')
        report['commands'].append({'argv': argv, 'cwd': str(ROOT), 'environment': env,
                                   'exit_code': result.returncode, 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
    image_data = json.loads((output / 'image.json').read_text()); previous = json.loads(previous_image.read_text())
    comparison = {'previous_image': str(previous_image), 'previous_sha256': sha(previous_image),
                  'equal_fields': [k for k in image_data if image_data[k] == previous.get(k)],
                  'different_function_rows': [], 'scope': 'Inventory field comparison only; heap bytes remain separate identities.'}
    if len(image_data['functions']) != len(previous['functions']): raise ValueError('native image function inventory differs')
    for left, right in zip(image_data['functions'], previous['functions']):
        if left != right:
            comparison['different_function_rows'].append({'id': left['id'], 'differences': {
                k: [left[k], right.get(k)] for k in left if left[k] != right.get(k)}})
    (output / 'comparison.json').write_text(json.dumps(comparison, indent=2) + '\n')
    foreign = json.loads((output / 'foreign.json').read_text()); source = (ROOT / 'lisp-kernel/imports.s').read_text()
    joins = import_joins(foreign['kernel_imports'], source); controls = []
    for name, rows in [('missing-slot', foreign['kernel_imports'][:-1]),
                       ('wrong-offset', [dict(r, offset=r['offset'] + 8) for r in foreign['kernel_imports']]),
                       ('duplicate-name', [dict(r, name=foreign['kernel_imports'][0]['name']) for r in foreign['kernel_imports']])]:
        try: import_joins(rows, source)
        except ValueError as exc: controls.append({'name': name, 'status': 'REJECTED', 'reason': str(exc)})
        else: raise ValueError('native import-table control escaped: ' + name)
    (output / 'kernel-import-joins.json').write_text(json.dumps({'status': 'PASS', 'rows': joins, 'controls': controls,
            'scope': 'Evaluated native offsets joined to explicit U1 table order, not invoked or classified as Wasm implementations.'}, indent=2) + '\n')
    for p in (ROOT / 'lisp-kernel/imports.s', ROOT / 'compiler/X86/X8664/x8664-arch.lisp'):
        report.setdefault('table_source_sha256', {})[str(p)] = sha(p)
    report['summary'] = {'resident_functions': len(image_data['functions']), 'bindings': len(image_data['bindings']),
                         **{k: len(foreign[k]) for k in ('kernel_imports', 'entrypoints', 'foreign_variables', 'libraries')},
                         'import_controls_rejected': len(controls)}
    path = output / 'image.json'
    with path.open('rb') as src, gzip.open(str(path) + '.gz', 'wb') as dst: shutil.copyfileobj(src, dst)
    path.unlink()
    (output / 'run.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['summary']))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('trace', 'previous-image', 'output'): p.add_argument('--' + name, required=True, type=Path)
    args = p.parse_args(); run(args.trace.resolve(), args.previous_image.resolve(), args.output.resolve())
