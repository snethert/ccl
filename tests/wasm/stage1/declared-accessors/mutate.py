"""Materialize one independently corrupted accessor in the ordinary bundle."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'loader-target'))
from record_reader import read_records
from check import expressions, nodes

HERE = Path(__file__).resolve().parent
KINDS = {'car': 'DA-CAR', 'nil': 'DA-LIST-CAR', 'index': 'DA-BOUNDED',
         'bounds': 'DA-FIXED', 'length': 'DA-SAFE-VECTOR'}


def mutate(build, out, kind):
    out.mkdir(parents=True)
    for name in ['bundles.json', 'versions.json', 'policy.json', 'd2.mjs', 'benchmark.w32fsl']:
        shutil.copyfile(build/name, out/name)
    (out/'runtime').symlink_to((build/'runtime').resolve(), target_is_directory=True)
    names = {r['name']: r['wire'] for r in json.loads((build/'function-names.json').read_text())}
    records = read_records(build/'benchmark.records.json')
    record = next(u['record'] for u in records['units'] if u['name'] == names[KINDS[kind]])
    tree = expressions(record[4])
    body = next(n for n in tree if isinstance(n, list) and n[:2] == ['func', '$body'])
    candidates = []
    for node in nodes(body):
        if (kind == 'car' and node[:1] == ['i32.load'] and len(node) == 2
                and node[1][:1] == ['i32.add'] and node[1][-1] == ['i32.const', '3']):
            candidates.append((node[1], -1, ['i32.const', '-1']))
        elif (kind == 'nil' and node[:1] == ['if'] and node[1] == ['result', 'i32']
              and node[2][:1] == ['i32.eq'] and node[2][-1] == ['i32.const', '77825']
              and node[3] == ['then', ['i32.const', '77825']]):
            candidates.append((node[3], 1, ['i32.const', '0']))
        elif (kind == 'index' and node[:1] == ['i32.load'] and len(node) == 2
              and node[1][:1] == ['i32.add'] and node[1][1][:1] == ['i32.sub']
              and node[1][1][-1] == ['i32.const', '2']):
            candidates.append((node[1], 2, ['i32.xor', node[1][2], ['i32.const', '4']]))
        elif (kind == 'bounds' and node[:1] == ['i32.ge_u']
              and node[1][:1] == ['i32.shr_u'] and node[-1] == ['i32.const', '4']):
            candidates.append((node, 0, 'i32.gt_u'))
        elif (kind == 'length' and node[:1] == ['i32.eq']
              and node[1][:1] == ['i32.shr_u'] and node[1][-1] == ['i32.const', '8']
              and node[-1] == ['i32.const', '4']):
            candidates.append((node, slice(None), ['i32.const', '1']))
    assert len(candidates) == 1, (kind, len(candidates))
    node, position, replacement = candidates[0]
    node[position] = replacement

    def wat(node):
        return '('+' '.join(wat(x) for x in node)+')' if isinstance(node, list) else node
    record[4] = wat(tree)
    (out/'benchmark.records.json').write_text(json.dumps(records)+'\n')
    (out/'mutation.json').write_text(json.dumps(dict(kind=kind, function=KINDS[kind], changes=1), indent=2)+'\n')
    with (out/'materialize.log').open('w') as log:
        subprocess.run(['node', str(HERE.parent/'loader-target/bundles.mjs'), str(out), '--v1'],
                       stdout=log, stderr=subprocess.STDOUT, check=True)


if __name__ == '__main__':
    mutate(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), sys.argv[3])
