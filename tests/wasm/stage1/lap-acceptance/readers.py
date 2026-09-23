"""Compare the full L1-CLOS form list under CCL's 17 existing readers."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--native-output', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
native = args.native_output.resolve()
out = args.output.resolve()
out.mkdir()
source = native / 'work/ccl'
assert json.loads((native / 'native/run.json').read_text())['status'] == 'PASS'
driver = (HERE.parent / 'bootstrap-core-acceptance/readers.lisp').read_text()
old = '(dolist (stem \'("l0-def" "l0-pred" "l0-utils"))'
assert driver.count(old) == 1
driver = driver.replace(old, '(dolist (stem \'("l1-clos"))')
driver = driver.replace('(concatenate \'string "level-0/" stem ".lisp")',
                        '(concatenate \'string "level-1/" stem ".lisp")')
(out / 'readers.lisp').write_text(driver)
env = dict(os.environ, CCL_DEFAULT_DIRECTORY=str(source),
           READER_U1=str(source) + '/', READER_PROPOSAL=str(ROOT) + '/',
           READER_OUTPUT=str(out) + '/')
with (out / 'readers.log').open('w') as log:
    subprocess.run([source / 'dx86cl64', '--no-init', '--batch',
                    '--load', ROOT / 'tests/wasm/native-census/observer.lisp',
                    '--load', out / 'readers.lisp'], cwd=source, env=env,
                   stdout=log, stderr=log, check=True)
report = json.loads((out / 'readers.json').read_text())
assert report['status'] == 'PASS' and len(report['rows']) == 17
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(out / 'inputs.json').write_text(json.dumps(dict(
    before=sha(source / 'level-1/l1-clos.lisp'), after=sha(ROOT / 'level-1/l1-clos.lisp'),
    kernel=sha(source / 'dx86cl64'), image=sha(source / 'dx86cl64.image'),
    reader_driver=sha(out / 'readers.lisp')), indent=2, sort_keys=True) + '\n')
print('PASS: identical whole-file forms for all 17 existing targets')
