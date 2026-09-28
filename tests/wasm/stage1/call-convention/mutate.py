"""Single-fault emitted-code controls, materialized through the normal loader."""
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'loader-target'))
from record_reader import read_records
import shutil
import subprocess
from boundaries import expressions, wat

HERE = Path(__file__).resolve().parent


def nodes(tree):
    if isinstance(tree, list):
        yield tree
        for child in tree:
            yield from nodes(child)


def mutate(build, out, kind):
    out.mkdir(parents=True)
    for name in ['bundles.json', 'versions.json', 'policy.json', 'd2.mjs', 'benchmark.w32fsl']:
        shutil.copyfile(build/name, out/name)
    (out/'runtime').symlink_to((build/'runtime').resolve(), target_is_directory=True)
    names = {r['wire']: r['name'] for r in json.loads((build/'function-names.json').read_text())}
    records = read_records(build/'benchmark.records.json')
    changes = 0
    for unit in records['units']:
        if kind != 'public-entry' and names[unit['name']] != {'argument-roots': 'CC-MOVING-ARGUMENTS', 'pool-root': 'CC-POOL'}[kind]:
            continue
        tree = expressions(unit['record'][4])
        body = next(n for n in tree if isinstance(n, list) and n[:2] == ['func', '$body'])
        if kind == 'public-entry':
            entry = next(n for n in tree if isinstance(n, list) and n[:2] == ['func', ['export', '"entry"']])
            start = next(i for i,n in enumerate(entry) if isinstance(n, list) and n[:1] == ['local.set'])
            entry[start:] = [['unreachable']]; changes += 1
        elif kind == 'argument-roots':
            store = next(n for n in nodes(body) if n[:3] == ['i32.store', 'offset=128', ['global.get', '$tcr']]
                         and n[-1][:1] == ['i32.add'] and n[-1][-1] == ['i32.const', '32'])
            store[:] = ['nop']; changes += 1
        else:
            cache = next(n for n in nodes(body) if n[:3] == ['i32.store', 'offset=44', ['local.get', '$context']])
            value = cache[-1]
            cache[:] = ['block', ['local.set', '$stale_pool', value], ['i32.store', 'offset=44', ['local.get', '$context'], ['local.get', '$stale_pool']]]
            for n in nodes(body):
                if n == ['i32.load', 'offset=44', ['local.get', '$context']]:
                    n[:] = ['local.get', '$stale_pool']; changes += 1
            start = next(i for i,n in enumerate(body) if isinstance(n, list) and n[:1] == ['local.set'])
            body.insert(start, ['local', '$stale_pool', 'i32'])
        unit['record'][4] = wat(tree)
    assert changes > 0
    (out/'benchmark.records.json').write_text(json.dumps(records)+'\n')
    (out/'mutation.json').write_text(json.dumps(dict(kind=kind, changes=changes), indent=2)+'\n')
    with (out/'materialize.log').open('w') as log:
        subprocess.run(['node', str(HERE.parent/'loader-target/bundles.mjs'), str(out), '--v1'], stdout=log, stderr=subprocess.STDOUT, check=True)


if __name__ == '__main__':
    import sys
    mutate(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3])
