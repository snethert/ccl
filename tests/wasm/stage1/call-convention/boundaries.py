"""Extract actual product entries/helpers for deterministic admission controls."""
import json
from pathlib import Path
import subprocess
import sys

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'loader-target'))
from record_reader import read_records

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'execution-bench'))
from code_shapes import expressions


def wat(node):
    return '(' + ' '.join(wat(x) for x in node) + ')' if isinstance(node, list) else node


def build(source, out, mutant=None):
    out.mkdir(parents=True, exist_ok=True)
    names = {r['wire']: r['name'] for r in json.loads((source/'function-names.json').read_text())}
    metadata = {}
    for unit in read_records(source/'benchmark.records.json')['units']:
        name = names[unit['name']]
        if name not in ['CC-ZERO', 'CC-V0', 'CC-V1', 'CC-V4', 'CC-V5', 'CC-V64', 'CC-TAIL', 'CC-DEPTH']:
            continue
        tree = expressions(unit['record'][4])
        def nodes(node):
            if isinstance(node, list):
                yield node
                for child in node:
                    yield from nodes(child)
        pool_checks = [n for n in nodes(tree) if n[:2] == ['call', '$object_base']
                       and n[2][:2] == ['i32.load', 'offset=24']]
        metadata[name] = dict(required=unit['record'][2][1], optional=unit['record'][2][2],
                              poolHeader=int(pool_checks[0][-1][1]) if pool_checks else 1786)
        implicit = next(n for n in tree if isinstance(n, list) and n[:2] == ['func', '$implicit_error'])
        # Observe the real stack guard's Lisp-signal boundary without a boot image.
        implicit[:] = expressions('(func $implicit_error (param $kind i32) (param $top i32) (i32.store (i32.const 256) (i32.load offset=180 (global.get $tcr))) (throw $call_error (local.get $kind)))')
        tree += [['export', '"resolve_test"', ['func', '$resolve']], ['export', '"guard_test"', ['func', '$stack_guard']]]
        text = wat(tree)
        if mutant == 'always-guard':
            def restore(node):
                if not isinstance(node, list):
                    return
                if node[:1] == ['if'] and len(node) == 3 and node[-1][:1] == ['then'] and node[-1][1][:2] == ['call', '$stack_guard']:
                    node[:] = node[-1][1]
                else:
                    for child in node:
                        restore(child)
            restore(tree)
            text = wat(tree)
        if mutant == 'zero-slot':
            old = '(if (i32.eqz (local.get $slot)) (then (throw $call_error (i32.const 4))))'
            assert text.count(old) == 1
            text = text.replace(old, '')
        if mutant == 'version':
            old = '(if (i32.ne (local.get $version) (i32.load offset=4 (local.get $row))) (then (throw $call_error (i32.const 4))))'
            assert text.count(old) == 1
            text = text.replace(old, '')
        if mutant == 'stack-signal':
            old = '(i32.or (local.get $flags) (i32.const 1))'
            assert text.count(old) == 1
            text = text.replace(old, '(local.get $flags)')
        if mutant == 'public-metadata':
            entry = next(n for n in tree if isinstance(n, list) and n[:2] == ['func', ['export', '"entry"']])
            clause = next(n for n in nodes(entry) if n[:1] == ['if'] and n[1][:1] == ['i32.or']
                          and n[1][1][:1] == ['i32.ne'] and n[1][1][1][:2] == ['i32.load', 'offset=16'])
            clause[:] = ['nop']
            text = wat(tree)
        path = out/(name+'.wat'); path.write_text(text)
        subprocess.run(['wat2wasm', '--enable-all', str(path), '-o', str(path.with_suffix('.wasm'))], check=True)
    (out/'metadata.json').write_text(json.dumps(metadata)+'\n')
    return out


if __name__ == '__main__':
    source, out = map(Path, sys.argv[1:3])
    build(source, out)
    subprocess.run(['node', str(HERE/'boundaries.mjs'), str(out)], check=True)
    build(source, out/'always-guard', 'always-guard')
    subprocess.run(['node', str(HERE/'boundaries.mjs'), str(out/'always-guard')], check=True)
    before = json.loads((out/'always-guard/boundaries.json').read_text())
    after = json.loads((out/'boundaries.json').read_text())
    assert before == after, 'inline guard must preserve the exact overflow depth'
    for kind in ('zero-slot', 'version', 'stack-signal', 'public-metadata'):
        build(source, out/kind, kind)
        result = subprocess.run(['node', str(HERE/'boundaries.mjs'), str(out/kind)], capture_output=True, text=True)
        (out/(kind+'.log')).write_text(result.stdout+result.stderr)
        assert result.returncode and 'AssertionError' in result.stderr, kind
        print(kind, 'KILLED')
