"""Execute the integrated stack, or audit 181's specific significand mutant."""
from pathlib import Path
import hashlib
import json
import sys
import check

HERE = Path(__file__).resolve().parent
DEFINITIONS = HERE.parent / 'loader-def'
sys.path.insert(0, str(DEFINITIONS))
import product
import identity
import storage
c = check.c
base_drivers = identity.drivers


def drivers():
    result = base_drivers()
    for path in c.files(HERE):
        if path.suffix in ('.py', '.json', '.lisp', '.mjs'):
            result[str(path.relative_to(c.ROOT))] = c.sha(path)
    result[str(check.RECORD.relative_to(c.ROOT))] = c.sha(check.RECORD)
    return result


def module(name):
    return product.module('integrated_definitions_' + name, DEFINITIONS / (name + '.py'))


def runtime(out):
    product.module('integrated_runtime', HERE.parent / 'loader/run.py').runtime(out)
    c.save(out / 'array-runtime.json', dict(source=c.sha(c.ROOT / 'runtime/wasm32/collector.c'),
                                           binary=c.sha(out / 'collector.wasm')))


def capacity_controls():
    helper = product.module('capacity_controls', HERE.parent / 'loader-new-ptr/exercise.py').expand_table_capacity
    code = (HERE.parent / 'loader-level0/execute.mjs').read_text()
    sentinel = '\n// unrelated 512 and 1512 remain unchanged\n'
    assert helper(code + sentinel) == code.replace('512', '1024') + sentinel
    rejected = []
    for name, body in (
        ('missing-manifest', code.replace('table_capacity:512', 'table_capacity:256')),
        ('missing-table', code.replace("initial:512", "initial:256", 1)),
        ('duplicate-registry', code + '\nput(REGISTRY,512);'),
    ):
        try:
            helper(body)
        except AssertionError:
            rejected.append(name)
        else:
            raise AssertionError(name)
    return dict(status='PASS', unrelated_literals_preserved=True, rejected=rejected)


def run(out, mutant=False):
    out.mkdir(parents=True, exist_ok=True)
    initial = check.check()
    inputs = drivers()
    c.save(out / 'inputs.json', inputs)
    c.save(out / 'capacity-controls.json', capacity_controls())
    product.sources = check.sources
    product.prepare_runtime = check.prepare_runtime
    product.runtime = runtime
    identity.drivers = drivers
    if mutant:
        def mutated_sources():
            bodies = check.sources()
            name = 'level-0/WASM32/w32-lap.lisp'
            before, after = '(- 20 (integer-length high))', '(- 21 (integer-length high))'
            assert bodies[name].count(before) == 1
            bodies[name] = bodies[name].replace(before, after)
            return bodies
        product.sources = mutated_sources
    execution = out / 'execution'
    module('run').run(execution)
    expected = dict(id='float-subnormal-10', values=[True, -1029, None, 45, None])
    packet = c.STORE / c.read(check.RECORD)['packets']['definitions']['path']
    previous = check.read(packet, 'execution/summary.json')
    if mutant:
        try:
            module('exercise').run(execution)
        except AssertionError as error:
            # Preserve the exact failed comparison, then inspect all four runs.
            c.save(out / 'original-failure.json', dict(type=type(error).__name__, detail=str(error)))
        else:
            raise AssertionError('significand mutant survived')
        oracle = c.read(execution / 'native/native.json')
        assert oracle == previous['native'] + [expected]
        loader = product.module('mutant_execution', HERE.parent / 'loader/run.py')
        modes = {}
        for mode in ('plain', 'collect', 'relocate', 'relocate-collect'):
            log = execution / (mode + '.log')
            if mode == 'plain':
                result = json.loads(log.read_text().strip().splitlines()[-1])
            else:
                flags = (['--collect'] if 'collect' in mode else []) + (['--relocate'] if 'relocate' in mode else [])
                result = loader.node([execution / 'execute.mjs', execution / 'prefix/artifacts',
                    execution / 'runtime', execution / 'cases.json', *flags], log)
            assert result['status'] == 'PASS' and result['modules'] == 595
            assert result['observations'][:-1] == previous['native']
            assert result['observations'][-1]['id'] == expected['id']
            assert result['observations'][-1]['values'] == [True, -1030, None, 44, None]
            assert result['refusals'] == previous['runs'][mode]['refusals']
            modes[mode] = dict(old_rows_equal=110, expected=expected, actual=result['observations'][-1], killed=True)
        report = dict(status='PASS', mutant='M1_NONZERO_HIGH_20_TO_21', source_identity={
            n:hashlib.sha256(b.encode()).hexdigest() for n,b in product.sources().items()},
            modes=modes, product_qualification=False)
        c.save(out / 'mutant.json', report)
    else:
        result = module('exercise').run(execution)
        assert result['source_identity'] == initial['source_identity']
        assert result['native'] == previous['native'] + [expected]
        assert result['runtime'] == previous['runtime']
        for mode, row in result['runs'].items():
            assert row['modules'] == 595 and row['initializersExecuted'] == 33
            assert row['refusals'] == previous['runs'][mode]['refusals']
            assert row['collections'] == (151 if 'collect' in mode else 9)
        reproduced = {}
        production = {}
        for name, row in c.read(packet / 'regenerable.json').items():
            path = out / name
            if path.is_file() and c.sha(path) == row['sha256']:
                reproduced[name] = row['sha256']
            if name.startswith('execution/') and name.endswith('.w32fsl') and (
                name.count('/') == 1 and Path(name).stem.startswith('l0-') or
                name in ('execution/inputs/w32-lap.w32fsl', 'execution/inputs/w32-prims.w32fsl')):
                assert path.is_file() and c.sha(path) == row['sha256'], name
                production[name] = row['sha256']
        assert len(production) == 11, production
        report = dict(**initial, drivers=inputs, reviewed_artifacts=reproduced,
            production_fasls=production, product_files=8, runs=4, modules=595,
            initializers=33, native_equal_rows=111, controls_per_run=116,
            capacity_controls=c.read(out / 'capacity-controls.json'))
        report['new_execution'] = True
        c.save(out / 'integration.json', report)
    assert drivers() == inputs, 'drivers changed during execution'
    assert check.check() == initial, 'integrated product changed during execution'
    c.save(out / 'finished.json', dict(status='PASS', drivers=inputs,
        integration_record=initial['integration_record'], mutant=mutant))
    print(json.dumps(dict(status='PASS', mutant=mutant, runs=4, observations=111)))
    return report


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve(), '--mutant' in sys.argv[2:])
