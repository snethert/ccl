"""Execute the whole-file loader image with native arithmetic observations."""
from pathlib import Path
import sys
import product
import storage

HERE = product.HERE
PARENT = HERE.parent / 'loader-aref'
c = product.c


def cases():
    parent = product.module('pointer_cases', HERE.parent / 'loader-new-ptr/exercise.py')
    result = parent.cases()
    def add(name, args):
        result.append(dict(id=name + '-' + '-'.join(map(str, args)),
                           call=['CCL', 'LOADER-' + name.upper()], args=args))
    for name in ('bindings', 'names', 'bits', 'macros', 'specials', 'setf-names', 'bootstrap', 'allocation', 'definition', 'hold-name', 'release-name'):
        add('def-' + name, [])
    for name in ('float-signs', 'float-decode', 'float-scale', 'float-copy', 'error-strings', 'def-funcallable-bits'):
        add(name, [])
    for kind in range(10):
        add('float-subnormal', [kind])
    return result


def run(out):
    product.module('definition_hash_leaves', HERE / 'hash-leaves.py').prepare(out)
    driver = product.module('ptr_execution', PARENT / 'exercise.py')
    driver.HERE = PARENT
    driver.product = product
    save, command = c.save, c.command

    def write(path, value):
        if path == out / 'cases.json':
            value.extend(cases())
            script = out / 'execute.mjs'
            text = script.read_text()
            text = text.replace('assert(depth<64', 'assert(depth<256')
            text = text.replace('  if(tag===191)',
                '  if(tag===130)return {istruct:decode(get(get(v-2)+3),depth+1),slots:(get(v-6)>>>8)-1};\n  if(tag===191)')
            assert text.count("from './controls.mjs'") == 1
            # The owner still selects placement; only table capacity grows.
            text = text.replace('512', '1024')
            text = text.replace("['c-stack',1048576,1114112]",
                "['image',280000,280096],['c-stack',1048576,1114112]")
            anchor = '// Drain the package witness'
            assert text.count(anchor) == 1
            text = text.replace(anchor, '''import {installHashLeaves} from './hash-leaves.mjs';
const hashLeaves=await installHashLeaves({memory,env,get,put,binary,hash,symbolAddress,layout,registry:REGISTRY,N,
 pins:JSON.parse(fs.readFileSync(new URL('./hash-leaves.json',import.meta.url)))});
''' + anchor)
            text = text.replace('JSON.stringify({refusals,', 'JSON.stringify({hashLeaves,refusals,')
            (out / 'hash-leaves.mjs').write_text((HERE / 'hash-leaves.mjs').read_text())
            text = text.replace("from './controls.mjs'", "from './pointer-controls.mjs'")
            script.write_text(text)
            (out / 'pointer-controls.mjs').write_text((HERE.parent / 'loader-new-ptr/controls.mjs').read_text())
            (out / 'definition-controls.mjs').write_text((HERE / 'controls.mjs').read_text())
            script.write_text(script.read_text().replace("from './pointer-controls.mjs'", "from './definition-controls.mjs'"))
        return save(path, value)

    def execute(argv, log, env=None, **kwargs):
        if env and 'LOADER_SOURCE' in env and Path(env['LOADER_SOURCE']).name == 'native-source':
            with (Path(env['LOADER_SOURCE']) / 'packages.lisp').open('a') as stream:
                stream.write((HERE.parent / 'loader-new-ptr/witnesses.lisp').read_text())
                stream.write((HERE / 'witnesses.lisp').read_text())
        return command(argv, log, env, **kwargs)

    c.save, c.command = write, execute
    try:
        result = driver.run(out)
        for row in result['runs'].values():
            assert len(row['refusals']) == 116
            assert len(row['observations']) == 110
        return result
    finally:
        c.save, c.command = save, command


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        run(Path(sys.argv[1]).resolve())
