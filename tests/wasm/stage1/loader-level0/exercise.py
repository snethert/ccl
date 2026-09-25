"""Package and execute the full prefix and focused keyword witnesses."""
from pathlib import Path
import importlib.util
import json
import os
import shutil
import sys
import product
import storage

HERE = Path(__file__).resolve().parent
c = product.c


def helper(name):
    spec = importlib.util.spec_from_file_location('prefix_loader_' + name,
                                                HERE.parent / 'loader' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def native(out, cases):
    out.mkdir(parents=True, exist_ok=True)
    def form(value):
        if isinstance(value, dict):
            return '(:symbol ' + ' '.join(json.dumps(x) for x in value['symbol']) + ')'
        return str(value)
    rows = ['(' + json.dumps(x['id']) + ' ' + ' '.join(json.dumps(n) for n in x['call']) +
            ' (' + ' '.join(form(a) for a in x['args']) + '))' for x in cases]
    (out / 'cases.lisp').write_text('(' + '\n'.join(rows) + ')\n')
    kernel = out / 'dx86cl64'
    shutil.copyfile(c.KERNEL, kernel)
    kernel.chmod(0o755)
    c.command([kernel, '-I', c.IMAGE, '--no-init', '--batch', '--load', HERE / 'native.lisp'],
              out / 'native.log', dict(os.environ, LOADER_SOURCE=str(HERE) + '/',
                                      LOADER_OUTPUT=str(out) + '/'), timeout=120)
    kernel.unlink()
    return c.read(out / 'native.json')


def run(out):
    pins = c.read(out / 'identity.json')['source_identity']
    import hashlib
    assert pins == {n: hashlib.sha256(b.encode()).hexdigest() for n, b in product.sources().items()}
    product.prepare_runtime(out / 'runtime')
    for name in ('write.mjs', 'd2.mjs'):
        shutil.copyfile(HERE.parent / 'loader' / name, out / name)
    shutil.copyfile(HERE / 'execute.mjs', out / 'execute.mjs')
    c.save(out / 'policy.json', c.read(c.STORE / '2026-09-20-stage1-materialization-r1/execution/policy.json'))
    c.save(out / 'versions.json', dict(abi=dict(name='B', version=1),
                                     layout=dict(version=1, sha256=c.sha(c.ROOT / 'doc/WASM/contracts/wasm32-layout.v1.json'))))
    driver = helper('run')
    driver.runtime(out / 'runtime')
    results = {}
    for label, folder, cases_name in [('prefix', 'prefix', 'prefix-cases.json'),
                                      ('keywords', 'keywords', 'keyword-cases.json')]:
        artifacts = out / folder / 'artifacts'
        written = driver.node([out / 'write.mjs', out / folder, artifacts,
                               out / 'policy.json', out / 'versions.json'], out / (label + '-write.log'))
        cases = c.read(HERE / cases_name)
        oracle = native(out / (label + '-native'), cases)
        modes = {}
        for mode in ('plain', 'collect', 'relocate', 'relocate-collect'):
            flags = (['--collect'] if 'collect' in mode else []) + (['--relocate'] if 'relocate' in mode else [])
            result = driver.node([out / 'execute.mjs', artifacts, out / 'runtime',
                                  HERE / cases_name, *flags], out / (label + '-' + mode + '.log'))
            assert result['observations'] == oracle, (label, mode, result['observations'], oracle)
            modes[mode] = result
        results[label] = dict(artifacts=written, native=oracle, runs=modes)
    result = dict(status='PASS', source_identity=pins, results=results,
                  ordered=c.read(out / 'ordered.json'), prefix=c.read(out / 'prefix.json'),
                  metadata_controls=c.read(out / 'keyword-controls.json'),
                  development_skips=c.read(HERE / 'prefix-skips.json'),
                  current_skips=['general boxed EQL needs its runtime function',
                                 'full ordered level-0 build stops at native FFI'],
                  production_executed_files=[2, 2, 0], accepted_files=[0, 0, 0],
                  accepted_originals=[575, 535], ledger=[21, 12], slot_credit=False)
    c.save(out / 'summary.json', result)
    print(json.dumps({label: r['artifacts'] for label, r in results.items()}))
    return result


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
