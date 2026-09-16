"""Portable, content-bound queries over one retained native execution."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import zlib
from native import digest, save

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'build-flow'))
from flow import convert, functions, Graph

HEADER = re.compile(rb'^\{"(?:version":\d+,"sequence|sequence)":(\d+),"kind":"([^"]+)"')
BUILD_KINDS = {'snapshot', 'before-pass2', 'resident-binding', 'binding-installed', 'binding-removing', 'complete'}
REGISTRY_KINDS = {'function', 'registry-checkpoint', 'mutation-enter', 'mutation-leave', 'compiler-materialization', 'complete'}


def encoded(value): return zlib.compress(json.dumps(value, separators=(',', ':')).encode(), 1)
def decoded(value): return json.loads(zlib.decompress(value))


def member(packet_path, packet, name):
    rows = [r for r in packet['files'] if r['path'] == name]
    if len(rows) != 1: raise ValueError('missing or duplicate capture member: ' + name)
    row = rows[0]; original = packet_path.parent / name; path = original.resolve()
    if not path.is_relative_to(packet_path.parent.resolve()) or original.is_symlink():
        raise ValueError('escaping capture member')
    if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
        raise ValueError('capture member identity: ' + name)
    return path, row['sha256']


def inputs(packet_path):
    packet = json.loads(packet_path.read_text())
    if packet['version'] != 1 or packet['execution_status'] != 'PASS':
        raise ValueError('capture is not a completed execution')
    paths = {}; hashes = {}
    for name in ('run.json', 'build.jsonl.gz', 'registries.jsonl.gz'):
        paths[name], hashes[name] = member(packet_path, packet, packet['capture'] + '/' + name)
    record = json.loads(paths['run.json'].read_text())
    if record['status'] != 'PASS' or not record['source_restored'] or record['r6']['unexplained']:
        raise ValueError('capture failed observation/recovery checks')
    fingerprint = dict(packet=digest(packet_path), inputs=hashes,
                       query_tools={str(p.relative_to(HERE.parent)): digest(p) for p in
                           (Path(__file__), HERE / 'native.py', HERE.parent / 'build-flow/flow.py',
                            HERE.parent / 'source-closure/analysis.py')})
    return packet, paths, fingerprint


def stream(path, wanted):
    previous = 0; counts = Counter(); completed = False
    with gzip.open(path, 'rb') as src:
        for line in src:
            if completed: raise ValueError('event after completion')
            header = HEADER.match(line)
            if not header: raise ValueError('invalid native stream header')
            sequence = int(header[1]); kind = header[2].decode()
            if sequence != previous + 1: raise ValueError('missing or reordered native event')
            previous = sequence; counts[kind] += 1
            if kind in wanted:
                row = json.loads(line)
                if kind == 'complete':
                    if row.get('completed', True) is not True: raise ValueError('incomplete registry execution')
                    completed = True
                yield row
    if not completed: raise ValueError('native stream has no completion')


def symbol_from(value):
    nodes = {r['id']: r for r in value['objects']}
    root = nodes.get(value['root'].get('ref'))
    if root and root['kind'] == 'cons':
        if root['car'] == {'atom': 'nil'}:
            return dict(id=None, name='NIL', package='COMMON-LISP',
                        scope='No ordinary symbol identity in this event; retained separately, not a callable cell.')
        root = nodes.get(root['car'].get('ref'))
    if not root or root['kind'] != 'symbol': raise ValueError('binding event has no exact symbol')
    return root


def build_index(paths, target, fingerprint):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists(): raise ValueError('index already exists')
    db = sqlite3.connect(target)
    try:
        db.executescript('''
          CREATE TABLE functions (id INTEGER,event INTEGER,name TEXT,record BLOB,PRIMARY KEY(id,event));
          CREATE TABLE calls (owner INTEGER,site INTEGER,event INTEGER,record BLOB,PRIMARY KEY(owner,site,event));
          CREATE TABLE bindings (symbol INTEGER,event INTEGER,kind TEXT,record BLOB,PRIMARY KEY(symbol,event));
          CREATE TABLE bodies (id INTEGER PRIMARY KEY,record BLOB);
          CREATE TABLE registries (gf INTEGER,event INTEGER,kind TEXT,record BLOB,PRIMARY KEY(gf,event));
          CREATE TABLE materializations (afunc INTEGER,event INTEGER,record BLOB,PRIMARY KEY(afunc,event));
          CREATE TABLE metadata (key TEXT PRIMARY KEY,record BLOB);
          CREATE INDEX names ON functions(name);
        ''')
        operators = None
        for row in stream(paths['build.jsonl.gz'], BUILD_KINDS):
            kind = row['kind']; event = row['sequence']; payload = row['payload']
            if kind == 'snapshot':
                if operators is not None: raise ValueError('duplicate compiler snapshot')
                operators = {r['id']: r['name'] for r in payload['operators']}
            elif kind == 'before-pass2':
                if operators is None: raise ValueError('missing compiler snapshot')
                cap = convert(payload, operators); graph = Graph(cap['flow'])
                raw = {n['id']: n for n in payload['ir']['objects']}
                for f in functions(cap['function']):
                    details = dict(function=f, event=event, source=row['source'], source_position=row['source_position'])
                    db.execute('INSERT INTO functions VALUES (?,?,?,?)', (f['function_id'], event, f['name'], encoded(details)))
                    for c in f['calls']:
                        detail = dict(c, function=f['function_id'], event=event, source=row['source'])
                        if c['dependency']['category'] == 'global-binding':
                            callee = graph.node(graph.items(graph.nodes[c['site_id']]['operands'])[0]); seen = set()
                            while callee and callee.get('operator') in ('CCL::TYPED-FORM', 'CCL::TYPE-ASSERTED-FORM'):
                                if callee['id'] in seen: raise ValueError('cyclic callee wrapper')
                                seen.add(callee['id']); callee = graph.node(graph.items(callee['operands'])[1])
                            value = graph.items(callee['operands'])[0]
                            detail['symbol'] = raw[value['identity']]
                            if detail['symbol']['kind'] != 'symbol': raise ValueError('non-symbol global designator')
                        db.execute('INSERT INTO calls VALUES (?,?,?,?)', (f['function_id'], c['site_id'], event, encoded(detail)))
            elif kind in ('resident-binding', 'binding-installed', 'binding-removing'):
                value = payload['binding'] if kind == 'resident-binding' else payload
                symbol = symbol_from(value)
                detail = dict(row, symbol=symbol, semantics='removal-intent-before-store' if kind == 'binding-removing' else 'observed-value')
                db.execute('INSERT INTO bindings VALUES (?,?,?,?)', (symbol['id'], event, kind, encoded(detail)))
        for row in stream(paths['registries.jsonl.gz'], REGISTRY_KINDS):
            kind = row['kind']; event = row['sequence']
            if kind == 'function':
                db.execute('INSERT INTO bodies VALUES (?,?)', (row['id'], encoded(row)))
            elif kind == 'registry-checkpoint':
                for state in row['entries']:
                    db.execute('INSERT INTO registries VALUES (?,?,?,?)', (state['gf'], event, kind,
                        encoded(dict(state=state, event=event, kind=kind, stage=row['stage']))))
            elif kind in ('mutation-enter', 'mutation-leave'):
                db.execute('INSERT INTO registries VALUES (?,?,?,?)', (row['gf']['gf'], event, kind, encoded(row)))
            elif kind == 'compiler-materialization':
                for entry in row['functions']:
                    db.execute('INSERT INTO materializations VALUES (?,?,?)', (entry['afunc'], event, encoded(dict(entry,event=event,build_event=row['build_event']))))
        counts = {name: db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
                  for name in ('functions', 'calls', 'bindings', 'bodies', 'registries', 'materializations')}
        counts['unkeyed_binding_events'] = db.execute('SELECT count(*) FROM bindings WHERE symbol IS NULL').fetchone()[0]
        for key, value in [('fingerprint', fingerprint), ('counts', counts)]:
            db.execute('INSERT INTO metadata VALUES (?,?)', (key, encoded(value)))
        db.commit()
    finally: db.close()
    save(target.with_suffix(target.suffix + '.json'), dict(fingerprint=fingerprint, counts=counts, sha256=digest(target)))
    return counts


def open_index(packet_path, cache):
    packet, paths, fingerprint = inputs(packet_path)
    if not cache.exists(): build_index(paths, cache, fingerprint)
    proof = json.loads(cache.with_suffix(cache.suffix + '.json').read_text())
    if proof['fingerprint'] != fingerprint or proof['sha256'] != digest(cache):
        raise ValueError('stale or damaged derived index; use a fresh cache path')
    db = sqlite3.connect('file:' + str(cache.resolve()) + '?mode=ro', uri=True)
    actual = decoded(db.execute("SELECT record FROM metadata WHERE key='fingerprint'").fetchone()[0])
    if actual != fingerprint: db.close(); raise ValueError('index capture identity differs')
    return packet, db, proof


def query(packet_path, cache, question):
    packet, db, proof = open_index(packet_path, cache)
    try:
        kind = question['kind']
        if kind == 'summary':
            if set(question) != {'kind'}: raise ValueError('invalid summary query')
            records = [proof['counts']]
        elif kind == 'find-function':
            if set(question) != {'kind', 'name'} or not isinstance(question['name'], str): raise ValueError('invalid function query')
            records = [decoded(r[0]) for r in db.execute('SELECT record FROM functions WHERE name=? ORDER BY id,event', (question['name'],))]
        else:
            mappings = {'function': ('functions', 'id'), 'calls': ('calls', 'owner'),
                        'body': ('bodies', 'id'), 'binding': ('bindings', 'symbol'),
                        'registry': ('registries', 'gf'), 'materialization': ('materializations', 'afunc'),
                        'binding-event': ('bindings', 'event')}
            if kind == 'call-site':
                if set(question) != {'kind', 'function', 'site'} or any(type(question[k]) is not int for k in ('function', 'site')):
                    raise ValueError('invalid call-site query')
                selected = db.execute('SELECT record FROM calls WHERE owner=? AND site=? ORDER BY event', (question['function'], question['site']))
            elif kind in mappings:
                if set(question) != {'kind', 'id'} or type(question['id']) is not int: raise ValueError('invalid identity query')
                table, column = mappings[kind]
                selected = db.execute('SELECT record FROM ' + table + ' WHERE ' + column + '=? ORDER BY rowid', (question['id'],))
            else: raise ValueError('unknown question kind')
            records = [decoded(r[0]) for r in selected]
        return dict(version=1, kind=kind, status='OBSERVED' if records else 'NOT_OBSERVED',
            question=question, namespace=packet['id'], records=records, exhaustive=False,
            scope='One native execution. Absence is not an unsupported disposition; observed values are not a callee bound.',
            evidence=dict(packet_sha256=proof['fingerprint']['packet'], index_sha256=proof['sha256'],
                          inputs=proof['fingerprint']['inputs']))
    finally: db.close()
