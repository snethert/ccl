"""Omit only l0-aprims' package-lock initializer in an otherwise real boot."""
from pathlib import Path
import subprocess
import sys
import product
import storage

c = product.c


def run(out):
    assert c.read(out / 'summary.json')['status'] == 'PASS'
    artifacts = out / 'prefix/artifacts'
    manifest = c.read(artifacts / 'manifest.json')
    symbols = {c.digest(s['reference']): s['name'] for s in manifest['symbols']}
    selected = []
    for row in c.read(artifacts / 'code-set.json')['modules']:
        names = {symbols.get(c.digest(s['reference'])) for s in row['symbols']}
        if {'%ALL-PACKAGES%', 'MAKE-READ-WRITE-LOCK'} <= names:
            selected.append(row['code_id'])
    assert len(selected) == 1, selected
    original = (out / 'execute.mjs').read_text()
    anchor = "  try{coldResults.push(callObject(get(list+3),[]));}"
    assert original.count(anchor) == 1
    mutated = original.replace(anchor,
        '  if((get(get(list+3)-2)>>>2)===' + str(selected[0]) + ')continue;\n' + anchor)
    script = out / 'omit-package-locks.mjs'
    script.write_text(mutated)
    try:
        c.command([c.NODE, script, artifacts, out / 'runtime', out / 'cases.json'],
                  out / 'omit-package-locks.log', timeout=60)
    except subprocess.CalledProcessError:
        log = (out / 'omit-package-locks.log').read_text()
        assert 'Error: rwlock-packages: checked ' in log, log[-1800:]
    else:
        raise AssertionError('package-lock initializer omission survived')
    record = dict(status='KILLED', omitted_code_id=selected[0],
        scope='only the package-lock initializer is omitted; all other cold-load functions execute',
        original_driver=c.sha(out / 'execute.mjs'), mutant_driver=c.sha(script),
        failing_observation='rwlock-packages', native_claim=False)
    c.save(out / 'initializer-control.json', record)
    print(record)


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
