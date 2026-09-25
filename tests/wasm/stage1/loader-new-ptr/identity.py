"""Bind the complete producer, execution and product inputs."""
import product

c = product.c


def drivers():
    result = {}
    for name in ('loader-new-ptr', 'loader-aref', 'loader', 'loader-level0',
                 'loader-locks', 'loader-prefix-acceptance', 'registration',
                 'bootstrap-validation'):
        for path in c.files(product.HERE.parent / name):
            if path.suffix in ('.py', '.lisp', '.mjs', '.json', '.c', '.h'):
                result[str(path.relative_to(c.ROOT))] = c.sha(path)
    for path in (c.ROOT / 'runtime/wasm32').iterdir():
        if path.suffix in ('.c', '.h', '.mjs'):
            result[str(path.relative_to(c.ROOT))] = c.sha(path)
    return result
