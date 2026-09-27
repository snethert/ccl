"""Join observed boot calls to installed code identities and source branches.

Native name matches are antecedents, never original-body execution credit.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys


def read(path): return json.loads(path.read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def run(report, image, sources, directories):
    boot, inventory = read(report), read(sources)
    assert boot['ready'] and not boot['traceFrom'], 'complete boot observation required'
    assert boot['execution'], 'empty execution is not a census'
    manifest = read(image/'boot/artifacts/manifest.json')
    assert manifest['heap']['digest'] == boot['heapDigest']
    assert manifest['codeDigest'] == boot['codeDigest']
    sets = {'boot0': read(image/'boot/artifacts/code-set.json')}
    origins = {'boot0': None}
    inputs = {r['path']: r['sha256'] for r in boot['bundleInputs']}
    available = {}
    for directory in directories:
        for row in read(directory/'bundle-manifest.json')['files']:
            available[row['path']] = directory, row
    for path, expected in inputs.items():
        directory, row = available[path]
        data = (directory/row['bundle']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected == row['sha256']
        assert data[:8] == b'W32B\x01\x00\x00\x00'
        n = struct.unpack_from('<I', data, 8)[0]
        sets[path] = json.loads(data[16:16+n])['codeSet']
        origins[path] = row['source']
    modules = {path: {r['name']: r for r in code['modules']} for path, code in sets.items()}
    primitives = inventory['target_primitive_definitions']
    rows = []
    for event in boot['execution']:
        assert event['count'] > 0
        path, module = event['file'], event['module']
        code = modules[path][module]
        callable_name = (event['callable'] or {}).get('function')
        name = callable_name.get('symbol') if isinstance(callable_name, dict) else None
        matches = [p for p in primitives if p['name'] == name and
                   (path == 'boot0' or p['source'] == origins[path])]
        branches = [r for r in inventory['sites'] if r['source'] == origins[path]]
        rows.append(dict(**event, source=origins[path], code_identity=code,
                         target_primitive_candidates=matches,
                         source_branch_sites=[dict(line=r['line'], classification=r['classification'],
                                                   form_sha256=r['form_sha256']) for r in branches],
                         original_execution_credit=False))
    assert len(rows) == len({(r['file'], r['module']) for r in rows})
    return dict(status='ENUMERATED', inputs={str(p): digest(p) for p in (report, sources)},
                heap=boot['heapDigest'], code=boot['codeDigest'], entries=rows,
                reached_modules=len(rows), calls=sum(r['count'] for r in rows),
                by_file=dict(Counter(r['file'] for r in rows)),
                primitive_candidate_modules=sum(bool(r['target_primitive_candidates']) for r in rows),
                scope='Every observed module is joined to its installed bundle/code identity. '
                      'Bundle origins and reader branches are enumerated, not inferred to be executed branches. '
                      'Level-0 modules retain their image identity; name-based primitive matches are candidates. '
                      'Anonymous/generated code and backend lowering routes gain no original-body credit. '
                      'This dynamic census describes these startup inputs, not all possible callable paths.')


if __name__ == '__main__':
    report, image, sources, output, *directories = map(Path, sys.argv[1:])
    result = run(report, image, sources, directories)
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'], result['reached_modules'], 'observed modules')
