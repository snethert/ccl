"""The old case-name trap switch must fail on an ordinarily named caller."""
import json
import os
from pathlib import Path
import subprocess
import sys

def check(out):
    work = out / 'trap-control'
    work.mkdir()
    for source in out.iterdir():
        if source != work:
            (work / source.name).symlink_to(source, target_is_directory=source.is_dir())
    for name in ('check.mjs', 'install.mjs'):
        (work / name).unlink()
        (work / name).write_bytes((out / name).read_bytes())
    path = work / 'check.mjs'
    source = path.read_text()
    fixed = 'put(tcr+200,7); // Native CCL default, independent of the case name.'
    assert source.count(fixed) == 1
    path.write_text(source.replace(fixed,
        "if(activeCase.startsWith('CORE-LIBM-')||activeCase.startsWith('CORE-TRANSCEND-'))put(tcr+200,7);"))
    with (work / 'failure.log').open('w') as log:
        result = subprocess.run(['/usr/local/bin/node', path, work, work / 'result.json'],
            env=dict(os.environ, CCL_LIBRARY_CASE='CORE-LOG-CONDITION'),
            stdout=log, stderr=log, timeout=60)
    failure = (work / 'failure.log').read_text()
    assert result.returncode != 0 and 'AssertionError' in failure and 'CORE-LOG-CONDITION' in failure
    for path in work.iterdir():
        if path.is_symlink():
            path.unlink()
    (out / 'trap-control.json').write_text(json.dumps(dict(status='PASS',
        control='R1 case-name-dependent trap mode', result='REJECTED',
        case='CORE-LOG-CONDITION', default_fp_control=7), indent=2, sort_keys=True)+'\n')

if __name__ == '__main__':
    check(Path(sys.argv[1]).resolve())
