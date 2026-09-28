"""Change one emitted instruction/check and materialize the ordinary bundle."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
from check import expressions

HERE = Path(__file__).resolve().parent
KINDS = {'arithmetic': 'FX-FIT', 'overflow': 'FX-ADD',
         'signed': 'FX-LESS', 'type': 'FX-IDENTITY'}


def mutate(build, out, kind):
    out.mkdir(parents=True)
    for name in ['bundles.json', 'versions.json', 'policy.json', 'd2.mjs', 'benchmark.w32fsl']:
        shutil.copyfile(build/name, out/name)
    (out/'runtime').symlink_to((build/'runtime').resolve(), target_is_directory=True)
    names = {r['name']: r['wire'] for r in json.loads((build/'function-names.json').read_text())}
    records = json.loads((build/'benchmark.records.json').read_text())
    function = KINDS[kind]
    record = next(u['record'] for u in records['units'] if u['name'] == names[function])
    tree = expressions(record[4])
    body = next(n for n in tree if isinstance(n, list) and n[:2] == ['func', '$body'])
    changed = 0

    def walk(node):
        nonlocal changed
        if not isinstance(node, list) or not node:
            return
        if not changed:
            if (kind == 'arithmetic' and node[0] == 'i32.add' and len(node) == 3
                    and all(isinstance(x, list) and x[0] == 'local.get' and x[1].startswith('$tmp') for x in node[1:])):
                node[0] = 'i32.sub'; changed += 1
            elif kind == 'overflow' and node[0] == 'i64.eq' and node[1] == ['local.get', '$wide']:
                node[:] = ['i32.const', '1']; changed += 1
            elif kind == 'signed' and node[0] == 'i32.lt_s':
                node[0] = 'i32.lt_u'; changed += 1
            elif (kind == 'type' and node[0] == 'if' and isinstance(node[1], list)
                  and node[1][0] == 'i32.and' and node[1][-1] == ['i32.const', '3']):
                node[1] = ['i32.const', '0']; changed += 1
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
