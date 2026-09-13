#!/usr/bin/env python3
"""Check boot execution order, retained identities and final binding state."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

PAYLOADS = {
    'boot-start': {'queued', 'startup_file'}, 'handoff': {'phase'},
    **{k: {'function'} for k in ('cold-enter', 'cold-return', 'call-enter', 'call-return')},
    **{k: {'file', 'table'} for k in ('load-enter', 'load-return')},
    'reader-enter': {'file', 'offset', 'opcode', 'reader', 'table'}, 'reader-return': {'reader'},
    **{k: {'symbol', 'old', 'new'} for k in ('binding-installed', 'binding-removing')},
}


def read(path):
    with (gzip.open(path, 'rt') if path.suffix == '.gz' else path.open()) as stream:
        return [json.loads(line) for line in stream]


def analyze(rows):
    def require(condition, reason):
        if not condition: raise ValueError(reason)
    require(rows and all(r.get('version') == 1 for r in rows), 'STREAM_VERSION')
    require(rows[0]['kind'] == 'capture' and rows[-1]['kind'] == 'complete', 'STREAM_COMPLETION')
    header, completion = rows[0], rows[-1]
    require(header['owner_thread_only'] is True and header['foreign_thread_observed'] is False, 'OWNER_THREAD_SCOPE')
    events = [r for r in rows if 'sequence' in r]
    require(all(set(r) == {'version', 'kind', 'sequence', 'payload'} and
                r['kind'] in PAYLOADS and set(r['payload']) == PAYLOADS[r['kind']] for r in events), 'EVENT_FIELDS')
    require(header['events'] == completion['events'] == len(events) and len(events) > 0, 'EVENT_COUNTS')
    require([r['sequence'] for r in events] == list(range(1, len(events) + 1)) and
            all(type(r['sequence']) is int for r in events), 'EVENT_SEQUENCE')
    finals = [r for r in rows if r['kind'] == 'final-bindings']; require(len(finals) == 1, 'FINAL_BINDINGS_SECTION')
    descriptions = [r['object'] for r in rows if r['kind'] == 'object']
    objects = {r['id']: r for r in descriptions}
    require(len(objects) == len(descriptions) == completion['described_objects'], 'OBJECT_IDENTITIES')
    require(all(type(i) is int and 1 <= i <= completion['identities'] for i in objects), 'OBJECT_ID_RANGE')
    require(len(rows) == len(events) + len(descriptions) + 3, 'SURPLUS_STREAM_RECORD')
    require(rows[1:1 + len(events)] == events and rows[1 + len(events)] == finals[0], 'STREAM_SECTION_ORDER')
    def obj(i, kind=None):
        require(i in objects and (kind is None or objects[i]['kind'] == kind), 'OBJECT_REFERENCE')
        return objects[i]
    def function(i):
        row = obj(i, 'function'); require(type(row['code']) is int and 1 <= row['code'] <= completion['identities'], 'CODE_ID_RANGE')
        return row
    require(events[0]['kind'] == 'boot-start' and events[-1]['kind'] == 'handoff', 'BOOT_PHASE_BOUNDARY')
    queue = events[0]['payload']['queued']; require(len(queue) > 0, 'EMPTY_COLD_QUEUE')
    require(queue == header['original_cold_queue'], 'ORIGINAL_COLD_QUEUE')
    for i in queue: function(i)
    initial_rows = header['initial_bindings']; initial = {r['symbol']: r['value'] for r in initial_rows}
    require(len(initial) == len(initial_rows) and initial, 'INITIAL_BINDING_IDENTITIES')
    for sym, value in initial.items(): obj(sym, 'symbol'); obj(value)
    stack = []; calls = []; loads = []; readers = []; bindings = []; current = dict(initial); cold = []; counts = Counter()
    enter_kinds = {'cold-enter': 'cold', 'load-enter': 'load', 'reader-enter': 'reader', 'call-enter': 'call'}
    returns = {'cold-return': 'cold', 'load-return': 'load', 'reader-return': 'reader', 'call-return': 'call'}
    for event in events:
        kind, seq, p = event['kind'], event['sequence'], event['payload']; counts[kind] += 1
        if kind == 'boot-start':
            require(seq == 1, 'DUPLICATE_BOOT_START'); continue
        if kind == 'handoff':
            require(seq == len(events) and p == {'phase': 'normal-toplevel'}, 'HANDOFF_POSITION')
            continue
        if kind in enter_kinds:
            family = enter_kinds[kind]
            if family == 'cold':
                require(not stack and len(cold) < len(queue) and p['function'] == queue[len(cold)], 'COLD_QUEUE_ORDER')
            elif family == 'reader':
                enclosing_load = next((r for r in reversed(stack) if r['family'] == 'load'), None)
                require(enclosing_load and enclosing_load['file'] == p['file'] and
                        enclosing_load['table'] == p['table'], 'READER_LOAD_CONTEXT')
                require(type(p['offset']) is int and p['offset'] >= 0 and type(p['opcode']) is int, 'READER_OPERAND')
                function(p['reader'])
            elif family == 'call':
                require(stack and stack[-1]['family'] == 'reader' and not stack[-1].get('call'), 'CALL_READER_CONTEXT')
                stack[-1]['call'] = seq; function(p['function'])
            elif family == 'load':
                require(isinstance(p['file'], str) and p['file'] and type(p['table']) is int and
                        1 <= p['table'] <= completion['identities'], 'LOAD_CONTEXT')
                if not stack:
                    require(len(cold) == len(queue), 'LOAD_BEFORE_COLD_QUEUE')
            record = {'family': family, 'enter': seq, 'parent': stack[-1]['enter'] if stack else None, **p}
            stack.append(record); continue
        if kind in returns:
            family = returns[kind]
            require(stack and stack[-1]['family'] == family, 'RETURN_NESTING')
            entry = stack.pop()
            require(all(entry.get(k) == value for k, value in p.items()), 'RETURN_IDENTITY')
            record = {**entry, 'return': seq}
            if family == 'cold': cold.append(record)
            elif family == 'load': loads.append(record)
            elif family == 'reader':
                require('call' in entry, 'READER_CALL_MISSING'); readers.append(record)
            else: calls.append(record)
            continue
        if kind in ('binding-installed', 'binding-removing'):
            sym = p['symbol']; obj(sym, 'symbol'); obj(p['old']); obj(p['new'])
            require(sym in current and current[sym] == p['old'], 'BINDING_CHAIN')
            current[sym] = p['new']
            if kind == 'binding-removing': require(objects[p['new']]['kind'] == 'unbound-function', 'REMOVAL_TARGET')
            bindings.append({'event': seq, 'kind': kind, 'parent': stack[-1]['enter'] if stack else None, **p})
            continue
        raise ValueError('UNKNOWN_EVENT_KIND: ' + kind)
    require([c['function'] for c in cold] == queue, 'COLD_QUEUE_COVERAGE')
    require([r['family'] for r in stack] == ['load', 'reader', 'call'], 'HANDOFF_ACTIVE_FRAMES')
    require(stack[0]['file'] == events[0]['payload']['startup_file'] and stack[1]['file'] == stack[0]['file'], 'HANDOFF_STARTUP_FILE')
    require(stack[1].get('call') == stack[2]['enter'], 'HANDOFF_CALL_LINK')
    final_rows = finals[0]['bindings']; final = {r['symbol']: r['value'] for r in final_rows}
    require(len(final) == len(final_rows) and final == current and
            set(initial) == {r['symbol'] for r in bindings}, 'FINAL_BINDING_STATE')
    require(counts['binding-installed'] > 0 and calls and loads, 'EMPTY_BOOT_OBSERVATION')
    return {'version': 1, 'status': 'BOOT_EXECUTION_OBSERVED_UNQUALIFIED', 'review_disposition': 'NOT_REVIEWED',
            'scope': 'Owner-thread cold initializer queue and boot loader through explicit top-level handoff; exact retained object identities, not complete static dependencies or cross-process code equivalence.',
            'summary': {'events': len(events), 'cold_initializers': len(cold), 'completed_loads': len(loads),
                        'completed_readers': len(readers), 'completed_calls': len(calls),
                        'installations': counts['binding-installed'], 'removals': counts['binding-removing'],
                        'binding_symbols': len(final), 'objects': len(objects), 'active_handoff_frames': len(stack)},
            'cold_initializers': cold, 'loads': sorted(loads, key=lambda r: r['enter']),
            'readers': sorted(readers, key=lambda r: r['enter']), 'calls': sorted(calls, key=lambda r: r['enter']),
            'initial_bindings': initial_rows, 'final_bindings': final_rows,
            'bindings': bindings, 'handoff': stack, 'objects': descriptions}


def bind_files(result, source, overrides=None, recorded_root=None):
    """Join every observed load and opcode to real, unchanged retained bytes."""
    source = source.resolve(); overrides = overrides or {}
    recorded_root = Path(recorded_root).resolve() if recorded_root else source
    readers = result['readers'] + [r for r in result['handoff'] if r['family'] == 'reader']
    loads = result['loads'] + [r for r in result['handoff'] if r['family'] == 'load']
    rows = []
    for name in sorted({r['file'] for r in loads}):
        original = (recorded_root / name).resolve()
        if recorded_root not in original.parents: raise ValueError('LOAD_OUTSIDE_ARCHIVE')
        relative = str(original.relative_to(recorded_root))
        path = (source / relative).resolve()
        if source not in path.parents: raise ValueError('LOAD_OUTSIDE_ARCHIVE')
        actual = overrides.get(relative, path)
        data = actual.read_bytes()
        related = [r for r in readers if r['file'] == name]
        for r in related:
            # Independently pinned U1 xdump/faslenv.lisp constants: lfuncall=4,
            # epush flag=bit 7. The recorded offset points to the opcode byte.
            if not (0 <= r['offset'] < len(data) and data[r['offset']] == r['opcode'] and
                    r['opcode'] & 127 == 4): raise ValueError('FASL_OPCODE_IDENTITY')
        rows.append({'file': name, 'relative_path': relative, 'sha256': hashlib.sha256(data).hexdigest(),
                     'bytes': len(data), 'load_entries': [r['enter'] for r in loads if r['file'] == name],
                     'reader_entries': [r['enter'] for r in related]})
    return {'version': 1, 'files': rows, 'opcode_witnesses': len(readers)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('events', type=Path); p.add_argument('output', type=Path)
    a = p.parse_args(); result = analyze(read(a.events))
    with gzip.open(a.output, 'wt') as stream: json.dump(result, stream, separators=(',', ':')); stream.write('\n')
    print(json.dumps(result['summary'], indent=2))
