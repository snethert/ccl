"""Compare numeric observations and require overflow, GC and code witnesses."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'execution-bench'))
from code_shapes import expressions


def rows(text):
    return [line for line in text.splitlines() if line.startswith('FX-ROW ')]


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
    assert reference.count('FX-PASS') == 1 and text.count('FX-PASS') == 1
    assert report['ready'] and report['targetLoadedFiles'] == 82
    assert not report['openFiles'] and not report['abandonedSessions']
    assert len(rows(reference)) == 125
    assert rows(text) == rows(reference), 'native/target numeric observations differ'
    forced = report['benchmark']['forced']
    assert len(forced) == 6
    assert all(r['after'] == r['before']+1 and r['oldBase'] != r['newBase'] for r in forced)
    code = {name: str(body) for name, body in bodies(build).items()}
    for name, operation in [('FX-ADD', 'add'), ('FX-SUB', 'sub'), ('FX-MUL', 'mul')]:
        assert f'i64.{operation}' in code[name] and 'i64.eq' in code[name]
        assert "'$integer'" in code[name] and '$float_slow' not in code[name]
    assert 'i32.add' in code['FX-FIT'] and '$integer' not in code['FX-FIT']
    assert '$float_slow' not in code['FX-FIT']
    assert 'i32.lt_s' in code['FX-LESS']
    assert '$float_slow' in code['FX-GENERIC']
    return dict(status='PASS', nativeMatchedRows=len(rows(text)), forcedMovingCollections=len(forced),
                checkedConditions=['argument type', 'result range', 'generic operand type', 'recovery'],
                codeShapes='direct declared addition; signed comparison; widened add/sub/mul with bignum fallback; generic float fallback')


if __name__ == '__main__':
    print(json.dumps(check(*map(Path, sys.argv[1:4])), indent=2))
