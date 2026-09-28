"""Compare raw-bit observations and require collection, safety and code witnesses."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'execution-bench'))
from code_shapes import expressions


def rows(text):
    return [line for line in text.splitlines() if line.startswith('FU-ROW ')]


def bodies(build):
    names = {r['wire']: r['name'] for r in json.loads((build/'function-names.json').read_text())}
    result = {}
    for unit in json.loads((build/'benchmark.records.json').read_text())['units']:
        tree = expressions(unit['record'][4])
        result[names[unit['name']]] = next(n for n in tree if isinstance(n, list) and n[:2] == ['func', '$body'])
    return result


def check(native, target, build):
    reference = native.read_text()
    report = json.loads(target.read_text())
    text = ''.join(r['text'] for r in report['outputEvents'] if r['channel'] == 1)
    assert reference.count('FU-PASS') == 1 and text.count('FU-PASS') == 1
    assert report['ready'] and report['targetLoadedFiles'] == 82
    assert not report['openFiles'] and not report['abandonedSessions']
    assert len(rows(reference)) == 83
    assert rows(text) == rows(reference), 'native/target raw-bit observations differ'
    forced = report['benchmark']['forced']
    assert len(forced) == 4
    assert all(r['after'] == r['before']+1 and r['oldBase'] != r['newBase'] for r in forced)
    code = bodies(build)
    for prefix, width in [('D', 64), ('S', 32)]:
        for name, op in [('ADD', 'add'), ('SUB', 'sub'), ('MUL', 'mul'), ('DIV', 'div')]:
            body = str(code[f'FU-{prefix}{name}'])
            assert f'f{width}.{op}' in body
            assert '$float_slow' not in body
    for name in ['FU-SAFE', 'FU-SAFE-LOCAL']:
        assert '$float_slow' in str(code[name]) and 'f64.div' not in str(code[name])
    assert 'f64.div' in str(code['FU-UNSAFE-LOCAL'])
    return dict(status='PASS', nativeMatchedRows=len(rows(text)), forcedMovingCollections=len(forced),
                checkedConditions=['invalid', 'division-by-zero', 'overflow', 'type-error'],
                codeShapes='eight direct arithmetic bodies, two checked scopes, one unchecked inner scope')


if __name__ == '__main__':
    result = check(*map(Path, sys.argv[1:4]))
    print(json.dumps(result, indent=2))
