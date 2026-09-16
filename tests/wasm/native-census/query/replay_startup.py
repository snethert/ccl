#!/usr/bin/env python3
"""Replay startup analysis from retained inputs, with commands and source snapshots."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import traceback

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / 'tests/wasm/native-census'
REGISTRY = FIXTURES / 'registry-callees'


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(path):
    with (gzip.open(path, 'rt') if path.suffix == '.gz' else path.open()) as f:
        return json.load(f)


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def run(evidence, out):
    require(not out.exists() and ROOT not in out.parents, 'FRESH_OUTPUT_OUTSIDE_CHECKOUT')
    out.mkdir(parents=True)
    inputs = out / 'inputs'
    inputs.mkdir()
    record = dict(status='FAIL', command=[sys.executable, *sys.argv], inputs=[], stages=[])
    sources = sorted(FIXTURES.rglob('*.py')) + [
        FIXTURES / 'startup-closure/seeds.json',
        ROOT / 'doc/WASM/tools/check-census.py', ROOT / 'doc/WASM/contracts/census.schema.json']
    record['sources'] = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    with tarfile.open(out / 'executed-sources.tar.gz', 'w:gz') as archive:
        for path in sources:
            archive.add(path, arcname=str(path.relative_to(ROOT)))
    save(out / 'run.json', record)

    def pinned(relative, expected):
        path = evidence / relative
        actual = sha(path)
        require(actual == expected, 'INPUT_HASH ' + relative)
        record['inputs'].append(dict(locator=relative, sha256=actual))
        save(out / 'run.json', record)
        return path

    def packet(ident):
        index = read(ROOT / 'doc/WASM/evidence/index.json')
        row = next(r for r in index['auxiliary_records'] if r['id'] == ident)
        relative = str(Path(row['locator']).relative_to(Path(read(ROOT / 'doc/WASM/evidence/repository.json')['path'])))
        path = pinned(relative, row['sha256'])
        value = read(path)
        return path.parent, {f['path']: f['sha256'] for f in value['files']}

    def member_archive(folder, pins, name, target, members=None):
        path = pinned(str((folder / name).relative_to(evidence)), pins[name])
        with tarfile.open(path) as archive:
            selected = [m for m in archive.getmembers() if members is None or m.name in members]
            require(members is None or {m.name for m in selected} == set(members), 'ARCHIVE_MEMBERS')
            archive.extractall(target, members=selected, filter='data')

    def stage(name, argv):
        require(record['sources'] == {str(p.relative_to(ROOT)): sha(p) for p in sources}, 'SOURCE_CHANGED')
        entry = dict(name=name, argv=[str(x) for x in argv], cwd=str(ROOT), status='RUNNING')
        record['stages'].append(entry)
        save(out / 'run.json', record)
        with (out / (name + '.log')).open('w') as log:
            result = subprocess.run(entry['argv'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=900)
        entry.update(exit_code=result.returncode, status='PASS' if result.returncode == 0 else 'FAIL')
        save(out / 'run.json', record)
        require(result.returncode == 0, 'STAGE_FAILED ' + name)
        print(name + ': PASS', flush=True)

    try:
        prior, prior_pins = packet('ON-DEMAND-CENSUS-R1')
        finite, finite_pins = packet('CENSUS-FINITE-CHAIN-R1')
        member_archive(prior, prior_pins, 'startup-native.tar.gz', inputs / 'native')
        member_archive(prior, prior_pins, 'startup-analysis.tar.gz', inputs / 'previous')
        member_archive(finite, finite_pins, 'fresh-runs.tar.gz', inputs / 'finite', ['constructor/census.json.gz'])
        base = inputs / 'finite/constructor/census.json.gz'
        require(sha(base) == '6d30938b5c0fd4fedf1355da9bde32177d7d4da84db2576697c92cf1194517ba', 'RETAINED_BASE')
        record['base'] = dict(packet='CENSUS-FINITE-CHAIN-R1', archive='fresh-runs.tar.gz',
                              member='constructor/census.json.gz', sha256=sha(base))
        u1_pins = read(evidence / 'macos-u1-inputs/pins.json')
        require(u1_pins['source_revision'] == 'c994217adc56b3f8a564526cee4695893ac84d86', 'U1_REVISION')
        source = pinned('macos-u1-inputs/source.tar', u1_pins['inputs']['source.tar'])
        with tarfile.open(source) as archive:
            archive.extractall(inputs / 'u1', filter='data')
        common = [sys.executable]
        native = inputs / 'native/compile'
        stage('bodies', common + [REGISTRY / 'seed_bodies.py', '--native', native,
                                 '--source', inputs / 'u1', '--output', out / 'bodies'])
        stage('bindings', common + [REGISTRY / 'seed_bindings.py', '--native', native,
                                   '--bodies', out / 'bodies', '--output', out / 'bindings'])
        stage('graph', common + [REGISTRY / 'seed_transitive_graph.py', '--walk', out / 'bindings',
                                '--bodies', out / 'bodies', '--base', base, '--output', out / 'graph'])
        comparisons = {}
        for name in ('bodies', 'bindings'):
            for old in sorted((inputs / 'previous' / name).iterdir()):
                new = out / name / old.name
                require(sha(new) == sha(old), 'UNCHANGED_ANALYSIS ' + str(new))
                comparisons[str(new.relative_to(out))] = sha(new)
        old_graph = pinned(str((prior / 'startup-graph.json.gz').relative_to(evidence)), prior_pins['startup-graph.json.gz'])
        current = read(out / 'graph/seed-graph.json.gz')
        old = read(old_graph)
        require({k: v for k, v in current.items() if k != 'profile'} ==
                {k: v for k, v in old.items() if k != 'profile'}, 'STARTUP_WORKLIST_CHANGED')
        original_base = read(base)
        combined = read(out / 'graph/census.json.gz')
        expected = dict(original_base, nodes=original_base['nodes'] + current['nodes'],
                        edges=original_base['edges'] + current['edges'], seeds=original_base['seeds'] + current['seeds'])
        require(combined == expected, 'COMBINED_GRAPH')
        save(out / 'comparison.json', dict(unchanged_analysis=comparisons, startup_equal_except_profile=True,
             combined_is_exact_union=True, base_nodes=len(original_base['nodes']), base_edges=len(original_base['edges']),
             combined_nodes=len(combined['nodes']), combined_edges=len(combined['edges']),
             old_profile=old['profile'], new_profile=current['profile']))
        record['outputs'] = {str(p.relative_to(out)): sha(p) for name in ('bodies', 'bindings', 'graph')
                             for p in sorted((out / name).iterdir()) if p.is_file()}
        require(record['sources'] == {str(p.relative_to(ROOT)): sha(p) for p in sources}, 'SOURCE_CHANGED')
        record['status'] = 'PASS'
    except BaseException:
        (out / 'failure.txt').write_text(traceback.format_exc())
        raise
    finally:
        save(out / 'run.json', record)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.evidence.resolve(), args.output.resolve())
