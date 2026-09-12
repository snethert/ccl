#!/usr/bin/env python3
"""Reconcile a retained native startup trace without claiming complete census closure."""
import argparse
import collections
import json
from pathlib import Path
import re
import shutil
from reversible import digest, save

LINE = re.compile(r'^\d\d:\d\d:\d\d\.\d+\s+(\S+)\s+(.*?)\s+(\d+\.\d+)\s+(?:W\s+)?(.+)\.(\d+)$')


def reconcile(root):
    report = json.loads((root / 'trace.json').read_text())
    if report['version'] != 2 or report['status'] != 'CAPTURED_REQUIRES_RECONCILIATION':
        raise ValueError('requires a captured v2 trace with pre/post-exec coverage')
    for artifact in report['artifacts']:
        path = (root / artifact['path']).resolve()
        if not path.is_relative_to(root.resolve()) or digest(path) != artifact['sha256']:
            raise ValueError('trace artifact identity mismatch')
    for name, expected in report['inputs_sha256'].items():
        # Original source may evolve; its exact executed copy is retained.
        path = root / 'trace-startup.py' if name.endswith('/trace-startup.py') else Path(name)
        if digest(path) != expected: raise ValueError('trace input identity mismatch')
    client = report['client_command']; executable = Path(client[0]); image = client[client.index('--image-name') + 1]
    native_marker = str(root / 'native-control-read.txt'); launcher_marker = str(root / 'trace-control-read.txt')
    ancestors = {str(p) for name in [image, str(executable), native_marker] for p in Path(name).parents}
    rows = []; unparsed = []; background = 0
    for number, line in enumerate((root / 'fs_usage.log').read_text().splitlines(), 1):
        match = LINE.match(line)
        if not match:
            unparsed.append({'line': number, 'text': line}); continue
        op, body, seconds, process, thread = match.groups()
        if process not in [executable.name, 'Python']:
            background += 1; continue
        found = re.search(r'(?:\[-?\d+\])?/.*', body)
        path = found[0].rstrip() if found else None
        error = re.search(r'\[\s+(\d+)\]', body)
        if process == 'Python': category = 'launcher-coverage-control'
        elif path == image: category = 'pinned-clean-image'
        elif path == str(executable): category = 'byte-identical-kernel-copy'
        elif path == native_marker: category = 'post-startup-coverage-control'
        elif path == str(root): category = 'executable-directory-query'
        elif path and path.endswith('/Info.plist') and path.startswith(str(root)):
            category = 'optional-executable-bundle-metadata'
        elif path and path.startswith('/dev/'): category = 'host-device'
        elif path and path.startswith(('/usr/lib/', '/System/', '[-2]//Library/Preferences/')):
            category = 'host-loader-or-service-path'
        elif path in ancestors and op in ['getattrlist', 'stat64', 'lstat64']:
            category = 'input-ancestor-metadata'
        elif path and error and op in ['access', 'stat64', 'lstat64']:
            category = 'failed-existence-probe'
        elif path: category = 'unresolved-path-context'
        else: category = 'descriptor-or-pathless-operation'
        rows.append({'line': number, 'operator': op, 'details': body, 'path': path,
                     'errno': int(error[1]) if error else None, 'process': process, 'thread': int(thread),
                     'classification': category})
    def opened(path, process):
        return any(r['path'] == path and r['operator'] in ['open', 'openat'] and r['errno'] is None
                   and 'F=' in r['details'] and r['process'] == process for r in rows)
    checks = {'image_open': opened(image, executable.name),
              'native_control_open': opened(native_marker, executable.name),
              'launcher_control_open': opened(launcher_marker, 'Python'),
              'matching_pid': report['native_pid'] == report['pid'],
              'clean_exit': report['client_exit_code'] == report['tracer_exit_code'] == 0,
              'no_reported_loss': not report['event_loss_reported'], 'all_trace_lines_parsed': not unparsed}
    if not all(checks.values()): raise ValueError('trace coverage/reconciliation failed: ' + repr(checks))
    unresolved = [r for r in rows if r['classification'] == 'unresolved-path-context' or
                  (r['operator'] in ['open', 'openat'] and r['path'] is None)]
    lisp_reads = [r for r in rows if r['path'] and r['path'].endswith(('.lisp', '.dx64fsl', '.image'))]
    return {'version': 1, 'status': 'CAPTURE_VERIFIED_PARTIAL_RECONCILIATION', 'census_acceptance': 'BLOCKED',
            'trace_report_sha256': digest(root / 'trace.json'), 'checks': checks,
            'scope': 'One --no-init batch startup from the clean r5 image, with a byte-identical uniquely named kernel. File activity only; not cold disk caches, a rebuilt image, complete bootstrap loading, or LL15 closure.',
            'internal_observation_relationship': 'The image is the clean baseline, not the instrumented startup image. The separate r5 native run establishes unchanged evaluated operator/callback inventories and R6 output comparisons; this trace does not establish initializer prerequisite semantics.',
            'background_disk_events_excluded': background,
            'classification_counts': dict(collections.Counter(r['classification'] for r in rows)),
            'lisp_file_operations': lisp_reads, 'unresolved_path_contexts': unresolved,
            'rows': rows, 'unparsed_lines': unparsed,
            'remaining': ['Resolve anonymous/relative loader pathname contexts',
                          'Join semantic startup and loader prerequisites into the qualified census',
                          'Independent review; no new acceptance']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trace', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
    if any(a.output.iterdir()): p.error('output must be new and empty')
    shutil.copyfile(__file__, a.output / 'reconcile-trace.py')
    result = reconcile(a.trace.resolve()); save(a.output / 'reconciliation.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ['rows', 'lisp_file_operations']}, indent=2))
