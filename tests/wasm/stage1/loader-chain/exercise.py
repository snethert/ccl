"""Execute an ordered image with appended cases, witnesses and controls."""
from pathlib import Path
import hashlib
import json
import os
import shutil

HERE = Path(__file__).resolve().parent


def run(out, product, cases, witnesses, controls, inputs, startup_refusals=None, pending_cases=None):
    c = product.c
    assert c.read(out / 'proposal-inputs.json') == inputs
    pins = {n: hashlib.sha256(b.encode()).hexdigest() for n,b in product.sources().items()}
    assert c.read(out / 'identity.json')['source_identity'] == pins
    product.prepare_runtime(out / 'runtime')
    product.runtime(out / 'runtime')
    product.module('hash_leaves', HERE.parent / 'loader-def/hash-leaves.py').prepare(out)
    for folder, name, target in (
        ('loader-chain', 'execute.mjs', 'execute.mjs'),
        ('loader', 'write.mjs', 'write.mjs'), ('loader', 'd2.mjs', 'd2.mjs'),
        ('loader-locks', 'controls.mjs', 'lock-controls.mjs'),
        ('loader-aref', 'controls.mjs', 'controls.mjs'),
        ('loader-new-ptr', 'controls.mjs', 'pointer-controls.mjs'),
        ('loader-def', 'controls.mjs', 'definition-controls.mjs'),
        ('loader-def', 'hash-leaves.mjs', 'hash-leaves.mjs')):
        shutil.copyfile(HERE.parent / folder / name, out / target)
    imports = []
    for i, path in enumerate(controls):
        name = 'extension-' + str(i) + '.mjs'
        shutil.copyfile(path, out / name)
        imports.append("import {controls as c%d} from './%s';" % (i, name))
    (out / 'extra-controls.mjs').write_text('\n'.join(imports) + '\nexport const controls=ctx=>[' +
        ','.join('...c%d(ctx)' % i for i in range(len(controls))) + '];\n')
    c.save(out / 'cases.json', cases)
    c.save(out / 'startup-refusals.json', startup_refusals or [])
    c.save(out / 'pending-cases.json', pending_cases or {})
    c.save(out / 'policy.json', c.read(c.STORE / '2026-09-20-stage1-materialization-r1/execution/policy.json'))
    c.save(out / 'versions.json', dict(abi=dict(name='B', version=1), layout=dict(version=1,
        sha256=c.sha(c.ROOT / 'doc/WASM/contracts/wasm32-layout.v1.json'))))
    driver = product.module('chain_loader', HERE.parent / 'loader/run.py')
    artifacts = out / 'prefix/artifacts'
    written = driver.node([out / 'write.mjs', out / 'prefix', artifacts,
                           out / 'policy.json', out / 'versions.json'], out / 'write.log')
    native = out / 'native'; native.mkdir(exist_ok=True)
    support = out / 'native-source'; support.mkdir(exist_ok=True)
    for name in ('keywords.lisp', 'package-first.lisp', 'package-second.lisp', 'native.lisp'):
        shutil.copyfile(HERE.parent / 'loader-level0' / name, support / name)
    (support / 'packages.lisp').write_text('\n'.join(p.read_text() for p in witnesses))
    def form(value):
        if isinstance(value, dict):
            return '(:symbol ' + ' '.join(json.dumps(x) for x in value['symbol']) + ')'
        return str(value)
    (native / 'cases.lisp').write_text('(' + '\n'.join('(' + json.dumps(x['id']) + ' ' +
        ' '.join(json.dumps(n) for n in x['call']) + ' (' + ' '.join(form(a) for a in x['args']) + '))' for x in cases) + ')\n')
    c.command([out / 'dx86cl64', '-I', c.IMAGE, '--no-init', '--batch', '--load', support / 'native.lisp'],
        native / 'native.log', dict(os.environ, CCL_DEFAULT_DIRECTORY=str(c.ROOT) + '/',
            LOADER_SOURCE=str(support) + '/', LOADER_OUTPUT=str(native) + '/'), timeout=180)
    oracle = c.read(native / 'native.json')
    modes = {}
    for mode in ('plain', 'collect', 'relocate', 'relocate-collect'):
        flags = (['--collect'] if 'collect' in mode else []) + (['--relocate'] if 'relocate' in mode else [])
        row = driver.node([out / 'execute.mjs', artifacts, out / 'runtime', out / 'cases.json', *flags], out / (mode + '.log'))
        failed = {r['id'] for r in row['failures']}
        expected = [r for r in oracle if r['id'] not in failed]
        assert row['observations'] == expected, (mode, [(a,b) for a,b in zip(row['observations'],expected) if a != b])
        for failure in row['failures']:
            failure['native_expected'] = next(r['values'] for r in oracle if r['id'] == failure['id'])
        modes[mode] = row
    result = dict(status='INCOMPLETE' if any(r['failures'] for r in modes.values()) else 'WITNESSES_PASS_STARTUP_INCOMPLETE' if startup_refusals else 'PASS', source_identity=pins, runtime=c.read(out / 'runtime/array-runtime.json'),
        artifacts=written, native=oracle, runs=modes, ordered=c.read(out / 'ordered.json'),
        whole_file=c.read(out / 'whole-file.json')['whole_file'], slot_credit=False)
    c.save(out / 'summary.json', result)
    print({name: (r['modules'], r['initializersExecuted'], len(r['observations']), r['collections']) for name,r in modes.items()})
    return result
