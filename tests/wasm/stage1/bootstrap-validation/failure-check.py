"""Prove a failed setup/comparison is retained and later variants still run."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(base, out):
    out.mkdir(parents=True, exist_ok=False)
    # Share immutable compiled inputs. Only the oracle is a private copy;
    # neither the qualified corpus nor its execution record is modified.
    for source in base.iterdir():
        if source.name != 'compiled':
            (out / source.name).symlink_to(source, target_is_directory=source.is_dir())
    compiled = out / 'compiled'
    compiled.mkdir()
    for source in (base / 'compiled').iterdir():
        if source.name != 'native.json':
            (compiled / source.name).symlink_to(source, target_is_directory=source.is_dir())
    oracle = base / 'compiled/native.json'
    original = sha(oracle)
    rows = json.loads(oracle.read_text())
    # Use one Worker so the unaffected case must follow both failures.
    rows[0]['values'] = ['deliberately incorrect oracle']
    rows[1]['args'] = [{'unsupported_failure_control_input': True}]
    (compiled / 'native.json').write_text(json.dumps(rows) + '\n')
    plan = dict(workers=1, indices=[0, 1, 2], controls=False, controlIndices=[])
    (out / 'failure-plan.json').write_text(json.dumps(plan) + '\n')
    process = subprocess.run(['node', str(base / 'parallel.mjs'), str(out),
                              str(out / 'failure-plan.json'), str(out / 'failure-results.json')],
                             capture_output=True, text=True, timeout=240)
    (out / 'failure-run.log').write_text(process.stdout + process.stderr)
    result = json.loads((out / 'failure-results.json').read_text())
    ids = json.loads((base / 'case-ids.json').read_text())
    assert process.returncode == 1 and result['status'] == 'FAIL'
    assert result['complete'] and len(result['rows']) == 12
    assert len(result['failures']) == 8 and result['comparisons'] == 4
    for i in range(3):
        variants = [r for r in result['rows'] if r['caseId'] == ids[i]]
        assert len(variants) == 4
        assert all((r.get('status') == 'FAIL') == (i < 2) for r in variants)
    assert sha(oracle) == original
    report = dict(status='PASS', failedVariantsRetained=8, laterPassingVariants=4,
                  failedRunExitCode=process.returncode, originalOracle=original,
                  mutatedOracle=sha(compiled / 'native.json'),
                  runner=sha(base / 'parallel.mjs'), worker=sha(base / 'worker.mjs'),
                  control=sha(Path(__file__)), result=sha(out / 'failure-results.json'))
    (out / 'failure-check.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    run(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
