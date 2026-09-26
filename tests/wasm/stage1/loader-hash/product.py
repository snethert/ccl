"""Apply a strict proposal delta to the pinned, integrated parent sources."""
from pathlib import Path
import hashlib
import importlib.util
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'bootstrap-validation'))
sys.path.append(str(HERE.parent / 'loader'))
import common as c


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def all_sources():
    pins = c.read(HERE / 'files/parent.json')['sources']
    c.verify_files(c.ROOT, pins)
    result = {name: (c.ROOT / name).read_text() for name in pins}
    lines = (HERE / 'files/proposal.patch').read_text().splitlines(keepends=True)
    i = 0
    while i < len(lines):
        assert lines[i].startswith('--- a/')
        name = lines[i][6:].strip()
        assert lines[i + 1] == '+++ b/' + name + '\n' and name in result
        old, output, cursor = result[name].splitlines(keepends=True), [], 0
        i += 2
        while i < len(lines) and lines[i].startswith('@@ '):
            match = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n', lines[i])
            assert match, lines[i]
            start, removed, added = int(match[1]) - 1, int(match[2] or 1), int(match[4] or 1)
            assert start >= cursor
            output.extend(old[cursor:start]); cursor = start; i += 1
            before = after = 0
            while i < len(lines) and not lines[i].startswith(('@@ ', '--- a/')):
                mark, body = lines[i][0], lines[i][1:]
                assert mark in ' +-'
                if mark in ' -':
                    assert old[cursor] == body, (name, cursor)
                    cursor += 1; before += 1
                if mark in ' +':
                    output.append(body); after += 1
                i += 1
            assert (before, after) == (removed, added)
        output.extend(old[cursor:]); result[name] = ''.join(output)
    return result


def sources():
    return {name: body for name, body in all_sources().items() if name.endswith('.lisp')}


def prepare_runtime(out):
    import shutil
    out.mkdir(parents=True, exist_ok=True)
    for path in (c.ROOT / 'runtime/wasm32').glob('*.mjs'):
        shutil.copyfile(path, out / path.name)


def runtime(out):
    module('chain_runtime', HERE.parent / 'loader/run.py').runtime(out)
    source = out / 'collector.c'
    source.write_text(all_sources()['runtime/wasm32/collector.c'])
    c.command(['/usr/local/opt/llvm/bin/clang', '--target=wasm32', '-O2', '-nostdlib', '-fno-builtin',
        '-matomics', '-mbulk-memory', '-Wl,--no-entry', '-Wl,--import-memory',
        '-Wl,--max-memory=2147549184', '-Wl,--shared-memory', '-Wl,--global-base=1048576',
        '-Wl,-z,stack-size=65536', '-Wl,--export=collect', '-Wl,--export=__stack_pointer',
        source, '-o', out / 'collector.wasm'], out / 'collector-build.log')
    c.save(out / 'array-runtime.json', dict(source=c.sha(source),
                                           binary=c.sha(out / 'collector.wasm')))
