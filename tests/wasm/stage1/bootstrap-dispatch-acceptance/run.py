"""Integrate audit 160's reviewed GCD and cached method dispatch bytes."""
import argparse
import importlib.util
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STORE = ROOT.parent / 'ccl-evidence'
PACKET = STORE / '2026-09-22-stage1-method-dispatch-r1'
spec = importlib.util.spec_from_file_location('stack_acceptance', HERE.parent / 'bootstrap-stack-acceptance/run.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.PACKET = PACKET
base.PACKET_ID = 'STAGE1-METHOD-DISPATCH-R1'
sha, read, save = base.sha, base.read, base.save


def proposal(source, target):
    """Use the final reviewed files, never reapply patches to integrated files."""
    files = base.reviewed_files()
    shutil.copytree(PACKET / 'native/proposal', target)
    for name, reviewed in files.items():
        assert (ROOT / name).read_bytes() == reviewed.read_bytes(), name
        shutil.copyfile(ROOT / name, target / 'files' / name)
    return read(target / 'unit.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('install', 'verify', 'native', 'recount'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True)
    files = base.reviewed_files()
    if args.mode == 'install':
        changes = []
        for name, source in files.items():
            target = ROOT / name
            before = sha(target) if target.exists() else None
            if before != sha(source):
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                changes.append(dict(file=name, before=before, after=sha(target), reviewed=sha(source)))
        save(out / 'changes.json', changes)
        print('Installed', len(changes), 'reviewed files')
        return
    for name, source in files.items():
        assert (ROOT / name).read_bytes() == source.read_bytes(), name
    if args.mode in ('native', 'recount'):
        sys.setrecursionlimit(10000)
        sys.path.insert(0, str(HERE.parent / 'bootstrap-gcd'))
        spec = importlib.util.spec_from_file_location('gcd_native', HERE.parent / 'bootstrap-gcd/native.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if args.mode == 'native':
            module.m.driver.proposal = proposal
            assert module.m.driver.run(STORE / 'macos-u1-inputs',
                STORE / '2026-09-12-native-census-r7/baseline/build/dx86cl64',
                out / 'work', out / 'native', STORE / '2026-09-16-stage1-1a-r2/native') == 0
        else:
            module.backend.proposal = proposal
            spec = importlib.util.spec_from_file_location('file_recount', HERE.parent / 'bootstrap-lexpr-spread/run.py')
            recount = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(recount)
            recount.backend = module.backend
            recount.run(out / 'environment')
            summary = read(out / 'environment/summary.json')
            summary.pop('original_definitions_executed_reused', None)
            summary.pop('non_nil_witness_reused', None)
            save(out / 'recount.json', summary)
        return
    work, count = base.materialize(out)
    used = {}
    for source in (ROOT / 'runtime/wasm32').glob('*.mjs'):
        target = work / 'runtime' / source.name
        if target.exists():
            assert source.read_bytes() == target.read_bytes(), source.name
            used[source.name] = sha(source)
            shutil.copyfile(source, target)
    base.command(['/usr/local/bin/node', work / 'check.mjs', work, out / 'execution.json'], out / 'execution.log')
    assert (out / 'execution.json').read_bytes() == (work / 'execution.json').read_bytes()
    comparisons = sum(row['comparisons'] for row in read(out / 'execution.json')['rows'])
    assert comparisons == read(PACKET / 'summary.json')['comparisons'] == 23916
    save(out / 'integration.json', dict(status='PASS', files={n: sha(ROOT / n) for n in files},
         runtime=used, materialized_artifacts=count, production_execution=sha(out / 'execution.json'),
         original_definitions=549, non_nil_witnesses=514, comparisons=comparisons, slot_credit=False))
    print('PASS: reviewed final files, production imports,', comparisons, 'comparisons')


if __name__ == '__main__':
    main()
