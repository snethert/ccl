"""Build and check the wasm32 layout schema v1 from derived rows and the disposition ledger."""
import hashlib
import json
from pathlib import Path
from derive import derive, c_constants

SCHEMA_NAME = 'wasm32-layout'
SCHEMA_VERSION = 1
VOCABULARY = ('inherited', 'replaced', 'unsupported', 'deferred', 'reserved')
# The only Lisp/C disagreement in U1: the C macro reuses the immheader form for the node bound.
KNOWN_C_DISAGREEMENTS = {'max-non-array-node-subtag': {'lisp': 146, 'c': 159, 'note': 'x86-constants32.h line 140 spells the node bound as ((19<<ntagbits)|fulltag_immheader); the Lisp definition ((18<<3)|fulltag-nodeheader) governs the schema. The C name is unused by the kernel sources.'}}
LISP_SOURCE = 'compiler/X86/X8632/x8632-arch.lisp'
C_SOURCE = 'lisp-kernel/x86-constants32.h'


def sha(data): return hashlib.sha256(data).hexdigest()


def c_name(name): return name.replace('-', '_').replace('.', '_')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def entry(ledger, group, name):
    value = ledger.get(group, {}).get(name)
    require(isinstance(value, list) and len(value) >= 2 and value[0] in VOCABULARY and isinstance(value[1], str) and value[1], 'LEDGER ' + group + ' ' + name)
    return value


def build(lisp_text, c_text, ledger, layout_subset, source_revision, lisp_sha, c_sha):
    table = derive(lisp_text)
    values = table['values']
    schema = {'schema': SCHEMA_NAME, 'version': SCHEMA_VERSION, 'source_revision': source_revision,
              'sources': {LISP_SOURCE: lisp_sha, C_SOURCE: c_sha}, 'ledger_sha256': sha(json.dumps(ledger, sort_keys=True).encode()),
              'coordinates': 'raw_offset counts bytes from the object base; tagged_displacement is the immediate added to the tagged pointer (negative displacements need explicit address adjustment on wasm32, positive ones can use the memory instruction offset)',
              'vocabulary': ledger['vocabulary']}
    schema['word_bytes'] = values['word-size-in-bytes']; schema['endianness'] = 'little'; schema['object_alignment'] = values['dnode-size']
    constants = []
    for row in table['order']:
        if row['kind'] != 'constant':
            continue
        d = entry(ledger, 'constants', row['name'])
        value = row['value']
        if isinstance(value, tuple):
            value = {'byte_size': value[1], 'byte_position': value[2]}
        constants.append({'name': row['name'], 'value': value, 'disposition': d[0], 'target': d[1], 'note': d[2] if len(d) > 2 else ''})
    schema['constants'] = constants
    schema['subtags'] = [{**s, 'disposition': entry(ledger, 'subtags', s['name'])[0], 'target': entry(ledger, 'subtags', s['name'])[1], 'note': entry(ledger, 'subtags', s['name'])[2]} for s in table['subtags']]
    schema['headers'] = [{**h, 'disposition': entry(ledger, 'headers', h['name'])[0], 'target': entry(ledger, 'headers', h['name'])[1]} for h in table['headers']]
    objects = []
    for o in table['objects']:
        led = ledger.get('objects', {}).get(o['name']); require(isinstance(led, dict) and 'disposition' in led and 'cells' in led, 'LEDGER objects ' + o['name'])
        d = led['disposition']; require(d[0] in VOCABULARY, 'LEDGER objects ' + o['name'])
        cells = []
        for c in o['layout']['cells']:
            cd = led['cells'].get(c['cell']); require(isinstance(cd, list) and len(cd) >= 3 and cd[0] in VOCABULARY, 'LEDGER objects ' + o['name'] + '.' + c['cell'])
            cells.append({'name': c['cell'], 'index': c['index'], 'raw_offset': c['index'] * 4, 'tagged_displacement': c['offset'], 'disposition': cd[0], 'representation': cd[1], 'gc': cd[2], 'note': cd[3] if len(cd) > 3 else ''})
        objects.append({'name': o['name'], 'tag': o['tag'], 'tag_value': o['tag_value'], 'size_bytes': o['layout']['size'], 'alignment': values['dnode-size'], 'has_header': o['header'],
                        'element_count': o.get('element_count'), 'disposition': d[0], 'target': d[1], 'note': d[2] if len(d) > 2 else '', 'cells': cells})
    schema['objects'] = objects
    layouts = []
    for l in table['layouts']:
        led = ledger.get('layouts', {}).get(l['name']); require(isinstance(led, dict), 'LEDGER layouts ' + l['name'])
        d = led['disposition']; require(d[0] in VOCABULARY, 'LEDGER layouts ' + l['name'])
        cells = []
        for c in l['cells']:
            cd = led['cells'].get(c['cell']); require(isinstance(cd, list) and len(cd) >= 2 and cd[0] in VOCABULARY, 'LEDGER layouts ' + l['name'] + '.' + c['cell'])
            cells.append({'name': c['cell'], 'index': c['index'], 'offset': c['offset'], 'disposition': cd[0], 'target': cd[1], 'note': cd[2] if len(cd) > 2 else ''})
        layouts.append({'name': l['name'], 'origin': l['origin'], 'size_bytes': l['size'], 'disposition': d[0], 'target': d[1], 'note': d[2] if len(d) > 2 else '', 'cells': cells})
    schema['layouts'] = layouts
    enums = []
    for e in table['enums']:
        key = (e['prefix'] or 'registers').lower(); d = entry(ledger, 'enums', key)
        enums.append({'group': key, 'start': e['start'], 'step': e['step'], 'count': len(e['names']), 'disposition': d[0], 'target': d[1], 'note': d[2] if len(d) > 2 else '', 'names': e['names']})
    schema['enums'] = enums
    d = ledger.get('subprims'); require(isinstance(d, list) and d[0] in VOCABULARY, 'LEDGER subprims')
    schema['subprims'] = {'base': values['x8632-subprims-base'], 'shift': 2, 'count': len(table['subprims']), 'disposition': d[0], 'target': d[1], 'note': d[2] if len(d) > 2 else '', 'names': table['subprims']}
    # Lisp/C agreement over every integer constant the header also defines.
    c = c_constants(c_text)
    agree, disagree = [], {}
    for name, value in values.items():
        if isinstance(value, int) and c_name(name) in c:
            if c[c_name(name)] == value:
                agree.append(name)
            else:
                disagree[name] = {'lisp': value, 'c': c[c_name(name)]}
    schema['c_agreement'] = {'header': C_SOURCE, 'compared': len(agree) + len(disagree), 'agree': len(agree), 'disagreements': {k: {**v, 'note': KNOWN_C_DISAGREEMENTS.get(k, {}).get('note', 'UNEXPLAINED')} for k, v in sorted(disagree.items())}}
    # The initial contracts/layout.json subset must agree with the derived rows.
    cons = next(o for o in objects if o['name'] == 'cons'); cells = {c['name']: c for c in cons['cells']}
    subset = {'fixnum_shift': values['fixnumshift'], 'fixnum_min': values['target-most-negative-fixnum'], 'fixnum_max': values['target-most-positive-fixnum'],
              'fulltags': {'even_fixnum': values['fulltag-even-fixnum'], 'cons': values['fulltag-cons'], 'nodeheader': values['fulltag-nodeheader'], 'imm': values['fulltag-imm'], 'odd_fixnum': values['fulltag-odd-fixnum'], 'reserved_tra': values['fulltag-tra'], 'misc': values['fulltag-misc'], 'immheader': values['fulltag-immheader']},
              'cons': {'size_bytes': cons['size_bytes'], 'alignment': cons['alignment'], 'tag': cons['tag_value'], 'cdr_raw_offset': cells['cdr']['raw_offset'], 'car_raw_offset': cells['car']['raw_offset'], 'cdr_tagged_displacement': cells['cdr']['tagged_displacement'], 'car_tagged_displacement': cells['car']['tagged_displacement']},
              'word_bytes': values['word-size-in-bytes'], 'object_alignment': values['dnode-size']}
    schema['initial_subset'] = {'path': 'doc/WASM/contracts/layout.json', 'derived': subset, 'declared': {k: layout_subset.get(k) for k in subset}}
    schema['canonical_objects'] = {'nil': values['canonical-nil-value'], 't': values['canonical-t-value'], 't_offset': values['t-offset'], 'nil_symbol_offset': values['nilsym-offset'], 'note': 'provisional schema rows; the loader supplies the objects and Stage 1 confirms them through generated code'}
    count = lambda rows: {v: sum(1 for r in rows if r['disposition'] == v) for v in VOCABULARY}
    cell_rows = [c for o in objects for c in o['cells']] + [c for l in layouts for c in l['cells']]
    schema['counts'] = {'constants': count(constants), 'subtags': count(schema['subtags']), 'headers': count(schema['headers']), 'objects': count(objects), 'object_and_layout_cells': count(cell_rows),
                        'layouts': count(layouts), 'enums': count(enums), 'rows_total': len(constants) + len(schema['subtags']) + len(schema['headers']) + len(objects) + len(layouts) + len(cell_rows) + len(enums) + 1}
    return schema


def check(schema, expected_sources=None):
    """Structural and provenance checks on a built or committed schema; raises the first failure."""
    require(schema.get('schema') == SCHEMA_NAME and schema.get('version') == SCHEMA_VERSION, 'SCHEMA identity')
    if expected_sources is not None:
        require(schema.get('sources') == expected_sources, 'SOURCE_PIN schema sources')
    rows = list(schema['constants']) + list(schema['subtags']) + list(schema['headers']) + list(schema['objects']) + list(schema['layouts']) + list(schema['enums']) + [schema['subprims']]
    for o in schema['objects']:
        rows.extend(o['cells'])
    for l in schema['layouts']:
        rows.extend(l['cells'])
    for r in rows:
        require(r.get('disposition') in VOCABULARY and isinstance(r.get('target', r.get('representation')), str), 'LEDGER row ' + str(r.get('name', r.get('group'))))
    require(len(rows) == schema['counts']['rows_total'], 'COUNTS rows')
    fulltags = {r['name']: r['value'] for r in schema['constants'] if r['name'].startswith('fulltag-')}
    require(fulltags == {'fulltag-even-fixnum': 0, 'fulltag-cons': 1, 'fulltag-nodeheader': 2, 'fulltag-imm': 3, 'fulltag-odd-fixnum': 4, 'fulltag-tra': 5, 'fulltag-misc': 6, 'fulltag-immheader': 7}, 'D1 fulltags')
    cons = next(o for o in schema['objects'] if o['name'] == 'cons')
    require([c['name'] for c in cons['cells']] == ['cdr', 'car'] and cons['cells'][0]['raw_offset'] == 0 and cons['cells'][1]['raw_offset'] == 4 and cons['cells'][0]['tagged_displacement'] == -1 and cons['cells'][1]['tagged_displacement'] == 3, 'D1 cons')
    for s in schema['subtags']:
        require(s['value'] == (s['tag_value'] | (s['index'] << 3)) and s['value'] >= 3, 'SUBTAG ' + s['name'])
    require(len({s['value'] for s in schema['subtags']}) == len(schema['subtags']), 'SUBTAG uniqueness')
    disagreements = schema['c_agreement']['disagreements']
    require(set(disagreements) == set(KNOWN_C_DISAGREEMENTS) and all(disagreements[k]['lisp'] == KNOWN_C_DISAGREEMENTS[k]['lisp'] and disagreements[k]['c'] == KNOWN_C_DISAGREEMENTS[k]['c'] for k in disagreements), 'C_AGREEMENT ' + ','.join(sorted(disagreements)))
    require(schema['c_agreement']['agree'] >= 40, 'C_AGREEMENT coverage')
    subset = schema['initial_subset']
    require(subset['derived'] == subset['declared'], 'SUBSET contracts/layout.json')
    tcr = next(l for l in schema['layouts'] if l['name'] == 'tcr')
    require(len(tcr['cells']) == 61 and all(c['disposition'] != 'inherited' for c in tcr['cells']), 'TCR ledger: native TCR cells are never inherited')
    return {'rows': len(rows), 'c_agree': schema['c_agreement']['agree'], 'disagreements': sorted(disagreements)}
