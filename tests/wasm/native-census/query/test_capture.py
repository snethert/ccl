"""Compare indexed answers with original events; reject damaged inputs and scope changes."""
import argparse
from copy import deepcopy
import gzip
import json
from pathlib import Path
import shutil
import sqlite3
from capture import query, stream, member, decoded
from native import save


def run(a):
    a.output.mkdir(parents=True, exist_ok=False)
    packet = json.loads(a.capture.read_text())
    directory = a.capture.parent / packet['capture']
    # These independent selections come directly from native event fields, not the index.
    originals = {}
    with gzip.open(directory / 'registries.jsonl.gz', 'rt') as src:
        for line in src:
            row = json.loads(line)
            if row['kind'] == 'function' and 'body' not in originals: originals['body'] = row
            if row['kind'] == 'registry-checkpoint' and 'registry' not in originals: originals['registry'] = row
            if row['kind'] == 'compiler-materialization':
                originals['materialization'] = row
                break
    with gzip.open(directory / 'build.jsonl.gz', 'rt') as src:
        for line in src:
            row = json.loads(line)
            if row['kind'] == 'binding-removing':
                originals['removal'] = row
                break
    save(a.output / 'original-events.json', originals)
    cases = []
    def check(name, ok):
        if not ok: raise AssertionError(name)
        cases.append(dict(case=name, status='PASS'))
    def ask(question):
        answer = query(a.capture, a.cache, question)
        check('scope-' + str(len(cases)), answer['exhaustive'] is False and answer['namespace'] == packet['id'])
        return answer
    body = originals['body']
    check('literal-native-body', ask(dict(kind='body', id=body['id']))['records'] == [body])
    registry = originals['registry']; state = registry['entries'][0]
    rows = ask(dict(kind='registry', id=state['gf']))['records']
    check('literal-registry-checkpoint', rows[0] == dict(state=state, event=registry['sequence'], kind=registry['kind'], stage=registry['stage']))
    material = originals['materialization']; entry = material['functions'][0]
    check('literal-materialization', ask(dict(kind='materialization', id=entry['afunc']))['records'][0] == dict(entry, event=material['sequence'], build_event=material['build_event']))
    removal = originals['removal']
    answer = ask(dict(kind='binding-event', id=removal['sequence']))['records'][0]
    check('removal-is-intent', answer['semantics'] == 'removal-intent-before-store')
    check('literal-removal-payload', {k: answer[k] for k in removal} == removal)
    check('missing-is-not-observed', ask(dict(kind='body', id=-1))['status'] == 'NOT_OBSERVED')
    found = ask(dict(kind='find-function', name='CCL::GETF-TEST'))['records']
    wanted = {r['event']: r for r in found}; raw_sources = {}
    with gzip.open(directory / 'build.jsonl.gz', 'rt') as src:
        for number, line in enumerate(src, 1):
            if number in wanted:
                row = json.loads(line)
                raw_sources[number] = row
                check('source-event-' + str(number), row['sequence'] == number and row['kind'] == 'before-pass2'
                      and all(wanted[number][k] == row[k] for k in ('source', 'source_position')))
            if number >= max(wanted): break
    check('names-are-not-identities', len(found) == 3 and len(raw_sources) == 3
          and len({r['source'] for r in found}) == 2)
    save(a.output / 'source-events.json', raw_sources)
    function = next(r['function'] for r in found if r['source'].endswith('/level-1/l1-utils.lisp'))
    call = function['calls'][0]
    site = ask(dict(kind='call-site', function=function['function_id'], site=call['site_id']))['records']
    check('site-belongs-to-function', len(site) == 1 and all(site[0][k] == v for k, v in call.items()))

    def reject(name, thunk, reason):
        try: thunk()
        except (ValueError, OSError, KeyError) as error:
            if reason not in str(error): raise AssertionError((name, str(error)))
        else: raise AssertionError('control escaped: ' + name)
        cases.append(dict(case=name, status='REJECTED'))
    for question in [dict(kind='summary', exhaustive=True), dict(kind='body', id=True),
                     dict(kind='calls', id=2, namespace='another'), dict(kind='unknown')]:
        reject('invalid-question-' + str(len(cases)), lambda q=question: ask(q), 'query' if question['kind'] != 'unknown' else 'kind')
    for name, lines, reason in [
        ('missing-completion', [dict(sequence=1, kind='sample')], 'no completion'),
        ('lost-event', [dict(sequence=2, kind='complete')], 'reordered'),
        ('after-completion', [dict(sequence=1, kind='complete'), dict(sequence=2, kind='sample')], 'after completion'),
        ('incomplete', [dict(sequence=1, kind='complete', completed=False)], 'incomplete'),
    ]:
        path = a.output / (name + '.jsonl.gz')
        with gzip.open(path, 'wt') as dst:
            for row in lines: dst.write(json.dumps(row, separators=(',', ':')) + '\n')
        reject(name, lambda p=path: list(stream(p, {'complete'})), reason)
    base = a.output / 'members'; base.mkdir(); (base / 'sample').write_text('data')
    spec = dict(files=[dict(path='sample', bytes=4, sha256='0' * 64)])
    reject('wrong-member-hash', lambda: member(base / 'packet.json', spec, 'sample'), 'identity')
    reject('missing-member', lambda: member(base / 'packet.json', spec, 'absent'), 'missing')
    duplicate = deepcopy(spec); duplicate['files'] *= 2
    reject('duplicate-member', lambda: member(base / 'packet.json', duplicate, 'sample'), 'duplicate')
    escaping = dict(files=[dict(path='../outside', bytes=0, sha256='0' * 64)])
    reject('escaping-member', lambda: member(base / 'packet.json', escaping, '../outside'), 'escaping')
    # A copied derived cache is disposable; retained inputs are never changed.
    damaged = a.output / 'damaged.sqlite'; shutil.copyfile(a.cache, damaged)
    proof_path = damaged.with_suffix('.sqlite.json')
    shutil.copyfile(a.cache.with_suffix(a.cache.suffix + '.json'), proof_path)
    with damaged.open('ab') as dst: dst.write(b'changed')
    reject('damaged-cache', lambda: query(a.capture, damaged, dict(kind='summary')), 'stale or damaged')
    shutil.copyfile(a.cache, damaged)
    proof = json.loads(proof_path.read_text()); proof['fingerprint']['packet'] = '0' * 64; save(proof_path, proof)
    reject('wrong-cache-capture', lambda: query(a.capture, damaged, dict(kind='summary')), 'stale or damaged')
    # Every NULL cell remains a separately identifiable event, never a symbol bound.
    db = sqlite3.connect(a.cache)
    unkeyed = [decoded(r[0]) for r in db.execute('SELECT record FROM bindings WHERE symbol IS NULL')]; db.close()
    check('unkeyed-events-preserved', len(unkeyed) == 27 and all(r['symbol']['id'] is None for r in unkeyed))
    save(a.output / 'summary.json', dict(status='PASS', cases=cases, scope='Retained capture queries and quarantined refusals; no closure or gate credit.'))
    print('PASS', len(cases), 'capture checks')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('capture', 'cache', 'output'): p.add_argument('--' + name, type=Path, required=True)
    run(p.parse_args())
