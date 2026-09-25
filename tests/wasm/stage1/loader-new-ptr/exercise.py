"""Execute the whole-file loader image with native arithmetic observations."""
from pathlib import Path
import sys
import product
import storage

HERE = product.HERE
PARENT = HERE.parent / 'loader-aref'
c = product.c


def expand_table_capacity(text):
    # Fail closed if the generated harness changes; unrelated literals stay put.
    for before, after, count in (
        ('table_capacity:512', 'table_capacity:1024', 1),
        ("new WebAssembly.Table({element:'anyfunc',initial:512})",
         "new WebAssembly.Table({element:'anyfunc',initial:1024})", 2),
        ('put(REGISTRY,512)', 'put(REGISTRY,1024)', 1),
    ):
        assert text.count(before) == count, (before, text.count(before), count)
        text = text.replace(before, after)
    return text


def cases():
    result = []
    def add(name, args):
        result.append(dict(id=name + '-' + '-'.join(map(str, args)),
                           call=['CCL', 'LOADER-' + name.upper()], args=args))
    for bits in (80, 128, 544):
        for a, b in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            add('bignum-arithmetic', [bits, a, b])
    for sign in (1, -1):
        add('bignum-logical', [sign])
        for count in (0, 1, 16, 31, 32, 33, 65, 130):
            add('bignum-shifts', [count, sign])
        for b in (1, -1):
            add('bignum-divide', [sign, b])
    add('bignum-gcd', [])
    add('bignum-pressure', [500])
    add('markers', [])
    add('cfm-byte-length', [])
    add('literal-call', [5])
    return result


def run(out):
    driver = product.module('ptr_execution', PARENT / 'exercise.py')
    driver.HERE = PARENT
    driver.product = product
    save, command = c.save, c.command

    def write(path, value):
        if path == out / 'cases.json':
            value.extend(cases())
            script = out / 'execute.mjs'
            text = script.read_text()
            assert text.count("from './controls.mjs'") == 1
            # The owner still selects placement; only table capacity grows.
            text = expand_table_capacity(text)
            text = text.replace("from './controls.mjs'", "from './pointer-controls.mjs'")
            script.write_text(text)
            (out / 'pointer-controls.mjs').write_text((HERE / 'controls.mjs').read_text())
        return save(path, value)

    def execute(argv, log, env=None, **kwargs):
        if env and 'LOADER_SOURCE' in env and Path(env['LOADER_SOURCE']).name == 'native-source':
            with (Path(env['LOADER_SOURCE']) / 'packages.lisp').open('a') as stream:
                stream.write((HERE / 'witnesses.lisp').read_text())
        return command(argv, log, env, **kwargs)

    c.save, c.command = write, execute
    try:
        result = driver.run(out)
        for row in result['runs'].values():
            assert len(row['refusals']) == 112
            assert len(row['observations']) == 83
        return result
    finally:
        c.save, c.command = save, command


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
