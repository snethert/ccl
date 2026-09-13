#!/usr/bin/env python3
"""Measure seed masking in an existing graph; never emit a narrowed closure."""
import argparse
from collections import Counter, defaultdict, deque
import gzip
import hashlib
import json
from pathlib import Path


def reachable(edges, seeds):
    pending = deque(seeds)
    seen = set(seeds)
    while pending:
        for target in edges.get(pending.popleft(), ()):
            if target not in seen:
                seen.add(target)
                pending.append(target)
    return seen


def analyze(graph):
    """Counterfactual deletion is a diagnosis, never a justified call bound."""
    modes = {
        'retained': lambda e: False,
        'without_two_membership_edges': lambda e: e['evidence'] in ('members/@clean-image', 'members/tools/asdf.lisp'),
        'without_all_original_membership_edges': lambda e: e['evidence'].startswith('members/'),
    }
    rows = []
    for name, omit in modes.items():
        outgoing = defaultdict(set)
        removed = []
        for e in graph['edges']:
            if omit(e):
                removed.append({'from': e['from'], 'evidence': e['evidence'], 'target_count': len(e['targets'])})
            else:
                outgoing[e['from']].update(e['targets'])
        full = reachable(outgoing, graph['seeds'])
        omissions = []
        for seed in graph['seeds']:
            reduced = reachable(outgoing, [s for s in graph['seeds'] if s != seed])
            omissions.append({'seed': seed, 'lost_reachable_nodes': len(full - reduced),
                              'seed_still_reachable': seed in reduced})
        rows.append({'mode': name, 'reachable_nodes': len(full), 'removed_edges': removed,
                     'seed_omissions': omissions})
    return {'version': 1, 'status': 'DIAGNOSTIC_ONLY', 'graph_nodes': len(graph['nodes']),
            'graph_edges': len(graph['edges']), 'seed_review': graph['seed_review'],
            'seed_count': len(graph['seeds']), 'scenarios': rows,
            'remaining_membership_families': dict(Counter(e['evidence'].split('/')[0] for e in graph['edges']
                if 'member' in e['evidence'] and not e['evidence'].startswith('members/'))),
            'interpretation': 'These are the retained revision-1 graph seeds, not IDs from the new image. '
                'Counterfactual edge removals diagnose masking only; they are not sound replacements and '
                'do not establish static coverage, complete indirect-call bounds, or LL15-c omission qualification. '
                'The original graph and all its candidates remain unchanged.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--graph', type=Path, required=True)
    p.add_argument('--graph-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('output must be new')
    with a.graph.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != a.graph_sha256:
        raise ValueError('graph differs from retained materialization')
    with gzip.open(a.graph, 'rt') as stream:
        result = analyze(json.load(stream))
    result['input'] = {'path': str(a.graph.resolve()), 'sha256': actual}
    result['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with a.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps([{k: row[k] for k in ('mode', 'reachable_nodes', 'seed_omissions')}
                      for row in result['scenarios']], indent=2))


if __name__ == '__main__':
    main()
