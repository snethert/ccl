"""Replay P2-0 and its controls with the proposed producer and owner."""
from pathlib import Path
import hashlib
import sys
import product
import exercise
import storage


def run(out):
    product.accepted.sources = product.sources
    product.accepted.prepare_runtime = product.prepare_runtime
    result = exercise.helper('run').run(out / 'execution', stops=False)
    result['proposal_source_identity'] = {
        n: hashlib.sha256(b.encode()).hexdigest() for n, b in product.sources().items()}
    product.c.save(out / 'execution/summary.json', result)
    extra = exercise.helper('extra').run(out / 'extra', out / 'execution')
    product.c.save(out / 'summary.json', dict(status='PASS', image_checks=len(result['controls']),
                                             fasl_controls=2, extra=extra))


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
