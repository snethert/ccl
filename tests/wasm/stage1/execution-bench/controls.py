"""Reject corrupted benchmark answers and missing/repeated measurements."""
import json
from pathlib import Path
import sys
from run import parse, CASES

path = Path(sys.argv[1])
report = json.loads(path.read_text())
text = ''.join(e['text'] for e in report['outputEvents'] if e['channel'] == 1)
assert len(parse(text)) == 144
lines = text.splitlines()
sample = next(i for i,l in enumerate(lines) if l.startswith('EB-END '))
changes = {}
bad = lines.copy(); fields = bad[sample].split(); fields[-1] = str(int(fields[-1])+1); bad[sample] = ' '.join(fields)
changes['wrong-answer'] = '\n'.join(bad)
changes['missing-sample'] = '\n'.join(lines[:sample]+lines[sample+1:])
changes['duplicate-sample'] = '\n'.join(lines+[lines[sample]])
changes['missing-completion'] = text.replace('EB-PASS 16 9','incomplete')
changes['missing-gc-witness'] = text.replace('EB-GC-PASS 4 44','incomplete')
bad = lines.copy(); fields = bad[sample].split(); fields[4] = '0'; bad[sample] = ' '.join(fields)
changes['zero-duration'] = '\n'.join(bad)
for name, changed in changes.items():
    try:
        parse(changed)
    except (AssertionError, ValueError, KeyError):
        continue
    raise AssertionError('accepted '+name)
print(json.dumps(dict(status='PASS',rejected=list(changes))))
