"""Collector refusals, transaction checks and audit-182 remove-one-clause faults."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import product
import storage

c = product.c


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    product.runtime(out)
    schema = c.read(product.HERE / 'counter-schema.json')
    parent = c.read(c.ROOT / schema['parent'])
    assert c.sha(c.ROOT / schema['parent']) == schema['parent_sha256']
    assert parent['reserved'] == schema['reserved_before'] == [204, 256]
    assert schema['reserved_after'] == [208, 256] and schema['size_bytes'] == parent['size_bytes']
    field = schema['append_field']
    assert (field['offset'], field['width'], field['classification'], field['owner']) == (204, 4, 'bounded', 'collector')
    assert all(f['offset'] + f['width'] <= 204 for f in parent['fields'])
    code = (product.HERE.parent / 'collector-owner/check.mjs').read_text()
    extra = (product.HERE.parent / 'loader-aref/collector-cases.mjs').read_text()
    extra += (product.HERE / 'collector-cases.mjs').read_text()
    anchor = 'fs.writeFileSync(process.argv[3],'
    assert code.count(anchor) == 1
    (out / 'check.mjs').write_text(code.replace(anchor, extra + '\n' + anchor))
    shutil.copyfile(out / 'collector-owner.mjs', out / 'owner.mjs')
    for name in ('sha256.mjs', 'bytes.mjs'):
        shutil.copyfile(c.ROOT / 'runtime/wasm32' / name, out / name)
    c.command([c.NODE, out / 'check.mjs', out / 'collector.wasm', out / 'result.json'], out / 'check.log')
    # Each mutation is anchored in the initialized native-vector branch.
    source = (out / 'collector.c').read_text()
    a, b = source.index('    }else if(LOAD(p+4)==0){'), source.index('    /* Keep the existing strong')
    native = source[a:b]
    changes = [
        ('MC1', '||LOAD(p+20)!=NIL', '', 'native-hash-finalization-list'),
        ('MC2', '     if(LOAD(p+40)!=NIL&&((LOAD(p+40)&3)||LOAD(p+40)/4>=n))return reject(s,BAD_OBJECT);', '', 'native-hash-cache-index-limit'),
        ('MC3', '||((n-14)&1)', '', 'native-hash-odd-cell-count'),
        ('MC4', '||capacity>16384', '', 'native-hash-capacity'),
        ('MC5', '(LOAD(p+12)&3)||', '', 'native-hash-gc-count-type'),
        ('MC7', '     for(U j=0;j<n;j++)if(LOAD(p+4+4*j)!=51)return reject(s,BAD_OBJECT);', '', 'mixed-uninitialized-hash'),
        ('MC8', '||LOAD(p+52)!=capacity*4', '', 'native-hash-size'),
        ('MC9', '||LOAD(p+32)/4>capacity', '', 'native-hash-deleted-count'),
    ]
    faults = []
    for name, old, new, label in changes:
        section = source if name == 'MC7' else native
        assert section.count(old) == 1, name
        changed = section.replace(old, new)
        if name == 'MC9':
            clause = '||LOAD(p+32)/4+LOAD(p+36)/4>capacity'
            assert changed.count(clause) == 1
            changed = changed.replace(clause, '')
        faults.append((name, changed if name == 'MC7' else source[:a] + changed + source[b:], label))
    gate = '&&(LOAD(o->moved+8)&(1u<<30))'
    assert source.count(gate) == 1
    faults.append(('MC6', source.replace(gate, ''), 'native-hash-untracked-key-movement'))
    gate = ' if(LOAD(s->tcr+204)>=536870911u)return reject(s,BAD_OWNER);'
    assert source.count(gate) == 1
    faults.append(('COUNT-BOUND', source.replace(gate, ''), 'raw-collection-count-exhaustion'))
    results = []
    for name, body, label in faults:
        folder = out / name; folder.mkdir(exist_ok=True)
        path = folder / 'collector.c'; path.write_text(body)
        binary = folder / 'collector.wasm'
        c.command(['/usr/local/opt/llvm/bin/clang', '--target=wasm32', '-O2', '-nostdlib', '-fno-builtin',
            '-matomics', '-mbulk-memory', '-Wl,--no-entry', '-Wl,--import-memory', '-Wl,--shared-memory',
            '-Wl,--max-memory=2147549184', '-Wl,--global-base=1048576', '-Wl,-z,stack-size=65536',
            '-Wl,--export=collect', '-Wl,--export=__stack_pointer', path, '-o', binary], folder / 'build.log')
        with (folder / 'check.log').open('w') as stream:
            proc = subprocess.run([str(c.NODE), str(out / 'check.mjs'), str(binary), str(folder / 'unexpected.json')],
                                  stdout=stream, stderr=subprocess.STDOUT, timeout=60)
        log = (folder / 'check.log').read_text()
        assert proc.returncode != 0 and label in log and 'AssertionError' in log, (name, log[-2000:])
        results.append(dict(name=name, status='KILLED', control=label, source=c.sha(path), binary=c.sha(binary)))
    result = dict(status='PASS', runtime=c.read(out / 'array-runtime.json'),
                  checks=c.read(out / 'result.json'), mutants=results)
    c.save(out / 'summary.json', result)
    print(dict(status='PASS', checks=result['checks']['checks'], killed=len(results)))


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]): run(Path(sys.argv[1]).resolve())
