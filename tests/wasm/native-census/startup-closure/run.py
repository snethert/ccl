#!/usr/bin/env python3
"""Inspect a clean image and prepare a compact review packet from retained r7 inputs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from candidates import build, check_coverage
from test_candidates import run as controls

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from reversible import digest, save


def run(kernel, image, graph, output):
    if output.exists(): raise ValueError('output must be new')
    output.mkdir(parents=True)
    observer = HERE.parent / 'observer.lisp'
    inspector = HERE / 'image-inventory.lisp'
    seed_path = HERE / 'seeds.json'
    # Verify direct runtime inputs once. No baseline build, source patch, image
    # save, whole-archive walk or copies of previously retained input artifacts.
    paths = [kernel, image, graph, observer, inspector, seed_path, Path(__file__).resolve(),
             HERE / 'candidates.py', HERE / 'test_candidates.py']
    identities = {str(p): digest(p) for p in paths}
    pinned_clean = image.parents[2] / 'results.json'
    baseline = json.loads(pinned_clean.read_text())
    if (baseline['source_revision'] != 'c994217adc56b3f8a564526cee4695893ac84d86' or
            baseline['execution_status'] != 'PASS'):
        raise ValueError('requires the successful U1 native baseline')
    clean_artifact = next((a for a in baseline['artifacts']
                           if a['path'] == str(image.relative_to(pinned_clean.parent))), None)
    if not clean_artifact or clean_artifact['sha256'] != identities[str(image)] or '/baseline/build/' not in str(image):
        raise ValueError('image is not the retained clean baseline artifact')
    clean_kernel = next((a for a in baseline['artifacts'] if a['path'] == 'baseline/build/dx86cl64'), None)
    if not clean_kernel or clean_kernel['sha256'] != identities[str(kernel)]:
        raise ValueError('kernel differs from the retained clean baseline')
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'C', 'LC_ALL': 'C',
           'CCL_DEFAULT_DIRECTORY': str(kernel.parent), 'CCL_IMAGE_INVENTORY': str(output / 'image.json')}
    expression = '(progn (ccl-image-inventory::inspect-image (ccl:getenv "CCL_IMAGE_INVENTORY")) (ccl:quit))'
    argv = [str(kernel), '--image-name', str(image), '--no-init', '--batch',
            '--load', str(observer), '--load', str(inspector), '--eval', expression]
    record = {'version': 1, 'status': 'RUNNING', 'command': argv, 'environment': env,
              'input_sha256': identities, 'clean_baseline_record': str(pinned_clean),
              'clean_baseline_record_sha256': digest(pinned_clean)}
    save(output / 'run.json', record)
    try:
        with (output / 'native.log').open('wb') as log:
            child = subprocess.run(argv, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        if child.returncode or 'IMAGE-INVENTORY functions=' not in (output / 'native.log').read_text():
            raise ValueError('native inspection failed; see native.log')
        native = json.loads((output / 'image.json').read_text())
        observed = json.loads(graph.read_text()); seeds = json.loads(seed_path.read_text())
        result, summary = build(native, observed, seeds)
        check_coverage(result, native, observed, seeds)
        save(output / 'candidates.json', result)
        checks = controls(native, observed, seeds); save(output / 'controls.json', checks)
        summary['controls_rejected'] = len(checks['controls'])
        save(output / 'summary.json', summary)
        record['status'] = 'PREPARED_FOR_REVIEW'
        record['artifacts'] = [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)}
                               for p in sorted(output.iterdir()) if p.name != 'run.json']
        return summary
    except BaseException as exc:
        record.update(status='FAIL', error=str(exc)); raise
    finally:
        save(output / 'run.json', record)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel', 'image', 'graph', 'output'): p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(run(*(getattr(a, name).resolve() for name in ('kernel', 'image', 'graph', 'output'))), indent=2))
