"""Compare calling semantics and require every moving-collection witness."""
import json
from pathlib import Path
import sys


def rows(text):
    return [line for line in text.splitlines() if line.startswith('CC-ROW ')]


def check(native, target):
    reference = Path(native).read_text()
    report = json.loads(Path(target).read_text())
    text = ''.join(r['text'] for r in report['outputEvents'] if r['channel'] == 1)
    assert reference.count('CC-PASS') == text.count('CC-PASS') == 1
    assert report['ready'] and report['targetLoadedFiles'] == 82
    assert not report['openFiles'] and not report['abandonedSessions']
    assert rows(reference) == rows(text), 'native/target calling observations differ'
    assert len(rows(text)) == 69, len(rows(text))
    forced = report['benchmark']['forced']
    assert len(forced) == 9, len(forced)
    assert all(r['after'] == r['before'] + 1 and r['oldBase'] != r['newBase'] for r in forced)
    return dict(status='PASS', nativeMatchedRows=len(rows(text)), forcedMovingCollections=len(forced))


if __name__ == '__main__':
    print(json.dumps(check(*sys.argv[1:3]), indent=2))
