"""Attribute noncensus V8 samples using admitted function byte ranges.

Arguments: PROFILE BOOT_CODE_SET RUNTIME_ARCHIVE OUTPUT. Function index alone
is insufficient across modules: the sampled byte offset must also match.
Counts are body/helper self samples, never an estimate of removable overhead.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys


def summarize(profile, inventories):
    ranges = {}
    for tier, archive in inventories:
        for row in archive['helper_bodies']:
            key = row['index'], row['start']
            assert key not in ranges
            ranges[key] = tier, 'helper', row['name'], None
        units = {u['name']: u for u in archive['units']}
        for function, entry in zip(archive['functions'], archive['entries']):
            for role in ('entry', 'tail_entry'):
                key = entry[role]['index'], entry[role]['start']
                assert key not in ranges
                ranges[key] = tier, role, function['source_name'], units[function['unit']].get('file', 'boot0')
    nodes = {n['id']: n for n in profile['nodes']}
    counts = Counter(profile['samples'])
    attributed = Counter()
    for node_id, count in counts.items():
        frame = nodes[node_id]['callFrame']
        match = re.fullmatch(r'wasm-function\[(\d+)\]', frame['functionName'])
        binding = ranges.get((int(match[1]), frame['columnNumber'])) if match else None
        key = binding or ('other', frame['url'], frame['functionName'], None)
        attributed[key] += count
    return dict(samples=sum(counts.values()), rows=[dict(tier=k[0], role=k[1], name=k[2], file=k[3], samples=v)
                for k, v in attributed.most_common()],
                scope='Noncensus statistical self samples, including host/admission. '
                      'Function indices AND body starts bind archive attribution. '
                      'Body self time does not isolate resolution, guard or frame cost.')


if __name__ == '__main__':
    profile, boot, runtime, output = map(Path, sys.argv[1:])
    inventories = [('core' if str(runtime) == '-' else 'boot', json.loads(boot.read_text())['archive'])]
    if str(runtime) != '-':
        inventories.append(('runtime', json.loads(runtime.read_text())))
    result = summarize(json.loads(profile.read_text()), inventories)
    result['inputs'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (profile, boot, runtime) if str(p) != '-'}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(samples=result['samples'], top=result['rows'][:10])))
