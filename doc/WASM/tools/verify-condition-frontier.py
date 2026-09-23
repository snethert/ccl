#!/usr/bin/env python3
"""Replay the condition packet without hashing each control's corpus aliases."""
import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE_REVISION = '7212d982200c017930a0e7d9fcc9f02b9fa74374'
FIXTURE_PATH = Path('tests/wasm/stage1/bootstrap-condition-frontier')
DEFAULT_PACKET = ROOT.parent / 'ccl-evidence/2026-09-22-stage1-bootstrap-condition-frontier-r1'
PREFIX = 'numeric/condition-faults/'


def canonical_records(records):
    """Collapse only a control path's identical, named base-corpus counterpart."""
    kept, aliases = {}, {}
    for name, digest in records.items():
        target = 'numeric/' + name.split('/', 3)[3] if name.startswith(PREFIX) else None
        if target is not None and records.get(target) == digest:
            aliases[name] = target
        else:
            kept[name] = digest
    return kept, aliases


def write_module_digests(environment):
    """Retain the original file compiler's manifest without hashing aliases."""
    modules = {str(p.relative_to(environment)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted((environment / 'files').rglob('*.wat'))}
    (environment / 'module-digests.json').write_text(
        json.dumps(modules, indent=2, sort_keys=True) + '\n')


@contextmanager
def source_snapshot(root, revision):
    """Use committed sources for pins, derivation and both replay modes."""
    commit = subprocess.check_output(
        ['git', '-C', str(root), 'rev-parse', '--verify', revision + '^{commit}'],
        text=True).strip()
    with tempfile.TemporaryDirectory(prefix='ccl-condition-source-') as directory:
        parent = Path(directory)
        source = parent / 'ccl'
        source.mkdir()
        (parent / 'ccl-evidence').symlink_to(root.parent / 'ccl-evidence', target_is_directory=True)
        with tempfile.TemporaryFile() as archive:
            subprocess.run(['git', '-C', str(root), 'archive', commit], stdout=archive, check=True)
            archive.seek(0)
            subprocess.run(['tar', '-xf', '-', '-C', str(source)], stdin=archive, check=True)
        yield source, commit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path, default=DEFAULT_PACKET)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path, help='Fresh compile, execution and controls')
    mode.add_argument('--replay', type=Path, help='Check an already qualified replay, without rerunning it')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--source-revision', default=SOURCE_REVISION,
                        help='Committed source revision; all packet pins must still match')
    args = parser.parse_args()
    with source_snapshot(ROOT, args.source_revision) as (source, commit):
        verify(args, source, commit)


def verify(args, source, commit):
    fixture = source / FIXTURE_PATH
    sys.path.insert(0, str(fixture))
    spec = importlib.util.spec_from_file_location('condition_packet', fixture / 'packet.py')
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    sha, read = original.sha, original.read
    packet = args.packet.resolve()
    index = read(ROOT / 'doc/WASM/evidence/index.json')['auxiliary_records']
    binding = next(row for row in index if row['id'] == original.ID)
    assert sha(packet / 'packet.json') == binding['sha256'], 'packet binding'
    entries = read(packet / 'packet.json')['files']
    assert {row['path'] for row in entries} == {str(p.relative_to(packet)) for p in original.files(packet) if p.name != 'packet.json'}, 'packet file inventory'
    for row in entries:
        assert sha(packet / row['path']) == row['sha256'], row['path']
    assert original.pins() == read(packet / 'source-pins.json'), 'source pins'
    assert original.dependencies() == read(packet / 'dependencies.json'), 'dependencies'
    assert original.base.parent.parent.base.tools() == read(packet / 'tools.json'), 'tools'
    expected, aliases = canonical_records(read(packet / 'deterministic.json'))
    if args.output:
        output = args.output.resolve()
        output.mkdir()
        for script, directory in [('run.py', 'environment'), ('numeric.py', 'numeric'), ('faults.py', 'numeric')]:
            subprocess.run([sys.executable, fixture / script, output / directory], cwd=source, check=True)
        original.reports(output / 'environment', output / 'numeric')
        write_module_digests(output / 'environment')
    else:
        output = args.replay.resolve()
        reference = ROOT.parent / 'ccl-evidence/2026-09-22-stage1-bootstrap-condition-frontier-verification/verification.json'
        binding = next(row for row in index if Path(row['locator']) == reference)
        assert sha(reference) == binding['sha256'], 'qualified replay binding'
        assert sha(output / 'verification.json') == sha(reference), 'previous replay result'
    original.source_check(output / 'numeric', packet / 'native')
    for name, digest in expected.items():
        assert sha(output / name) == digest, name
    # Do not hash 12,480 repeated files. Assert their alias edges instead, so a
    # replaced symlink cannot silently become an unchecked control input.
    for name, target in aliases.items():
        path = output / name
        assert path.is_symlink() and path.resolve() == (output / target).resolve(), name
    record = dict(status='PASS', canonical_artifacts=len(expected),
                  control_artifacts=sum(name.startswith(PREFIX) for name in expected),
                  alias_edges_checked=len(aliases), repeated_content_hashes=0,
                  execution='fresh' if args.output else 'reused qualified replay',
                  new_execution_credit=0, source_revision=commit, packet_sha256=sha(packet / 'packet.json'),
                  deterministic_manifest_sha256=sha(packet / 'deterministic.json'),
                  verifier_sha256=sha(Path(__file__)))
    args.report.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(json.dumps(record, sort_keys=True))


if __name__ == '__main__':
    main()
