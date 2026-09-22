"""Exhaust the changed reader expression and compare entire native form lists."""
from pathlib import Path
import os
import json
import hashlib
import shutil
import tarfile
import subprocess
import sys
import backend

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
out = Path(sys.argv[1]).resolve()
out.mkdir(exist_ok=True)
source = 'level-0/l0-bignum32.lisp'
old = (ROOT / source).read_text()
new = backend.source_files(ROOT)[source]
restored = new.replace('#+(or x8632-target arm-target wasm32-target)', '#+(or x8632-target arm-target)')
restored = restored.replace('#-wasm32-target\n                 (let* ((ubytes', '(let* ((ubytes')
restored = restored.replace('\n                 #+wasm32-target (error "GMP is unavailable on this target.")', '')
assert restored == old
(out / 'l0-bignum32.lisp').write_text(new)
env = dict(os.environ, MULTIPLY_OLD=str(ROOT / source), MULTIPLY_NEW=str(out / 'l0-bignum32.lisp'),
           MULTIPLY_READERS=str(out / 'readers.json'))
kernel = ROOT.parent / 'ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64'
shutil.copyfile(kernel, out / 'dx86cl64')
(out / 'dx86cl64').chmod(0o755)
image = out / 'dx86cl64.image'
inputs = ROOT.parent / 'ccl-evidence/macos-u1-inputs'
archive_path = inputs / 'bootstrap.tar.gz'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive_path) == json.loads((inputs / 'pins.json').read_text())['inputs']['bootstrap.tar.gz']
with tarfile.open(archive_path) as archive:
    image.write_bytes(archive.extractfile('dx86cl64.image').read())
(out / 'inputs.json').write_text(json.dumps(dict(kernel=sha(kernel), bootstrap=sha(archive_path), image=sha(image), original_source=sha(ROOT / source), proposed_source=sha(out / 'l0-bignum32.lisp')), sort_keys=True, indent=2)+'\n')
with (out / 'readers.log').open('w') as log:
    subprocess.run([out / 'dx86cl64', '-I', image, '-n', '-b', '-l', HERE / 'readers.lisp'], env=env,
                   stdout=log, stderr=subprocess.STDOUT, check=True)
