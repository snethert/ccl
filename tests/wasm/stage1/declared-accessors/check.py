"""Compare accessor semantics, moving roots, policy, and emitted loads."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'execution-bench'))
from code_shapes import expressions


def bodies(build):
    names = {r['wire']: r['name'] for r in json.loads((build/'function-names.json').read_text())}
    result = {}
    for unit in json.loads((build/'benchmark.records.json').read_text())['units']:
        tree = expressions(unit['record'][4])
        result[names[unit['name']]] = next(n for n in tree if isinstance(n, list) and n[:2] == ['func', '$body'])
    return result


def rows(text):
    return [line for line in text.splitlines() if line.startswith('DA-ROW ')]


def nodes(tree):
    if isinstance(tree, list):
        yield tree
        for child in tree:
            yield from nodes(child)


def check(native, target, build):
    reference = native.read_text()
    report = json.loads(target.read_text())
    text = ''.join(r['text'] for r in report['outputEvents'] if r['channel'] == 1)
    assert reference.count('DA-PASS') == text.count('DA-PASS') == 1
    assert report['ready'] and report['targetLoadedFiles'] == 82
    assert not report['openFiles'] and not report['abandonedSessions']
    assert rows(text) == rows(reference), 'native/target accessor observations differ'
    assert len(rows(text)) == 71
    forced = report['benchmark']['forced']
    assert len(forced) == 8
    assert all(r['after'] == r['before']+1 and r['oldBase'] != r['newBase'] for r in forced)
    code = bodies(build)
    for name in ['DA-CAR', 'DA-CDR', 'DA-LIST-CAR', 'DA-LIST-CDR', 'DA-BOUNDED', 'DA-INNER-TRUST']:
        assert "'$span'" not in str(code[name]), name
    for name in ['DA-SAFE-CAR', 'DA-SAFE-VECTOR', 'DA-SLOW-POLICY', 'DA-INNER-SAFE', 'DA-CHECKED-THE']:
        assert "'$span'" in str(code[name]), name
    for name in ['DA-VECTOR', 'DA-FIXED']:
        assert any(n[:3] == ['call', '$implicit_error', ['i32.const', '17']]
                   for n in nodes(code[name])), name
    assert not any(n[:3] == ['call', '$implicit_error', ['i32.const', '17']]
                   for n in nodes(code['DA-BOUNDED']))
    return dict(status='PASS', nativeMatchedRows=len(rows(text)), forcedMovingCollections=len(forced),
                codeShapes='direct cons/list loads; bounded SVREF; retained dynamic bounds and checked lexical policies')


if __name__ == '__main__':
    print(json.dumps(check(*map(Path, sys.argv[1:4])), indent=2))
