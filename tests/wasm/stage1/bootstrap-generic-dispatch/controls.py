"""Focused omissions in the new metadata and population admission paths."""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
out = Path(sys.argv[1]).resolve()
work = out / 'generic-controls'
work.mkdir(exist_ok=True)
rows = []

def run(name, command, reason, env=None):
    result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=60)
    log = result.stdout + result.stderr
    (work / (name + '.log')).write_text(log)
    assert result.returncode and reason in log, (name, result.returncode, log[-2000:])
    assert 'RuntimeError:' not in log, (name, 'trap is not a refusal-test rejection')
    rows.append(dict(name=name, status='REJECTED', observation=reason))

def expression(text, start):
    depth = 0
    for end in range(start, len(text)):
        depth += (text[end] == '(') - (text[end] == ')')
        if depth == 0:
            return text[start:end+1]
    raise AssertionError('unbalanced generated expression')

for name, module, needle, reason in [
    ('function-prefix-magic', 'core_generic_function_bits',
     '(if (i32.ne (i32.load (i32.add', 'prefix magic'),
    ('function-bits-value', 'core_generic_set_function_bits',
     '(if (i32.or (i32.and (i32.load offset=12', 'bits writer type')]:
    wat = out / 'compiled' / (module + '.wat')
    binary = wat.with_suffix('.wasm')
    original = binary.read_bytes()
    text = wat.read_text()
    start = text.index(needle, text.index('(func $body')) + 4
    predicate = expression(text, start)
    if name == 'function-prefix-magic': assert '22873420' in predicate
    changed = text[:start] + '(i32.const 0)' + text[start+len(predicate):]
    fault = work / (name + '.wat')
    fault.write_text(changed)
    try:
        subprocess.run(['/usr/local/bin/wat2wasm', '--enable-tail-call', '--enable-exceptions',
                        '--enable-threads', fault, '-o', binary], check=True)
        run(name, ['/usr/local/bin/node', out/'check.mjs', out, work/(name+'.json')], reason,
            {**os.environ, 'CCL_DISPATCH_METADATA': '1'})
    finally:
        binary.write_bytes(original)

source = (out/'runtime/collector.c').read_text()
flags = ['--target=wasm32', '-O2', '-nostdlib', '-fno-builtin', '-matomics', '-mbulk-memory',
         '-Wl,--no-entry', '-Wl,--import-memory', '-Wl,--shared-memory',
         '-Wl,--max-memory=2147549184', '-Wl,-z,stack-size=65536',
         '-Wl,--global-base=1048576', '-Wl,--export=collect', '-Wl,--export=__stack_pointer']
for name, before, after in [
    ('population-width', 'if(n!=3||(W)p+16>s->used', 'if((W)p+16>s->used'),
    ('population-link', '||LOAD(p+4)!=0||(LOAD(p+8)!=0&&LOAD(p+8)!=4)',
                        '||(LOAD(p+8)!=0&&LOAD(p+8)!=4)'),
    ('population-kind', '||(LOAD(p+8)!=0&&LOAD(p+8)!=4)', '')]:
    assert source.count(before) == 1
    fault = work/(name+'.c');fault.write_text(source.replace(before,after))
    binary = work/(name+'.wasm')
    subprocess.run(['/usr/local/opt/llvm/bin/clang', *flags, fault, '-o', binary], check=True)
    run(name, ['/usr/local/bin/node', out/'population-check.mjs', binary, work/(name+'.json')],
        'Missing expected exception')

owner = out/'runtime/collector-owner.mjs'
original = owner.read_bytes();text=original.decode()
for name, before in [('pinned-population-width', 'n===3&&'),
                     ('pinned-population-link', 'this.#get(p+4)===0&&'),
                     ('pinned-population-kind', '&&(this.#get(p+8)===0||this.#get(p+8)===4)')]:
    # Limit the edit to the newly added population arm.
    start=text.index('if(tag===90)');end=text.index('\n',start)
    arm=text[start:end];assert arm.count(before)==1
    try:
        owner.write_text(text[:start]+arm.replace(before,'')+text[end:])
        run(name, ['/usr/local/bin/node', out/'population-check.mjs', out/'collector.wasm',
                   work/(name+'.json')], 'Missing expected exception')
    finally:owner.write_bytes(original)
(out/'generic-controls.json').write_text(json.dumps(dict(status='PASS',rejected=len(rows),rows=rows),
                                                   indent=2,sort_keys=True)+'\n')
