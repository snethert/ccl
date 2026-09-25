"""Prepare a fresh output directory for the complete compiler/runtime run."""
from pathlib import Path
import sys
import qualify
import storage

if __name__ == '__main__':
    sys.setrecursionlimit(20000)
    out = Path(sys.argv[1]).resolve()
    with storage.lease([out]):
        out.mkdir(parents=True, exist_ok=True)
        qualify.run('corpus', out)
