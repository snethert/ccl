"""Exercise the emitted catalog reader, including its checked memory boundary."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
out = Path(sys.argv[1]).resolve()
source = (out / 'compiled/core_cpl_select.wat').read_text()


def function(name):
    start = source.index('(func $' + name + ' ')
    depth = 0
    for end in range(start, len(source)):
        depth += (source[end] == '(') - (source[end] == ')')
        if not depth:
            return source[start:end + 1]
    raise AssertionError(name)


target = out / 'catalog'
target.mkdir(exist_ok=True)
parts = {name: function(name) for name in ('span', 'object_base', 'handler_cons', 'condition_class')}
assert '(call $condition_mask' not in function('body')
prefix = '''(module
 (import "env" "memory" (memory 1 32769 shared))
 (import "env" "call_error" (tag $call_error (param i32)))
 (import "env" "catalog" (global $symbol_condition_class_cells i32))
'''
variants = {'reader': '\n'.join(parts.values())}
checks = {
    'header': ('(i32.ne (i32.and (i32.load (local.get $p)) (i32.const 255)) (i32.const 250))', '(i32.const 0)'),
    'pointer': ('(i32.ne (i32.and (global.get $symbol_condition_class_cells) (i32.const 7)) (i32.const 6))', '(i32.const 0)'),
    'last': ('(i32.ge_u (local.get $i) (local.get $n))', '(i32.ge_u (i32.add (local.get $i) (i32.const 1)) (local.get $n))'),
    'class': ('(drop (call $object_base (local.get $class) (i32.const 16) (i32.const 882)))', ''),
}
for name, (old, new) in checks.items():
    assert variants['reader'].count(old) == 1, name
    variants[name] = variants['reader'].replace(old, new)
for name, body in variants.items():
    path = target / (name + '.wat')
    path.write_text(prefix + body + '\n(export "lookup" (func $condition_class)))\n')
    subprocess.run(['/usr/local/bin/wat2wasm', '--enable-all', path, '-o', path.with_suffix('.wasm')], check=True)
(target / 'source.json').write_text(json.dumps({
    'module_sha256': hashlib.sha256(source.encode()).hexdigest(),
    'functions': {name: hashlib.sha256(text.encode()).hexdigest() for name, text in parts.items()},
    'body_has_no_mask_call': True}, indent=2) + '\n')
subprocess.run(['/usr/local/bin/node', HERE / 'catalog.mjs', target], check=True)
