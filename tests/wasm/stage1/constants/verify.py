#!/usr/bin/env python3
"""Run the byte oracle and five semantic faults in disposable directories."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
source = (HERE / 'encode.py').read_text()
tests = (HERE / 'test_encode.py').read_text()
mutants = [
    ('host-integer-range', "n <= self.c['target-most-positive-fixnum']:\n", "n <= 2**60-1:\n", 'test_bignum_signed_limbs'),
    ('float-bit-order', "int(value, 16).to_bytes(width // 8, 'little')", "int(value, 16).to_bytes(width // 8, 'big')", 'test_float_payloads'),
    ('tagged-string', "c.to_bytes(4, 'little') for c in value", "((c << 8) | 75).to_bytes(4, 'little') for c in value", 'test_strings_and_vectors'),
    ('tagged-fixnum-vector', "n.to_bytes(4, 'little', signed=True)", "self.fixnum(n).to_bytes(4, 'little')", 'test_strings_and_vectors'),
    ('missing-vector-pad', 'offset = 8 if width * parts >= 64 else 4', 'offset = 4', 'test_strings_and_vectors'),
]
observations = []
with tempfile.TemporaryDirectory(prefix='ccl-ll10-encode-') as directory:
    p = Path(directory)
    # Explicit schema locator makes the same code runnable outside the checkout.
    executable = source.replace("SCHEMA = ROOT / 'doc/WASM/contracts/wasm32-layout.v1.json'",
                                'SCHEMA = Path(' + repr(str(ROOT / 'doc/WASM/contracts/wasm32-layout.v1.json')) + ')')
    # The temporary path is shallower than a checkout path; ROOT is unused after injection.
    executable = executable.replace('ROOT = Path(__file__).resolve().parents[4]', 'ROOT = Path.cwd()')
    (p / 'test_encode.py').write_text(tests)
    for name, old, new, test in [('positive', '', '', '')] + mutants:
        body = executable
        if old:
            assert body.count(old) == 1, (name, 'mutation site not unique')
            body = body.replace(old, new)
        (p / 'encode.py').write_text(body)
        r = subprocess.run([sys.executable, '-B', str(p / 'test_encode.py')], capture_output=True, text=True)
        log = r.stdout + r.stderr
        if name == 'positive':
            assert r.returncode == 0, log
        else:
            assert r.returncode == 1 and ('FAIL: ' + test in log or 'ERROR: ' + test in log), (name, log)
        observations.append({'case': name, 'result': 'PASS' if name == 'positive' else 'REJECTED'})
paths = [HERE / 'encode.py', HERE / 'test_encode.py', HERE / 'verify.py',
         ROOT / 'doc/WASM/contracts/wasm32-layout.v1.json',
         ROOT / 'compiler/X86/X8632/x8632-arch.lisp',
         ROOT / 'compiler/X86/X8632/x8632-vinsns.lisp', ROOT / 'compiler/X86/x862.lisp',
         ROOT / 'xdump/xfasload.lisp', ROOT / 'lib/chars.lisp']
print(json.dumps({'status': 'PASS', 'scope': 'Pointer-free encoder unit only; no generated-code or LL10 qualification.',
                  'cases': observations,
                  'source_pins': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}, indent=2))
