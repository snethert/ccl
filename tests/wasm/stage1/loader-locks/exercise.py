"""Execute the extended prefix through the existing D2 image installer."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import product
import storage

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / 'loader-level0'
c = product.c


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    return driver


def native(out, cases):
    driver = module('locks_native', PARENT / 'exercise.py')
    support = out.parent / 'native-source'
    support.mkdir(exist_ok=True)
    for name in ('keywords.lisp', 'packages.lisp', 'package-first.lisp', 'package-second.lisp'):
        shutil.copyfile(PARENT / name, support / name)
    with (support / 'packages.lisp').open('a') as stream:
        stream.write((HERE / 'locks.lisp').read_text())
    shutil.copyfile(PARENT / 'native.lisp', support / 'native.lisp')
    driver.HERE = support
    return driver.native(out, cases)


def run(out):
    pins = c.read(out / 'identity.json')['source_identity']
    assert pins == {n: hashlib.sha256(b.encode()).hexdigest() for n, b in product.sources().items()}
    product.prepare_runtime(out / 'runtime')
    for name in ('write.mjs', 'd2.mjs'):
        shutil.copyfile(HERE.parent / 'loader' / name, out / name)
    code = (PARENT / 'execute.mjs').read_text()
    code = code.replace('function callObject(fn,args){', 'function callObject(fn,args,decodeValues=true){')
    code = code.replace('decode(get(ROOT+8200+i*4))', '(decodeValues?decode(get(ROOT+8200+i*4)):get(ROOT+8200+i*4))')
    code = code.replace('function ensure(n){const r=owner.atSafepoint(o=>o.ensure(n));if(r.collected)collections++;}',
        'function ensure(n){const old=t(56),limit=t(52);const r=owner.atSafepoint(o=>o.ensure(n));'
        'if(r.collected){new Uint8Array(memory.buffer,old,limit-old).fill(0xdd);collections++;}}')
    code = code.replace('console.log(JSON.stringify({status:', '''import {controls} from './controls.mjs';
const refusals=controls({get,put,N,T,EXTERNAL,TCR,t,symbolAddress,callObject});
console.log(JSON.stringify({refusals,status:''')
    shutil.copyfile(HERE / 'controls.mjs', out / 'controls.mjs')
    (out / 'execute.mjs').write_text(code)
    c.save(out / 'policy.json', c.read(c.STORE / '2026-09-20-stage1-materialization-r1/execution/policy.json'))
    c.save(out / 'versions.json', dict(abi=dict(name='B', version=1),
        layout=dict(version=1, sha256=c.sha(c.ROOT / 'doc/WASM/contracts/wasm32-layout.v1.json'))))
    driver = module('locks_loader', HERE.parent / 'loader/run.py')
    driver.runtime(out / 'runtime')
    cases = c.read(PARENT / 'prefix-cases.json')
    for name, args in [('packages', []), ('basic', []), ('promote', []), ('allocate', [5]),
                       ('cleanup', [12000]), ('hold', []), ('release', [])]:
        cases.append(dict(id='rwlock-' + name, call=['CCL', 'LOADER-RWLOCK-' + name.upper()], args=args))
    c.save(out / 'cases.json', cases)
    artifacts = out / 'prefix/artifacts'
    written = driver.node([out / 'write.mjs', out / 'prefix', artifacts,
                           out / 'policy.json', out / 'versions.json'], out / 'write.log')
    oracle = native(out / 'native', cases)
    modes = {}
    for mode in ('plain', 'collect', 'relocate', 'relocate-collect'):
        flags = (['--collect'] if 'collect' in mode else []) + (['--relocate'] if 'relocate' in mode else [])
        result = driver.node([out / 'execute.mjs', artifacts, out / 'runtime', out / 'cases.json', *flags],
                             out / (mode + '.log'))
        assert result['observations'] == oracle, (mode, result['observations'], oracle)
        modes[mode] = result
    result = dict(status='PASS', source_identity=pins, artifacts=written, native=oracle, runs=modes,
                  ordered=c.read(out / 'ordered.json'), accepted_files=[0, 0, 0], slot_credit=False)
    c.save(out / 'summary.json', result)
    print({name: (r['modules'], r['initializersExecuted'], len(r['observations']), r['collections'])
           for name, r in modes.items()})
    return result


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
