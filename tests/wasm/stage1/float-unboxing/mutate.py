"""Alter one emitted operation/check, then use the existing bundle materializer."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'loader-target'))
from record_reader import read_records
from check import expressions

HERE = Path(__file__).resolve().parent


def mutate(build, out, kind):
    out.mkdir(parents=True)
    for name in ['bundles.json', 'versions.json', 'policy.json', 'd2.mjs', 'benchmark.w32fsl']:
        shutil.copyfile(build/name, out/name)
    (out/'runtime').symlink_to((build/'runtime').resolve(), target_is_directory=True)
    names = {r['name']: r['wire'] for r in json.loads((build/'function-names.json').read_text())}
    records = read_records(build/'benchmark.records.json')
    function = {'arithmetic': 'FU-DADD', 'rounding': 'FU-ROUND-SINGLE',
                'safety': 'FU-SAFE', 'type': 'FU-DADD'}[kind]
    record = next(u['record'] for u in records['units'] if u['name'] == names[function])
    tree = expressions(record[4])
    body = next(n for n in tree if isinstance(n, list) and n[:2] == ['func', '$body'])
    changed = 0

    def walk(node):
        nonlocal changed
        if not isinstance(node, list) or not node:
            return
        if not changed:
            if kind == 'arithmetic' and node[0] == 'f64.add':
                node[0] = 'f64.sub'; changed += 1
            elif kind == 'safety' and node[:2] == ['call', '$float_slow']:
                assert node[-1] == ['i32.const', '1']
                node[-1] = ['i32.const', '0']; changed += 1
            elif (kind == 'type' and node[0] == 'if' and node[1][0] == 'i32.ne'
                  and node[1][1][:2] == ['call', '$real_operand']
                  and node[1][2] == ['i32.const', '64']):
                node[1] = ['i32.const', '0']; changed += 1
            elif kind == 'rounding' and node[0] == 'f32.sub' and node[1][0] == 'f32.add':
                old = copy.deepcopy(node)
                promote = lambda x: ['f64.promote_f32', x]
                node[:] = ['f32.demote_f64', ['f64.sub',
                           ['f64.add', promote(old[1][1]), promote(old[1][2])], promote(old[2])]]
                changed += 1
        for child in node:
            walk(child)

    walk(body)
    assert changed == 1, (kind, changed)
    def wat(node):
        return '('+' '.join(wat(x) for x in node)+')' if isinstance(node, list) else node
    record[4] = wat(tree)
    (out/'benchmark.records.json').write_text(json.dumps(records)+'\n')
    (out/'mutation.json').write_text(json.dumps(dict(kind=kind, function=function, changes=changed), indent=2)+'\n')
    with (out/'materialize.log').open('w') as log:
        subprocess.run(['node', str(HERE.parent/'loader-target/bundles.mjs'), str(out), '--v1'],
                       stdout=log, stderr=subprocess.STDOUT, check=True)


if __name__ == '__main__':
    mutate(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), sys.argv[3])
