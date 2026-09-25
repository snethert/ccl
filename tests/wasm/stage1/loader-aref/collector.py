"""Exercise both new scanner layouts, refusals, and exact guard deletions."""
from pathlib import Path
import shutil
import subprocess
import sys
import product
import storage

c = product.c
HERE = product.HERE


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    source = HERE / 'files/runtime/wasm32/collector.c'
    original = source.read_text()
    base = (HERE.parent / 'collector-owner/check.mjs').read_text()
    anchor = 'fs.writeFileSync(process.argv[3],'
    assert base.count(anchor) == 1
    (out / 'check.mjs').write_text(base.replace(anchor, (HERE / 'collector-cases.mjs').read_text() + '\n' + anchor))
    for name in ('collector-owner.mjs', 'sha256.mjs', 'bytes.mjs'):
        shutil.copyfile(c.ROOT / 'runtime/wasm32' / name, out / ('owner.mjs' if name == 'collector-owner.mjs' else name))
    variants = [('positive', None, None),
        ('minimum', 'n<5||', 'array-minimum-width'),
        ('rank', 'if(tag==234&&LOAD(p+4)!=(n-5)*4)return reject(s,BAD_OBJECT);', 'array-rank-width'),
        ('vector-width', 'if(tag==242&&n!=5)return reject(s,BAD_OBJECT);', 'vector-header-width')]
    rows = []
    for name, clause, case in variants:
        text = original
        if clause:
            assert text.count(clause) == 1
            text = text.replace(clause, '')
        path = out / (name + '.c')
        path.write_text(text)
        binary = out / (name + '.wasm')
        c.command(['/usr/local/opt/llvm/bin/clang', '--target=wasm32', '-O2', '-nostdlib', '-fno-builtin',
            '-matomics', '-mbulk-memory', '-Wl,--no-entry', '-Wl,--import-memory',
            '-Wl,--max-memory=2147549184', '-Wl,--shared-memory', '-Wl,--global-base=1048576',
            '-Wl,-z,stack-size=65536', '-Wl,--export=collect', '-Wl,--export=__stack_pointer',
            path, '-o', binary], out / (name + '-build.log'))
        try:
            c.command([c.NODE, out / 'check.mjs', binary, out / (name + '.json')], out / (name + '.log'))
        except subprocess.CalledProcessError:
            assert clause and 'Missing expected exception: ' + case in (out / (name + '.log')).read_text()
            rows.append(dict(name=name, case=case, status='KILLED', source=c.sha(path)))
        else:
            assert clause is None, name + ' survived'
    result = dict(status='PASS', source=c.sha(source), positive=c.read(out / 'positive.json'), mutants=rows)
    c.save(out / 'summary.json', result)
    print(dict(status='PASS', checks=result['positive']['checks'], mutants=len(rows)))


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
