#!/usr/bin/env python3
"""Attempt every recorded compilation unit; incomplete units remain obligations."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
from run import digest, save, session


def survey(store, work, output, workers, mode, timeout):
    graph_path = store/'2026-09-12-dependencies-analysis-r3/graph.json'
    expected = '04ff3562d3c517831a873af7f0d394d78714cf053efc0915ac5263af53863ffe'
    if digest(graph_path) != expected: raise ValueError('NATIVE_SOURCE_INVENTORY_PIN')
    graph = json.loads(graph_path.read_text())
    names = sorted({s for n in graph['nodes'] for s in n['sources'] if s is not None})
    output.mkdir(parents=True, exist_ok=False)
    save(output/'inventory.json', dict(graph_sha256=expected, files=names,
         source_sha256={n:digest(work/'ccl'/n) for n in names}))
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(session, store, work, output/f'{i:03d}', work/'ccl'/n, mode, timeout): (i,n)
                   for i,n in enumerate(names)}
        for future in as_completed(futures):
            i,n = futures[future]
            row = dict(ordinal=i, file=n, status='SESSION_FAILED')
            try:
                future.result()
                p = json.loads(gzip.decompress((output/f'{i:03d}/capture.json.gz').read_bytes()))
                row.update(status=p['status'], captures=len(p['captures']), forms=len(p['forms']),
                           native_compilations=len(p.get('native_compilations',[])), eof_reached=p['eof_reached'],
                           problem=p['problem'])
            except Exception as e: row['error'] = str(e)
            rows.append(row)
            save(output/'summary.json', dict(status='COLLECTED' if len(rows)==len(names) else 'COLLECTING',
                                            qualified_census=False, completed=len(rows), expected=len(names),
                                            files=sorted(rows, key=lambda r:r['ordinal'])))
    print('SURVEY',len(rows),'units;',sum(r['status']=='CAPTURED' for r in rows),'complete front-end reads')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence-root', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--workers', type=int, default=3)
    p.add_argument('--timeout', type=int, default=600)
    p.add_argument('--mode', default='normal', choices=('normal', 'continue', 'native'))
    a = p.parse_args()
    survey(a.evidence_root.resolve(), a.work.resolve(), a.output.resolve(), a.workers, a.mode, a.timeout)
