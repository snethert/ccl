"""Inherited loader witnesses and cases, independent of a packet driver."""
from pathlib import Path

HERE = Path(__file__).resolve().parent


def witnesses():
    return [HERE.parent / folder / name for folder, name in (
        ('loader-level0', 'packages.lisp'), ('loader-locks', 'locks.lisp'),
        ('loader-aref', 'arrays.lisp'), ('loader-new-ptr', 'witnesses.lisp'),
        ('loader-def', 'witnesses.lisp'))] + sorted((HERE.parent / 'loader-hash/witnesses').glob('*.lisp'))


def cases(product):
    result = product.c.read(HERE.parent / 'loader-level0/prefix-cases.json')
    for name, args in [('packages', []), ('basic', []), ('promote', []), ('allocate', [5]),
                       ('cleanup', [12000]), ('hold', []), ('release', [])]:
        result.append(dict(id='rwlock-' + name, call=['CCL', 'LOADER-RWLOCK-' + name.upper()], args=args))
    for name in ('matrix', 'cube', 'chain', 'vector-chain', 'ranks', 'bits', 'string', 'integers', 'evaluation', 'collection', 'hold', 'release'):
        result.append(dict(id='array-' + name, call=['CCL', 'LOADER-ARRAY-' + name.upper()], args=[]))
    result += product.module('definitions_cases', HERE.parent / 'loader-def/exercise.py').cases()
    return result + product.c.read(HERE.parent / 'loader-hash/cases.json')
