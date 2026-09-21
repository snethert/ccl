"""Reader-form qualification for the user's narrow R6 source-location allowance."""
import hashlib, json, os, shutil, subprocess, sys, tarfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EVIDENCE = ROOT.parent / 'ccl-evidence'
CORE = EVIDENCE / '2026-09-21-stage1-bootstrap-core-r1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def run(out):
    out = Path(out).resolve(); out.mkdir()
    src = out / 'u1'; src.mkdir()
    with tarfile.open(EVIDENCE / 'macos-u1-inputs/source.tar') as archive:
        archive.extractall(src, filter='data')
    proposal = out / 'proposal'
    shutil.copytree(CORE / 'native/proposal/files/level-0', proposal / 'level-0')
    kernel = EVIDENCE / '2026-09-12-native-census-r7/baseline/build/dx86cl64'
    image = EVIDENCE / '2026-09-16-stage1-1a-r2/native/baseline.image'
    observer = ROOT / 'tests/wasm/native-census/observer.lisp'
    executable = out / 'dx86cl64'; shutil.copyfile(kernel, executable); executable.chmod(0o755)
    command = [str(executable), '--image-name', str(image), '--no-init', '--batch',
               '--load', str(observer), '--load', str(HERE / 'readers.lisp')]
    def execute(name):
        dest = out / name; dest.mkdir()
        env = dict(os.environ, CCL_DEFAULT_DIRECTORY=str(src)+'/', READER_U1=str(src)+'/',
                   READER_PROPOSAL=str(proposal)+'/', READER_OUTPUT=str(dest)+'/')
        with (dest / 'run.log').open('w') as log:
            proc = subprocess.run(command, env=env, cwd=src, stdout=log, stderr=log, timeout=60)
        return proc.returncode, dest
    code, positive = execute('positive'); assert code == 0
    rows = json.loads((positive / 'readers.json').read_text())['rows']
    expected = json.loads((CORE / 'native/baseline-snapshot.json').read_text())['targets']
    targets = {x['name'].lower().split('::')[-1] for x in expected}
    assert {x['target'] for x in rows} == targets and len(rows) == 51
    assert all(x['equal'] for x in rows)
    changed = proposal / 'level-0/l0-pred.lisp'; original = changed.read_text()
    try:
        changed.write_text(original+'\n#+ppc32-target (defun r6-reader-leak () t)\n')
        code, fault = execute('non-host-branch-fault')
        assert code != 0 and 'Existing-target reader changed: :DARWINPPC32' in (fault / 'run.log').read_text()
    finally:
        changed.write_text(original)
    # Bind the exact decoded-code evidence already reviewed in audit 145.
    native = {name: sha(CORE / 'native' / name) for name in
              ('run.json', 'l0-def-comparison.json', 'l0-pred-comparison.json', 'l0-utils-comparison.json')}
    own = {str(p.relative_to(ROOT)): sha(p) for p in [HERE/'run.py', HERE/'readers.lisp', observer]}
    dependencies = {str(p.relative_to(EVIDENCE)): sha(p) for p in
                    [kernel, image, EVIDENCE/'macos-u1-inputs/source.tar', CORE/'packet.json']}
    sources = {str(p.relative_to(proposal)): sha(p) for p in proposal.rglob('*.lisp')}
    result = dict(status='PASS',profiles=len(targets),reader_comparisons=len(rows),
                  forms=sum(x['forms'] for x in rows),rejected_non_host_control=True,
                  native_code_evidence=native,source_pins=own,dependencies=dependencies,proposal=sources,
                  scope='Identical complete forms under all 17 existing target readers. Decode/native execution evidence is the unchanged reviewed macOS qualification; no foreign machine-code execution claimed.')
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    shutil.rmtree(src); shutil.rmtree(proposal); executable.unlink()
    print(json.dumps(result,indent=2))

if __name__ == '__main__': run(sys.argv[1])
