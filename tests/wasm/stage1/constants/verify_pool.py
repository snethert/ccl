#!/usr/bin/env python3
"""Independent literal-word checks and semantic mutants for the pool linker."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = (HERE / 'pool.py').read_text()
mutants = [
    ('cons-order', "(cons_offsets['cdr'], spec['cdr']), (cons_offsets['car'], spec['car'])",
     "(cons_offsets['car'], spec['cdr']), (cons_offsets['cdr'], spec['car'])", 'test_identity_cycles_and_layout'),
    ('pointer-tag', '(base + target + tag).to_bytes', '(base + target).to_bytes', 'test_identity_cycles_and_layout'),
    ('root-base', 'base + value + tag if relative else value', 'value + tag if relative else value', 'test_identity_cycles_and_layout'),
    ('identity-collapse', 'offset, tag = indices[ident]', 'offset, tag = next(iter(indices.values()))', 'test_identity_cycles_and_layout'),
    ('drop-last-object', 'Materialized(base, bytes(image), roots,', 'Materialized(base, bytes(image[:-8]), roots,', 'test_mutual_forward_and_cold_pools'),
    ('extent-overflow', 'base < limit and end <= limit', 'base < limit', 'test_extent_refusals_preserve_plan'),
]
observations = []
with tempfile.TemporaryDirectory(prefix='ccl-ll10-pool-') as tmp:
    path = Path(tmp)
    (path / 'test_pool.py').write_bytes((HERE / 'test_pool.py').read_bytes())
    for case, old, new, test in [('positive', '', '', '')] + mutants:
        body = source
        if old:
            assert body.count(old) == 1, (case, 'mutation site not unique')
            body = body.replace(old, new)
        (path / 'pool.py').write_text(body)
        run = subprocess.run([sys.executable, '-B', str(path / 'test_pool.py')],
                             env={**os.environ, 'PYTHONPATH': str(HERE)}, capture_output=True, text=True)
        log = run.stdout + run.stderr
        if case == 'positive':
            assert run.returncode == 0, log
        else:
            assert run.returncode == 1 and 'FAIL: ' + test in log, (case, log)
        observations.append({'case': case, 'result': 'PASS' if case == 'positive' else 'REJECTED'})
paths = [HERE / f for f in ('encode.py', 'pool.py', 'test_pool.py', 'verify_pool.py')]
paths.append(HERE.parents[3] / 'doc/WASM/contracts/wasm32-layout.v1.json')
print(json.dumps({'status': 'PASS', 'scope': 'Isolated graph linker; no compiler/Worker or LL10 qualification.',
                  'cases': observations,
                  'source_pins': {str(p.relative_to(HERE.parents[3])): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}, indent=2))
