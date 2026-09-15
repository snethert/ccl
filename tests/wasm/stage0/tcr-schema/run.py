#!/usr/bin/env python3
"""Production TCR schema v1 (D5): explicit fields, widths, alignments, classifications and ownership, joined to the native cells and the executed fixtures."""
import argparse, copy, hashlib, json, platform, shutil, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[3]; DOCS = ROOT / 'doc/WASM'
ID = 'TCR-SCHEMA-R1'
SCOPE = ('Production TCR schema v1 under D5: 47 fields in nine D5 field groups with explicit offsets, widths, alignments, classification and '
         'ownership, joined to every replaced or deferred native TCR cell of the wasm32 layout schema and to every TCR field the accepted '
         'fixtures use, each fixture field mapped to one production field or declared fixture-private. Control execution over the committed '
         'contracts; no Wasm executed, no gate credit. The schema is the Stage 1 build target D5 owes; it does not claim executed proof.')
COMMITTED = DOCS / 'contracts/tcr.v1.json'; LAYOUT = DOCS / 'contracts/wasm32-layout.v1.json'; JOIN = DOCS / 'contracts/runtime-contracts.v1.json'
CLASSES = ('tagged-root', 'raw-address', 'bounded', 'atomic-state', 'code-identifier', 'raw-scalar'); OWNERS = ('thread', 'registry', 'collector', 'host')


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def save(p, x): p.write_text(json.dumps(x, indent=2, ensure_ascii=False) + '\n')
def canonical(x): return json.dumps(x, indent=2, ensure_ascii=False) + '\n'
def require(x, reason):
    if not x: raise ValueError(reason)


def sources():
    return [HERE / n for n in ('run.py', 'tcr.json')] + [LAYOUT, JOIN, COMMITTED]


def build(source, layout, join):
    fields = source['fields']; names = {f['name'] for f in fields}
    require(len(names) == len(fields), 'FIELD duplicate name')
    native_cells = next(l for l in layout['layouts'] if l['name'] == 'tcr')['cells']
    origins = source['native_origins']
    for c in native_cells:
        if c['disposition'] in ('replaced', 'deferred'):
            m = origins.get(c['name']); require(m is not None, 'NATIVE unmapped ' + c['name'])
            require(m == 'deferred' or (isinstance(m, list) and m and all(x in names for x in m)), 'NATIVE target ' + c['name'])
        else:
            require(c['name'] not in origins, 'NATIVE mapped unsupported cell ' + c['name'])
    fixture_fields = join['tcr']['fields']; fmap = source['fixture_map']
    for name in fixture_fields:
        m = fmap.get(name); require(m is not None, 'FIXTURE unmapped ' + name)
        if isinstance(m, dict):
            require(m.get('production') is None and m.get('reason'), 'FIXTURE private ' + name)
        else:
            require(isinstance(m, list) and m and all(x in names for x in m), 'FIXTURE target ' + name)
    require(set(fmap) == set(fixture_fields), 'FIXTURE extra entries')
    origin_of = {}
    for cell, targets in origins.items():
        if isinstance(targets, list):
            for t in targets: origin_of.setdefault(t, []).append(cell)
    witness_of = {}
    for fx, targets in fmap.items():
        if isinstance(targets, list):
            for t in targets: witness_of.setdefault(t, []).append({'field': fx, 'tests': fixture_fields[fx]['tests']})
    records = []
    for f in fields:
        records.append({**f, 'native_origins': sorted(origin_of.get(f['name'], [])), 'fixture_witnesses': witness_of.get(f['name'], [])})
    contract = dict(schema='tcr', version=1, size_bytes=source['size_bytes'], alignment=source['alignment'], reserved=source['reserved'], classifications=source['classifications'], owners=source['owners'],
                    groups=[{'group': g, 'd5': d, 'fields': [f['name'] for f in fields if f['group'] == g]} for g, d in source['groups'].items()],
                    fields=records, native_origins=origins, fixture_map=fmap,
                    inputs={'layout': {'path': 'doc/WASM/contracts/wasm32-layout.v1.json', 'sha256': sha(LAYOUT)}, 'join': {'path': 'doc/WASM/contracts/runtime-contracts.v1.json', 'sha256': sha(JOIN)}},
                    counts=dict(fields=len(fields), by_class={c: sum(1 for f in fields if f['classification'] == c) for c in CLASSES}, by_owner={o: sum(1 for f in fields if f['owner'] == o) for o in OWNERS},
                                native_cells_mapped=sum(1 for c in native_cells if isinstance(origins.get(c['name']), list)), native_cells_deferred=sum(1 for c in native_cells if origins.get(c['name']) == 'deferred'),
                                native_cells_unsupported=sum(1 for c in native_cells if c['disposition'] == 'unsupported'), fixture_fields_mapped=sum(1 for v in fmap.values() if isinstance(v, list)),
                                fixture_fields_private=sum(1 for v in fmap.values() if isinstance(v, dict)), fields_without_native_origin=sum(1 for r in records if not r['native_origins'])),
                    rules=['every field is assigned exactly once; the fixtures\' aliased extension offsets are resolved by this schema',
                           'atomic-state fields are read and written only with sequentially consistent atomics; unrelated bits are preserved',
                           'raw-address fields are rederived after movement where they point into movable storage; none is a tagged value',
                           'the multiple-value descriptor points at the owned VSP result region; no separate backing buffer exists',
                           'the host never writes a TCR field; it writes only inside owned request descriptors',
                           'tcr_index and a symbol binding index are different namespaces'])
    return contract


def check(contract):
    fields = contract['fields']; size = contract['size_bytes']
    require(size % contract['alignment'] == 0 and contract['alignment'] >= 16, 'SIZE')
    spans = []
    for f in fields:
        require(f['classification'] in CLASSES and f['owner'] in OWNERS, 'FIELD vocabulary ' + f['name'])
        require(f['width'] in (4, 8) and f['offset'] % f['alignment'] == 0 and f['alignment'] >= f['width'], 'FIELD alignment ' + f['name'])
        require(f['classification'] != 'atomic-state' or f['offset'] % 4 == 0, 'FIELD atomic alignment ' + f['name'])
        require(f['offset'] + f['width'] <= contract['reserved'][0], 'FIELD extent ' + f['name'])
        spans.append((f['offset'], f['offset'] + f['width'], f['name']))
    spans.sort()
    for (a0, a1, an), (b0, b1, bn) in zip(spans, spans[1:]):
        require(a1 <= b0, 'FIELD overlap ' + an + '/' + bn)
    require(contract['reserved'][1] == size, 'RESERVED tail')
    groups = {g['group']: g['fields'] for g in contract['groups']}
    require(len(groups) == 9 and all(groups[g] for g in groups), 'GROUP missing or empty')
    require({f['name'] for f in fields} == {n for fs in groups.values() for n in fs}, 'GROUP coverage')
    tagged = [f for f in fields if f['classification'] == 'tagged-root']
    require(all(f['name'] == 'next_method_context' for f in tagged), 'TAGGED roots limited to declared slots')
    require(all(w['tests'] for r in fields for w in r['fixture_witnesses']), 'WITNESS tests')
    return dict(fields=len(fields), witnessed=sum(1 for r in fields if r['fixture_witnesses']), native_mapped=contract['counts']['native_cells_mapped'])


def exercise(out):
    require(platform.system() == 'Darwin', 'MACOS_REFERENCE'); out.mkdir(parents=True, exist_ok=False)
    source = read(HERE / 'tcr.json'); layout = read(LAYOUT); join = read(JOIN)
    contract = build(source, layout, join); summary = check(contract)
    save(out / 'tcr.v1.json', contract)
    require(canonical(contract) == COMMITTED.read_text(), 'COMMITTED differs from the regeneration')
    q = out / 'quarantine'; q.mkdir(); refusals = []
    def control(name, fn, expected):
        try: fn()
        except ValueError as e: reason = str(e)
        else: raise ValueError('CONTROL_ESCAPED ' + name)
        require(reason.startswith(expected), 'CONTROL_REASON ' + name + ': ' + reason)
        refusals.append(dict(control=name, refused=reason)); save(q / (name + '.json'), dict(control=name, refused=reason))
    def mutated(fn):
        s = copy.deepcopy(source); fn(s); return s
    control('field-overlap', lambda: check(build(mutated(lambda s: s['fields'][1].update(offset=0)), layout, join)), 'FIELD overlap')
    control('atomic-misaligned', lambda: check(build(mutated(lambda s: next(f for f in s['fields'] if f['name'] == 'pending').update(offset=38, alignment=2)), layout, join)), 'FIELD alignment pending')
    control('classification-outside', lambda: check(build(mutated(lambda s: s['fields'][0].update(classification='fixnum')), layout, join)), 'FIELD vocabulary tcr_index')
    control('native-cell-unmapped', lambda: build(mutated(lambda s: s['native_origins'].pop('save-vsp')), layout, join), 'NATIVE unmapped save-vsp')
    control('native-target-missing', lambda: build(mutated(lambda s: s['native_origins'].update({'save-vsp': ['vsp_register']})), layout, join), 'NATIVE target save-vsp')
    control('fixture-field-unmapped', lambda: build(mutated(lambda s: s['fixture_map'].pop('active_request')), layout, join), 'FIXTURE unmapped active_request')
    control('group-dropped', lambda: check(build(mutated(lambda s: s['groups'].pop('mailbox')), layout, join)), 'GROUP')
    control('tagged-root-added', lambda: check(build(mutated(lambda s: s['fields'][0].update(classification='tagged-root')), layout, join)), 'TAGGED roots')
    save(out / 'controls.json', refusals)
    observations = dict(summary=summary, counts=contract['counts'], controls=[r['control'] for r in refusals])
    save(out / 'observations.json', observations)
    save(out / 'summary.json', dict(version=1, id=ID, status='PASS', scope=SCOPE, review_disposition='NOT_REVIEWED', **observations))
    return observations


def run(out):
    require(ROOT not in out.parents and out != ROOT and not out.exists(), 'FRESH_OUTPUT_OUTSIDE_CHECKOUT')
    snapshots = {str(p.relative_to(ROOT)): p.read_bytes() for p in sources()}
    source_sha = {str(p.relative_to(ROOT)): sha(p) for p in sources()}
    record = dict(version=1, status='FAIL', command=[sys.executable, *sys.argv], timestamp=datetime.now(timezone.utc).isoformat(), source_sha256=source_sha)
    try:
        exercise(out); (out / 'source').mkdir()
        for p in sources(): (out / 'source' / p.name).write_bytes(p.read_bytes())
        require(record['source_sha256'] == {str(p.relative_to(ROOT)): sha(p) for p in sources()}, 'SOURCE_CHANGED')
        record.update(status='PASS'); print('PASS: TCR schema v1, 47 fields, eight controls refused. Review pending; no gate credit.')
    except BaseException as e:
        record['error'] = type(e).__name__ + ': ' + str(e); raise
    finally:
        if out.exists():
            save(out / 'run.json', record); (out / 'source').mkdir(exist_ok=True)
            for name, data in snapshots.items(): (out / 'source' / Path(name).name).write_bytes(data)


def verify(packet):
    record = read(packet / 'run.json'); require(record['status'] == 'PASS', 'RUN_STATUS')
    for name, h in record['source_sha256'].items(): require(sha(ROOT / name) == h, 'SOURCE_PIN ' + name)
    temp = Path(tempfile.mkdtemp(prefix='ccl-tcr-schema-verify-'))
    try:
        fresh = temp / 'replay'; observations = exercise(fresh)
        require(observations == read(packet / 'observations.json'), 'REPLAY_OBSERVATIONS')
        names = [p.relative_to(fresh) for p in fresh.rglob('*') if p.is_file()]
        for n in names: require((fresh / n).read_bytes() == (packet / n).read_bytes(), 'REPLAY_BYTES ' + str(n))
    except BaseException as e:
        save(temp / 'failure.json', dict(status='FAIL', packet=str(packet), error=str(e))); print('Original verification failure retained at ' + str(temp), file=sys.stderr); raise
    else:
        shutil.rmtree(temp)
    print('PASS: schema regenerated; ' + str(len(names)) + ' identical deterministic files and pins.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output', type=Path); g.add_argument('--verify', type=Path); g.add_argument('--generate', action='store_true'); a = p.parse_args()
    if a.generate:
        contract = build(read(HERE / 'tcr.json'), read(LAYOUT), read(JOIN)); print(check(contract)); COMMITTED.write_text(canonical(contract)); print('generated', COMMITTED)
    elif a.verify: verify(a.verify.resolve())
    else: run(a.output.resolve())
