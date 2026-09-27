"""Check the dedicated handler/restart run without consuming ordinary READY's budget."""
import json
from pathlib import Path
import sys

report = json.loads(Path(sys.argv[1]).read_text())
assert report['ready'] and report['status'] == 'READY'
stdout = ''.join(row['text'] for row in report['outputEvents'] if row['channel'] == 1)
for marker in ('LOADER-LOAD-FILE-ERROR-PASS', 'LOADER-GENERATION-REFUSAL-PASS',
               'LOADER-ERROR-PATHS-PASS', 'LOADER-INSTANCE-A-PASS'):
    assert marker in stdout, marker
assert stdout.count('LOADER-LOAD-REFUSAL (:FILE-ERROR SIMPLE-FILE-ERROR') == 2
assert not report['abandonedSessions'] and not report['openFiles']
assert len(report['archiveStorage']) == 1
assert report['archiveStorage'][0]['generations'] == 2
assert report['archiveStorage'][0]['openSessions'] == 0
assert sum(row['event'] == 'open' and row['path'] == '/ccl/l1-fasls/l1-sort.w32fsl'
           for row in report['loadEvents']) == 2
for path in report['startupLoads']:
    assert any(row['event'] == 'return' and row['path'] == path and
               row['value'] == {'symbol': 'T'} for row in report['loadEvents']), path
print('PASS: caught LOAD refusals, error/restart paths, later LOAD, no leaked sessions')
