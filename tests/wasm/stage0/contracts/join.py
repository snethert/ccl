"""Join the runtime contracts to the executed, accepted Stage 0 fixtures.

Reads the accepted aggregate named by the current ledger, verifies each cited
artifact's hash inside the evidence repository, and checks that the fixtures
agree with one another and with the written contracts on frames, roots, TCR
fields, allocation/store protocols, the C boundary and link-derived ownership.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

JOIN_NAME = 'runtime-contracts'
JOIN_VERSION = 1
PREREQUISITES = ['S0-LL04-a', 'S0-LL13-c', 'S0-LL19-b', 'S0-LL23-b']
SUPPORTING = ['S0-LL20-a', 'S0-LL20-b', 'S0-LL20-c', 'S0-LL05-a', 'S0-LL07-a', 'S0-LL13-b', 'S0-LL21-a']


def sha(data): return hashlib.sha256(data).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def parse_frame_header(markdown):
    """Byte offsets of the logical frame header table in contracts/debug-frames.md."""
    header = {}
    for line in markdown.splitlines():
        m = re.match(r'\|\s*(\d+)\s*\|\s*(\w+)\s*\|', line)
        if m and m.group(2) not in ('Byte',):
            header[m.group(2)] = int(m.group(1))
    require(len(header) == 16, 'FRAME header table')
    return header


class Evidence:
    def __init__(self, evidence_root, aggregate_path, read=None, base=None):
        self.root = Path(evidence_root); self.read = read or (lambda p: Path(p).read_bytes())
        self.aggregate = json.loads(self.read(aggregate_path))
        self.base = Path(base) if base else Path(aggregate_path).parent; self.name = Path(aggregate_path).name
        require(self.base.resolve().is_relative_to(self.root.resolve()), 'AGGREGATE base outside the evidence repository')
        self.records = {(r['id'], r['variant']): r for r in self.aggregate['results']}

    def record(self, ident, variant=None):
        keys = [k for k in self.records if k[0] == ident and (variant is None or k[1] == variant)]
        require(keys, 'RECORD ' + ident)
        return self.records[keys[0]]

    def artifact(self, ident, suffix, variant=None):
        r = self.record(ident, variant)
        matches = [a for a in r['artifacts'] if a['path'].endswith(suffix)]
        require(matches, 'ARTIFACT ' + ident + ' ' + suffix)
        a = min(matches, key=lambda a: len(a['path']))
        data = self.read(self.base / a['path'])
        require(sha(data) == a['sha256'], 'ARTIFACT hash ' + a['path'])
        return a['path'], a['sha256'], json.loads(data)

    def cases(self, ident, variant=None):
        r = self.record(ident, variant)
        return sorted({a['path'].split('/')[-1][:-5] for a in r['artifacts'] if '/cases/' in a['path'] and a['path'].endswith('.json') and 'quarantine' not in a['path']})

    def accepted(self, ident):
        return all(r['review_disposition'] == 'ACCEPTED' for k, r in self.records.items() if k[0] == ident)


def ownership(evidence, node, fixture_dir):
    """Re-derive the boundary fixture's ownership map from its retained link metadata."""
    path, digest, retained = evidence.artifact('S0-LL13-c', 'memory-ownership.json')
    meta_path, meta_sha, _ = evidence.artifact('S0-LL13-c', 'linked-metadata.json')
    contract_path, contract_sha, contract = evidence.artifact('S0-LL13-c', 'source/contract.json')
    source_dir = evidence.base / Path(meta_path).parent / 'source'
    out = subprocess.run([node, str(Path(fixture_dir) / 'ownership.mjs'), str(source_dir), str(evidence.base / meta_path), str(evidence.base / contract_path)], capture_output=True, text=True, timeout=60)
    require(out.returncode == 0, 'OWNERSHIP derivation ' + out.stderr.strip()[:200])
    derived = json.loads(out.stdout)
    require(derived == retained, 'OWNERSHIP mismatch with retained map')
    regions = retained['regions']
    for i, a in enumerate(regions):
        require(a['start'] < a['end'] and a['start'] % a['alignment'] == 0, 'OWNERSHIP region ' + a['name'])
        for b in regions[i + 1:]:
            require(a['end'] <= b['start'] or b['end'] <= a['start'], 'OWNERSHIP overlap ' + a['name'] + '/' + b['name'])
    return {'retained': {'path': path, 'sha256': digest}, 'link_metadata': {'path': meta_path, 'sha256': meta_sha}, 'contract': {'path': contract_path, 'sha256': contract_sha},
            'derivation': 'planMemory/validateMap from the retained source/runtime.mjs over the retained linked-metadata.json',
            'regions': [{'name': r['name'], 'start': r['start'], 'end': r['end'], 'alignment': r['alignment']} for r in regions],
            'workers': len(retained['workers']), 'reserved_table_slots': retained['tableReserved'], 'used_end': retained['usedEnd']}


def build(evidence, frames_markdown, node, fixture_dir, pending=None):
    join = {'join': JOIN_NAME, 'version': JOIN_VERSION, 'aggregate': {'name': evidence.name, 'records': len(evidence.records)},
            'prerequisites': {p: evidence.accepted(p) for p in PREREQUISITES}, 'supporting': {s: evidence.accepted(s) for s in SUPPORTING if any(k[0] == s for k in evidence.records)}}
    require(all(join['prerequisites'].values()), 'PREREQUISITES accepted')
    # Frames: the written header contract equals the executed fixture's header.
    header = parse_frame_header(frames_markdown)
    df_path, df_sha, df = evidence.artifact('S0-LL23-b', 'source/debug-frames/schema.json')
    dc_path, dc_sha, dc = evidence.artifact('S0-LL05-a', 'source/dynamic-call/schema.json', 'full:B')
    require(df['header'] == header, 'FRAME header fixture/contract')
    require(df['header_bytes'] == 64 == dc['header_bytes'], 'FRAME header bytes')
    join['frames'] = {'contract': 'doc/WASM/contracts/debug-frames.md v0.1', 'header': header, 'header_bytes': 64,
                      'evidence': [{'test': 'S0-LL23-b', 'artifact': df_path, 'sha256': df_sha, 'cases': evidence.cases('S0-LL23-b')},
                                   {'test': 'S0-LL05-a', 'variant': 'full:B', 'artifact': dc_path, 'sha256': dc_sha, 'frame_bytes': dc['frame_bytes'], 'cases': len(evidence.cases('S0-LL05-a', 'full:B'))}]}
    # Roots: previous at +0, count at +4, tagged slots from +8 in every fixture that publishes root records.
    rb_path, rb_sha, rb = evidence.artifact('S0-LL13-c', 'source/contract.json')
    ir_path, ir_sha, ir = evidence.artifact('S0-LL20-a', 'source/integrated-runtime/schema.json')
    require(rb['roots'] == {'bytes': 16, 'previous_raw_offset': 0, 'count_raw_offset': 4, 'tagged_slots': [8, 12]}, 'ROOTS boundary')
    require(ir['roots']['previous_raw_offset'] == 0 and ir['roots']['count_raw_offset'] == 4 and ir['roots']['tagged_values_offset'] == 8, 'ROOTS integrated')
    require(df['payload']['root_previous'] + 4 == df['payload']['root_count'], 'ROOTS frame payload')
    join['roots'] = {'record': {'previous_raw_offset': 0, 'count_raw_offset': 4, 'tagged_values_offset': 8}, 'rule': 'every physical slot has exactly one scanner; TCR-owned result regions carry count zero in their linked record (abi/dynamic-call.v0.md)',
                     'evidence': [{'test': 'S0-LL13-c', 'artifact': rb_path, 'sha256': rb_sha}, {'test': 'S0-LL20-a', 'artifact': ir_path, 'sha256': ir_sha, 'maximum_values': ir['roots']['maximum_values'], 'maximum_frames': ir['roots']['maximum_frames']},
                                  {'test': 'S0-LL23-b', 'artifact': df_path, 'sha256': df_sha, 'root_previous': df['payload']['root_previous'], 'root_count': df['payload']['root_count']}]}
    # TCR: one consistent 256-byte fixture layout across the accepted fixtures.
    fields = {}
    for test, source, table in (('S0-LL13-c', rb_path, rb['tcr_offsets']), ('S0-LL20-a', ir_path, ir['tcr']), ('S0-LL05-a', dc_path, dc['tcr']), ('S0-LL23-b', df_path, df['tcr'])):
        for name, offset in table.items():
            if name in fields and fields[name]['offset'] != offset:
                raise ValueError('TCR conflict ' + name + ' ' + test)
            fields.setdefault(name, {'offset': offset, 'tests': []})['tests'].append(test)
    by_offset = {}
    for name, f in fields.items():
        by_offset.setdefault(f['offset'], []).append(name)
    # Fixture-private fields may reuse an offset under another name only across
    # different fixtures; within one fixture every offset has one name.
    aliases = {}
    for offset, names in by_offset.items():
        if len(names) > 1:
            owners = [set(fields[n]['tests']) for n in names]
            require(all(a.isdisjoint(b) for i, a in enumerate(owners) for b in owners[i + 1:]), 'TCR aliased within one fixture ' + json.dumps(names))
            aliases[str(offset)] = {n: fields[n]['tests'] for n in names}
    require(max(f['offset'] for f in fields.values()) + 4 <= ir['tcr_bytes'], 'TCR extent')
    groups = {'identity_and_lifetime': ['id', 'lifetime', 'token', 'retire_serial', 'reclaimed'], 'atomic_state_and_pending': ['state', 'pending', 'admitted', 'stops', 'interrupts', 'reloads'],
              'allocation_area': ['allocation_checks'], 'explicit_stacks': ['vsp', 'tsp', 'csp', 'stack_base', 'stack_limit', 'stack_ok', 'observed_sp', 'frame_address', 'observed_c_frame'],
              'dynamic_bindings': ['binding_depth', 'binding_cookie'], 'multiple_values': ['nvalues', 'mv_base', 'mv_owner_top'], 'roots_and_frames': ['root_head', 'root_slot', 'old_root', 'observed_root', 'observed_raw', 'frame_head', 'frame_serial', 'frame_cursor', 'frame_base', 'frame_limit'],
              'handlers_and_cleanup': ['catch_reason', 'cleanup_effect', 'cleanup', 'boundary_cleanup', 'handler_cookie', 'post_exit_effect', 'nested', 'continuation', 'mode'], 'mailbox': ['requests', 'active_request', 'ready', 'release', 'progress'],
              'runtime_private': ['tcr_before', 'tcr_after', 'abi_state', 'reply_cursor', 'reply_limit', 'debug_policy']}
    grouped = {g: sorted(n for n in names if n in fields) for g, names in groups.items()}
    ungrouped = sorted(set(fields) - {n for names in groups.values() for n in names})
    require(not ungrouped, 'TCR ungrouped ' + ','.join(ungrouped))
    join['tcr'] = {'contract': 'decisions.md D5 TCR schema field groups', 'fixture_bytes': ir['tcr_bytes'], 'alignment': ir['tcr_alignment'], 'fields': {n: fields[n] for n in sorted(fields, key=lambda n: fields[n]['offset'])}, 'groups': grouped, 'fixture_private_aliases': aliases,
                   'finding': 'the accepted fixtures share one 256-byte TCR with a common prefix (root_head 24 through mv_owner_top 52) and fixture-private extension fields; later fixtures reuse extension offsets under their own names. The production D5 TCR schema must assign every field once; that assignment is Stage 1 work.',
                   'evidence': [{'test': t, 'artifact': p, 'sha256': s} for t, p, s in (('S0-LL13-c', rb_path, rb_sha), ('S0-LL20-a', ir_path, ir_sha), ('S0-LL05-a', dc_path, dc_sha), ('S0-LL23-b', df_path, df_sha))]}
    # Allocation and store protocols.
    cv_path, cv_sha, cv = evidence.artifact('S0-LL07-a', 'bundle-a/abi.json')
    ll20 = evidence.cases('S0-LL20-a'); dyn = evidence.cases('S0-LL05-a', 'full:B')
    require('independent-cons-layout-and-graphs' in dyn, 'ALLOCATION cons fixture')
    require(all(c in ll20 for c in ('competing-collectors', 'moving-install-6-values', 'child-handoff-final-rescan', 'parked-admission', 'stopped-admission')), 'ALLOCATION collector cases')
    join['allocation_and_store'] = {'collector': {'kind': 'bounded cons-only copying collector, non-generational', 'semispace_bytes': ir['semispace_bytes'], 'states': ir['states'], 'pending': ir['pending'], 'evidence': [{'test': 'S0-LL20-a', 'artifact': ir_path, 'sha256': ir_sha, 'cases': ll20}]},
                                   'cons_layout': {'rule': 'CDR word 0, CAR word 1, canonical NIL distinguished; independent unequal fixtures with a one-sided swap rejected', 'evidence': [{'test': 'S0-LL04-a', 'cases': ['independent-cons-layout-and-graphs']}]},
                                   'conversions': {'rule': 'signed fixnum, raw address, logical-ID and typed-slot conversions are distinct checked families', 'evidence': [{'test': 'S0-LL07-a', 'artifact': cv_path, 'sha256': cv_sha, 'families': sorted({e['family'] for e in cv['exports'].values()})}]},
                                   'store_lowering': {'rule': 'potentially relevant stores pass through a replaceable lowering; the initial collector needs no generational barrier (outline section 04)', 'evidence': 'D4 clarification of 14 September; no Stage 0 fixture claims a barrier'}}
    # C boundary.
    cb_path, cb_sha, cb = evidence.artifact('S0-LL19-b', 'C-boundary-cases.json')
    cc_path, cc_sha, cc = evidence.artifact('S0-LL13-c', 'concurrent-C-calls.json')
    require(len(cb) == 12 and sorted({c['count'] for c in cb}) == [0, 1, 6] and sorted({(c['mode'], c['restart']) for c in cb}) == [(0, 0), (1, 0), (1, 1), (1, 2)], 'C_BOUNDARY cases')
    require(all(c['afterSp'] == c['beforeSp'] and c['checkpointsAfter'] == c['checkpointsBefore'] for c in cb), 'C_BOUNDARY restoration')
    join['c_boundary'] = {'contract': rb['boundary'], 'results': rb['results'], 'restarts': rb['restarts'], 'unsupported': rb['unsupported'], 'allowed_function_imports': rb['allowed_function_imports'],
                          'evidence': [{'test': 'S0-LL19-b', 'artifact': cb_path, 'sha256': cb_sha, 'cases': len(cb)}, {'test': 'S0-LL13-c', 'artifact': cc_path, 'sha256': cc_sha, 'workers': len(cc['observations'])}]}
    # Link-derived ownership.
    join['ownership'] = ownership(evidence, node, fixture_dir)
    if pending:
        join['pending_review'] = pending
    return join


def check(join):
    require(join.get('join') == JOIN_NAME and join.get('version') == JOIN_VERSION, 'JOIN identity')
    require(all(join['prerequisites'].get(p) is True for p in PREREQUISITES), 'PREREQUISITES accepted')
    require(len(join['frames']['header']) == 16 and join['frames']['header']['reserved'] == 60, 'FRAME header')
    require(join['roots']['record'] == {'previous_raw_offset': 0, 'count_raw_offset': 4, 'tagged_values_offset': 8}, 'ROOTS record')
    offsets = [f['offset'] for f in join['tcr']['fields'].values()]
    require(max(offsets) + 4 <= join['tcr']['fixture_bytes'], 'TCR extent')
    for names in join['tcr']['fixture_private_aliases'].values():
        owners = list(names.values())
        require(all(set(a).isdisjoint(b) for i, a in enumerate(owners) for b in owners[i + 1:]), 'TCR aliased within one fixture')
    regions = join['ownership']['regions']
    for i, a in enumerate(regions):
        for b in regions[i + 1:]:
            require(a['end'] <= b['start'] or b['end'] <= a['start'], 'OWNERSHIP overlap ' + a['name'] + '/' + b['name'])
    require(join['c_boundary']['evidence'][0]['cases'] == 12, 'C_BOUNDARY cases')
    return {'tcr_fields': len(offsets), 'regions': len(regions), 'frame_fields': len(join['frames']['header'])}
