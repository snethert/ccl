"""Classify still-unjoined prototype identities using one original execution."""
from collections import Counter, defaultdict
import copy
import hashlib
import json
import re

SCOPE = 'First recorded native function descriptors; no allocation-time, complete body, call-bound or heap-area claim.'
HEADER = re.compile(rb'^\{"version":2,"sequence":([0-9]+),"kind":"([a-z0-9-]+)"')
CODE = re.compile(rb'"code":([0-9]+)')
FIELDS = ('sequence', 'kind', 'process', 'parent', 'source', 'source_position', 'loading_source')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def targets(bodies, delta):
    open_codes = [int(e['from'].rsplit(':', 1)[1]) for e in delta['edges']
                  if e['evidence'].startswith('binding-versions/body/') and e['resolution'] == 'unresolved']
    witnessed = [r['code'] for r in bodies['bodies']]
    remaining = bodies['remaining_codes']
    require(len(set(open_codes)) == len(open_codes) and len(set(witnessed)) == len(witnessed), 'BODY_IDENTITY_SET')
    require(set(witnessed) <= set(open_codes) and remaining == sorted(set(open_codes) - set(witnessed)), 'REMAINING_PARTITION')
    return remaining


def binding_view(facts, histories, wanted):
    wanted = set(wanted)
    observations = defaultdict(dict)
    symbols = defaultdict(dict)
    original = {r['sequence']: r for r in facts['bindings']}
    require(len(original) == len(facts['bindings']), 'BINDING_EVENT_UNIQUENESS')
    for h in histories:
        if not h['call_count']:
            continue
        for o in h['observations']:
            v = o['value']
            if v['role'] != 'function' or v['code'] not in wanted:
                continue
            # The history adds an origin annotation, not a new observation.
            unannotated = copy.deepcopy(o)
            del unannotated['value']['origin']
            require(unannotated == original.get(o['sequence']), 'BINDING_HISTORY_JOIN')
            require(o['symbol']['id'] == h['symbol_id'], 'CALLED_SYMBOL_IDENTITY')
            observations[v['code']][o['sequence']] = o
            symbols[v['code']][h['symbol_id']] = dict(symbol_id=h['symbol_id'], descriptors=h['descriptors'], call_count=h['call_count'])
    require(set(observations) == wanted, 'CALLED_VALUE_COVERAGE')
    initial = defaultdict(list)
    for r in facts['residents']:
        if r['stage'] == 'before' and r['code'] in wanted:
            initial[r['code']].append(r)
    return {c: dict(first_binding=observations[c][min(observations[c])],
                    initial_residents=initial.get(c, []),
                    called_symbols=[symbols[c][s] for s in sorted(symbols[c])]) for c in sorted(wanted)}


def descriptors(value, path=()):
    pending = [(value, path)]
    while pending:
        v, where = pending.pop()
        if isinstance(v, dict):
            if v.get('kind') == 'function' and 'code' in v:
                require(set(v) == {'id', 'kind', 'code', 'description'} and type(v['code']) is int, 'FUNCTION_DESCRIPTOR_SHAPE')
                yield dict(path=list(where), value=v)
            pending.extend((x, where + (k,)) for k, x in v.items())
        elif isinstance(v, list):
            pending.extend((x, where + (i,)) for i, x in enumerate(v))


def scan(lines, wanted, parent_ids, expected_counts):
    """Read the complete stream, retaining first descriptors and direct parents.

    The byte prefilter only selects candidate lines. Parsed function records
    determine identities; integer literals and similarly spelled names do not.
    """
    pending = set(wanted)
    parents = {}
    first = {}
    witnesses = []
    counts = Counter()
    last = 0
    complete = False
    for line in lines:
        match = HEADER.match(line)
        require(match is not None, 'EVENT_HEADER')
        seq, kind = int(match[1]), match[2].decode()
        require(seq == last + 1 and not complete, 'EVENT_SEQUENCE')
        last = seq
        counts[kind] += 1
        candidates = pending.intersection(int(m[1]) for m in CODE.finditer(line))
        if not candidates and seq not in parent_ids and kind != 'complete':
            continue
        event = json.loads(line)
        require(event['sequence'] == seq and event['kind'] == kind, 'EVENT_HEADER_JOIN')
        keep = seq in parent_ids
        if keep:
            parents[seq] = {k: event[k] for k in FIELDS}
        found = defaultdict(list)
        if candidates:
            for item in descriptors(event):
                if item['value']['code'] in pending:
                    found[item['value']['code']].append(item)
            for code, items in found.items():
                first[code] = dict(event={k: event[k] for k in FIELDS},
                                   descriptors=sorted(items, key=canonical),
                                   event_sha256=hashlib.sha256(line).hexdigest())
                pending.remove(code)
            keep = keep or bool(found)
        if kind == 'complete':
            complete = True
            expected = {r['kind']: r['count'] for r in event['payload']['counts']}
            require(expected == {k: v for k, v in counts.items() if k != 'complete'}
                    and event['payload']['events_before_complete'] == seq - 1, 'STREAM_COMPLETION')
        if keep:
            witnesses.append(line)
    require(complete and dict(counts) == expected_counts, 'STREAM_COUNTS')
    require(not pending and set(parents) == set(parent_ids), 'FIRST_DESCRIPTOR_COVERAGE')
    return dict(first={str(k): v for k, v in sorted(first.items())},
                parents={str(k): v for k, v in sorted(parents.items())}, events=last), witnesses


def assemble(wanted, view, capture, inventories, readonly_codes):
    require(wanted == sorted(set(wanted)) and set(wanted) == set(view)
            and set(map(int, capture['first'])) == set(wanted), 'CLASSIFICATION_COVERAGE')
    require(not set(wanted).intersection(readonly_codes), 'READONLY_RECLASSIFICATION')
    before = [r for r in inventories if r['payload']['stage'] == 'before']
    require([r['kind'] for r in before] == ['inventory-enter', 'inventory-return'], 'INITIAL_INVENTORY_BOUNDARIES')
    start, end = (r['sequence'] for r in before)
    rows = []
    for code in wanted:
        v = view[code]
        first = capture['first'][str(code)]
        event = first['event']
        binding = v['first_binding']
        require(all(d['value']['code'] == code for d in first['descriptors']), 'FIRST_DESCRIPTOR_IDENTITY')
        require(event['sequence'] <= binding['sequence'] and event['process'] == binding['process'], 'FIRST_DESCRIPTOR_ORDER')
        if v['initial_residents']:
            require(event['kind'] == 'resident-function' and start < event['sequence'] < end
                    and event['sequence'] == min(r['event'] for r in v['initial_residents']), 'INITIAL_RESIDENT_WITNESS')
            require(binding['kind'] == 'resident-binding' and binding.get('stage') == 'before', 'INITIAL_BINDING_WITNESS')
            category = 'INITIAL_INVENTORY_OUTSIDE_READONLY'
        else:
            require(binding['kind'] == 'binding-installed' and binding['sequence'] > end
                    and event['sequence'] == binding['sequence'], 'FIRST_INSTALLATION_WITNESS')
            require(any(d['value']['id'] == binding['value']['object'] for d in first['descriptors']), 'INSTALLED_OBJECT_IDENTITY')
            category = 'FIRST_DESCRIPTOR_AT_LATER_INSTALLATION'
        parent = capture['parents'].get(str(binding['parent'])) if binding['parent'] is not None else None
        require(binding['parent'] is None or parent is not None and parent['sequence'] < binding['sequence']
                and parent['process'] == binding['process'], 'INSTALLATION_PARENT_JOIN')
        rows.append(dict(code=code,category=category,first_descriptor=first,
                         first_called_binding=binding,initial_residents=v['initial_residents'],
                         called_symbols=v['called_symbols'],binding_parent=parent,
                         complete_body=False,heap_area='UNCLASSIFIED'))
    categories = Counter(r['category'] for r in rows)
    sources = Counter((r['category'], r['first_called_binding']['value']['description']['source']) for r in rows)
    later = [r for r in rows if r['category'] == 'FIRST_DESCRIPTOR_AT_LATER_INSTALLATION']
    summary = dict(scope=SCOPE,prototypes=len(rows),categories=dict(categories),
                   descriptor_source_annotations=[dict(category=c,source=s,count=n) for (c,s),n in sorted(sources.items(), key=lambda x:canonical(x[0]))],
                   later_loading_contexts=dict(Counter(r['first_called_binding']['loading_source'] for r in later)),
                   later_parent_kinds=dict(Counter(r['binding_parent']['kind'] if r['binding_parent'] else 'NONE' for r in later)),
                   raw_stream_events=capture['events'],census_gate_credit=False,source_ir_bodies_closed=0,
                   computed_call_bounds_closed=0,native_execution=False)
    return dict(version=1,scope=SCOPE,prototypes=rows), summary


def controls(wanted, view, capture, inventories, readonly_codes, result, summary):
    outcomes = []
    def reject(name, fn, reason):
        try:
            fn()
        except ValueError as error:
            require(str(error) == reason, 'CONTROL_REASON '+name+': '+str(error))
            outcomes.append(dict(name=name,reason=reason))
        else:
            raise ValueError('CONTROL_ESCAPED '+name)
    def run(v=view, c=capture, ro=readonly_codes):
        return assemble(wanted,v,c,inventories,ro)
    def changed_capture(code, change):
        c=copy.deepcopy(capture);change(c['first'][str(code)]);return c
    initial=next(c for c in wanted if view[c]['initial_residents'])
    late=next(c for c in wanted if not view[c]['initial_residents'])
    c=copy.deepcopy(capture);del c['first'][str(initial)]
    reject('omit-first-descriptor',lambda:run(c=c),'CLASSIFICATION_COVERAGE')
    reject('promote-readonly-code',lambda:run(ro=readonly_codes+[initial]),'READONLY_RECLASSIFICATION')
    c=changed_capture(initial,lambda x:x['descriptors'][0]['value'].update(code=late))
    reject('substitute-code-with-equal-name',lambda:run(c=c),'FIRST_DESCRIPTOR_IDENTITY')
    c=changed_capture(initial,lambda x:x['event'].update(sequence=view[initial]['first_binding']['sequence']+1))
    reject('first-descriptor-after-binding',lambda:run(c=c),'FIRST_DESCRIPTOR_ORDER')
    c=changed_capture(initial,lambda x:x['event'].update(kind='binding-installed'))
    reject('initial-function-as-late-install',lambda:run(c=c),'INITIAL_RESIDENT_WITNESS')
    v=copy.deepcopy(view);v[late]['first_binding']['kind']='binding-removing'
    reject('removal-intent-as-installation',lambda:run(v=v),'FIRST_INSTALLATION_WITNESS')
    v=copy.deepcopy(view);v[initial]['first_binding']['stage']='after'
    reject('after-inventory-as-initial',lambda:run(v=v),'INITIAL_BINDING_WITNESS')
    c=changed_capture(late,lambda x:x['descriptors'][0]['value'].update(id=-1))
    reject('wrong-installed-object',lambda:run(c=c),'INSTALLED_OBJECT_IDENTITY')
    c=copy.deepcopy(capture);del c['parents'][str(view[late]['first_binding']['parent'])]
    reject('missing-effect-parent',lambda:run(c=c),'INSTALLATION_PARENT_JOIN')
    c=copy.deepcopy(capture);c['parents'][str(view[late]['first_binding']['parent'])]['process']=-1
    reject('cross-process-parent',lambda:run(c=c),'INSTALLATION_PARENT_JOIN')
    expected=run()
    for name, mutation in [('omit-worklist-row',lambda r,s:r['prototypes'].pop()),
                          ('invent-heap-area',lambda r,s:r['prototypes'][0].update(heap_area='dynamic')),
                          ('promote-body-to-complete',lambda r,s:r['prototypes'][0].update(complete_body=True)),
                          ('claim-census-credit',lambda r,s:s.update(census_gate_credit=True))]:
        r,s=copy.deepcopy((result,summary));mutation(r,s)
        reject(name,lambda:require((r,s)==expected,'DERIVED_RECORDS'),'DERIVED_RECORDS')
    # A compact parser corpus exercises the byte prefilter independently of
    # the genuine stream. Equal names and opaque integer fields are not IDs.
    def event(seq, kind, payload):
        return dict(version=2,sequence=seq,kind=kind,process=1,parent=None,
                    source=None,source_position=None,loading_source=None,payload=payload)
    def fn(code):
        return dict(kind='function',id=code,code=code,description=dict(name='SAME',source=None,position=None))
    corpus=[event(1,'snapshot',dict(kind='opaque',code=11)),
            event(2,'resident-function',fn(11)),
            event(3,'binding-installed',fn(11)),
            event(4,'binding-installed',fn(12))]
    counts=Counter(r['kind'] for r in corpus)
    corpus.append(event(5,'complete',dict(events_before_complete=4,counts=[dict(kind=k,count=n) for k,n in counts.items()])))
    counts['complete']=1
    def parsed(rows):
        return scan([(json.dumps(r,separators=(',',':'))+'\n').encode() for r in rows],[11,12],[],dict(counts))[0]
    positive=parsed(corpus)
    require(positive['first']['11']['event']['sequence']==2 and positive['first']['12']['event']['sequence']==4,
            'PARSER_FIRST_DESCRIPTOR_PROBE')
    bad=copy.deepcopy(corpus);bad[1]['sequence']=1
    reject('parser-duplicate-sequence',lambda:parsed(bad),'EVENT_SEQUENCE')
    reject('parser-missing-completion',lambda:parsed(corpus[:-1]),'STREAM_COUNTS')
    bad=copy.deepcopy(corpus);bad[-1]['payload']['events_before_complete']=3
    reject('parser-corrupt-completion',lambda:parsed(bad),'STREAM_COMPLETION')
    bad=copy.deepcopy(corpus);bad[1]['payload']['extra']='unqualified'
    reject('parser-unqualified-descriptor',lambda:parsed(bad),'FUNCTION_DESCRIPTOR_SHAPE')
    return dict(status='PASS',controls_rejected=len(outcomes),controls=outcomes,
                positive_probes=['first-descriptor-not-later-copy-or-equal-name-or-opaque-integer'])
