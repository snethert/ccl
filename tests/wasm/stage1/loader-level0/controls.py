from pathlib import Path
import json
import shutil
import subprocess
import sys
import product
import storage

HERE = Path(__file__).resolve().parent
c = product.c


def run(out, execution):
    out.mkdir(parents=True)
    product.prepare_runtime(out / 'runtime')
    shutil.copyfile(HERE / 'controls.mjs', out / 'controls.mjs')
    for name in ('policy.json', 'versions.json'):
        shutil.copyfile(execution / name, out / name)
    args = [c.NODE, out / 'controls.mjs', execution / 'keywords/artifacts']
    c.command(args, out / 'controls.log', timeout=120)
    positive = json.loads((out / 'controls.log').read_text())
    path = out / 'runtime/cross-image.mjs'
    source = path.read_text()
    mutants = []
    for name, clause in [
        ('keyword wire type', "row.arity[5].every(w=>typeof w==='string')"),
        ('keywords without key flag', '(row.arity[3]||row.arity[5].length===0)'),
        ('missing keyword wire', 'row.arity[5].every(w=>Object.hasOwn(symbols,w))')]:
        assert source.count(clause) == 1
        path.write_text(source.replace(clause, 'true'))
        log = out / (name.replace(' ', '-') + '.log')
        with log.open('w') as stream:
            p = subprocess.run([str(a) for a in args], stdout=stream, stderr=subprocess.STDOUT, timeout=120)
        assert p.returncode != 0 and 'Missing expected exception: ' + name in log.read_text()
        mutants.append(dict(name=name, status='KILLED', mutated_sha256=c.sha(path)))
    path.write_text(source)
    executor = (HERE / 'execute.mjs').read_text()
    clause = 'coldResults.push(callObject(get(list+3),[]));'
    assert executor.count(clause) == 1
    omitted = out / 'omit-initializers.mjs'
    omitted.write_text(executor.replace(clause, 'coldResults.push([]);'))
    log = out / 'omit-initializers.log'
    with log.open('w') as stream:
        p = subprocess.run([str(a) for a in [c.NODE, omitted, execution / 'prefix/artifacts',
                                             execution / 'runtime', HERE / 'prefix-cases.json']],
                           stdout=stream, stderr=subprocess.STDOUT, timeout=120)
    assert p.returncode != 0 and 'initializers set *PACKAGE*' in log.read_text()
    result = dict(status='PASS', controls=positive, mutants=mutants,
                  omitted_initializers=dict(status='KILLED', mutated_sha256=c.sha(omitted)))
    c.save(out / 'summary.json', result)
    return result


if __name__ == '__main__':
    with storage.lease([Path(sys.argv[1])]):
        print(json.dumps(run(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())))
