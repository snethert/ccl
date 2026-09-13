#!/usr/bin/env python3
"""Join recorded identities and exact FASL locations; never infer targets from names."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path

FAMILIES = {
    'compile-initializer': ('enter', 'return', 'abort'),
    'expander': ('enter', 'return', 'abort'),
    'fasl-effect': ('enter', 'return', 'abort'),
    'fasl-function': ('enter', 'return', 'abort'),
    'load-effect': ('call', 'value', 'abort'),
    'lower': ('enter', 'leave'), 'startup': ('enter', 'return'),
    'binding': ('before', 'after')}
PHASES = {family + '-' + phase: (family, i == 0)
          for family, phases in FAMILIES.items() for i, phase in enumerate(phases)}


class Graph:
    def __init__(self, payload):
        self.root = payload['root']; self.nodes = {r['id']: r for r in payload['objects']}
        if len(self.nodes) != len(payload['objects']): raise ValueError('duplicate payload object ID')

    def node(self, ref):
        if 'ref' not in ref: return ref
        return self.nodes[ref['ref']]

    def atom(self, ref):
        for key in ('string', 'integer', 'character'):
            if key in ref: return ref[key]
        if ref == {'atom': 'nil'}: return None
        return self.node(ref)

    def items(self, ref=None):
        ref = self.root if ref is None else ref
        rows = []; seen = set()
        while ref != {'atom': 'nil'}:
            node = self.node(ref)
            if node['kind'] != 'cons' or not node['expanded'] or node['id'] in seen:
                raise ValueError('expected a complete proper event argument list')
            seen.add(node['id']); rows.append(node['car']); ref = node['cdr']
        return rows

    def args(self): return [self.atom(x) for x in self.items()]

    def slice(self, ref):
        pending = [ref]; seen = set(); result = []
        while pending:
            item = pending.pop()
            if isinstance(item, dict):
                if 'ref' in item and item['ref'] not in seen:
                    seen.add(item['ref']); node = self.nodes[item['ref']]
                    result.append(node); pending.extend(node.values())
                else: pending.extend(item.values())
            elif isinstance(item, list): pending.extend(item)
        return {'root': ref, 'objects': result}

    def function(self, ref):
        value = self.node(ref)
        if value.get('kind') == 'simple-vector':
            # CCL macro bindings hold the actual expander in element 1.
            if value['length'] != 2 or len(value['elements']) != 2:
                raise ValueError('unrecognized binding container')
            value = self.node(value['elements'][1])
        if value.get('kind') != 'function': raise ValueError('binding does not identify a function')
        return value['code']


def reader_context(begin, returned=None):
    graph = Graph(begin); refs = graph.items()
    if len(refs) == 3:
        return {'reader_mode': 'unrecorded', 'reader_function': None}
    if len(refs) != 5: raise ValueError('invalid reader entry payload')
    mode = graph.node(refs[3])
    if mode.get('kind') != 'symbol' or mode.get('package') != 'KEYWORD' or mode['name'] not in ('NATIVE', 'CROSS-DUMP'):
        raise ValueError('unqualified reader dispatch table')
    code = graph.function(refs[4])
    if returned is not None:
        after = Graph(returned); values = after.items()
        if (len(values) != 6 or after.node(values[4]) != mode or after.function(values[5]) != code):
            raise ValueError('reader identity changed across its invocation')
    return {'reader_mode': mode['name'].lower(), 'reader_function': code}


def reader_value(graph, context):
    ref = graph.items()[3]; value = graph.node(ref); mode = context['reader_mode']
    if value.get('kind') == 'function':
        if mode == 'cross-dump': raise ValueError('cross-dump reader returned a host function')
        return {'function': graph.function(ref)}
    if 'integer' in value:
        word = value['integer']
        # U1 x8664 fulltagmask/fulltag-function are both 15. This is an image
        # word, never a host code identity. Legacy streams lack table identity.
        if mode == 'native' or not 16 <= word < 2**64 or word & 15 != 15:
            raise ValueError('reader returned an invalid image function word')
        return {'image_word': word}
    raise ValueError('reader returned neither a host function nor an image function word')


def events(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt') as stream:
        for line in stream: yield json.loads(line)


def analyze(rows, require_complete=True):
    counts = Counter(); stacks = defaultdict(list); entries = {}; last = 0
    functions = {}; materialized = {}; compile_calls = []; load_calls = []; writes = {}; reads = []; image_reads = []
    effect_values = []; resident_before = set(); resident_after = set()
    bindings = []; emissions = []; effects = []; expanders = []; resident = set()
    effect_schedule = []; preceding_effect_boundary = {}
    paths = set(); completed = False; snapshots = []; missing_stack = 0
    for row in rows:
        seq = row['sequence']; kind = row['kind']; process = row['process']; parent = row['parent']
        if row['version'] != 2 or seq != last + 1 or completed: raise ValueError('invalid event sequence/version')
        last = seq; counts[kind] += 1
        phase = PHASES.get(kind)
        if phase:
            family, entering = phase
            if family in ('compile-initializer', 'fasl-effect', 'startup'):
                effect_schedule.append({'event': seq, 'phase': kind, 'process': process,
                                        'prerequisite_boundary': preceding_effect_boundary.get(process),
                                        'rank': len(effect_schedule)})
                preceding_effect_boundary[process] = seq
            if entering:
                expected = stacks[process][-1][1] if stacks[process] else None
                if parent != expected: raise ValueError('entry parent differs from actual nesting')
                stacks[process].append((family, seq)); entries[seq] = row
            else:
                if not stacks[process] or stacks[process][-1] != (family, parent):
                    raise ValueError('unpaired ' + kind)
                stacks[process].pop()
        if kind == 'snapshot': snapshots.append(row['payload'])
        if row['source']: paths.add(row['source'])
        if kind in ('frontend', 'before-pass2'):
            todo = [row['payload']['function']]
            while todo:
                fn = todo.pop(); functions[fn['function_id']] = fn
                todo.extend(fn['inner_functions'])
        elif kind == 'function-materialized':
            graph = Graph(row['payload'])
            for node in graph.nodes.values():
                if node['kind'] == 'afunc' and node['function'] is not None:
                    code = graph.function(node['function'])
                    if code in materialized and materialized[code] != node['id']:
                        raise ValueError('native code mapped to two unrelated afunc identities')
                    materialized[code] = node['id']
        elif kind == 'resident-function':
            graph = Graph(row['payload']['function']); resident.add(graph.function(graph.root))
            (resident_before if row['payload']['stage'] == 'before' else resident_after).add(graph.function(graph.root))
        elif kind == 'compile-effect-call':
            graph = Graph(row['payload']); refs = graph.items()
            compile_calls.append({'event': seq, 'initializer': parent, 'function': graph.function(refs[1])})
        elif kind == 'load-effect-call':
            graph = Graph(row['payload']); refs = graph.items()
            load_calls.append({'event': seq, 'initializer': parent, 'function': graph.function(refs[1]),
                               'file': graph.atom(refs[0])})
        elif kind in ('compile-effect-values', 'load-effect-value'):
            graph = Graph(row['payload']); refs = graph.items()
            effect_values.append({'event': seq, 'parent': parent, 'kind': kind,
                                  'function': graph.function(refs[1]), 'values': graph.slice(refs[2])})
        elif kind == 'fasl-function-write':
            graph = Graph(row['payload']); args = graph.args(); code = graph.function(graph.items()[3])
            key = (args[0], args[1] + 1)
            # A later write to the same filename is a new build version. The
            # loader binds to the most recent preceding write in this session.
            writes[key] = {'event': seq, 'function': code, 'opcode': args[2]}
        elif kind == 'fasl-function-return':
            begin = Graph(entries[parent]['payload']).args(); graph = Graph(row['payload'])
            context = reader_context(entries[parent]['payload'], row['payload'])
            value = reader_value(graph, context); key = (begin[0], begin[2])
            written = writes.get(key)
            (reads if 'function' in value else image_reads).append(
                {'event': seq, 'file': begin[0], 'position_after_opcode': begin[2], **value, **context,
                 'written': written, 'origin': 'exact-file-position' if written else 'preexisting-fasl'})
        elif kind in ('binding-after', 'binding-installed'):
            graph = Graph(row['payload']); refs = graph.items(); symbol = graph.node(refs[0])
            bindings.append({'event': seq, 'parent': parent, 'source': row['source'],
                             'loading_source': row['loading_source'], 'symbol': symbol,
                             'function': graph.function(refs[1])})
        elif kind == 'vinsn-emitted':
            frames = row['context']['handler_frames']; missing_stack += not bool(frames)
            emissions.append({'event': seq, 'function': row['function'], 'template': row['payload']['template'],
                              'template_id': row['payload']['template_id'], 'frames': frames})
        elif kind in ('compile-initializer-return', 'fasl-effect-return', 'startup-return'):
            context = reader_context(entries[parent]['payload'], row['payload']) if kind == 'fasl-effect-return' else {}
            effects.append({'enter': parent, 'return': seq, 'family': phase[0], 'process': process,
                            'parent': entries[parent]['parent'], 'source': entries[parent]['source'], **context})
        elif kind == 'expander-enter':
            graph = Graph(row['payload']); refs = graph.items()
            expanders.append({'event': seq, 'function': graph.function(refs[1]), 'source': row['source']})
        elif kind == 'complete':
            expected = {r['kind']: r['count'] for r in row['payload']['counts']}
            actual = dict(counts); del actual['complete']
            if expected != actual or row['payload']['events_before_complete'] != seq - 1:
                raise ValueError('event counts differ from completion record')
            if any(stacks.values()): raise ValueError('unfinished observation stack')
            completed = True
        if phase and not phase[1]: del entries[parent]
    if require_complete and not completed: raise ValueError('missing completion record')
    unresolved_compile = [r for r in compile_calls if r['function'] not in materialized]
    if unresolved_compile: raise ValueError('executed compile initializer has no materialized front-end function')
    joined_reads = [r for r in reads if r['written']]
    loaded_codes = {r['function']: r['written']['function'] for r in joined_reads}
    def code_origin(code):
        if code in materialized: return {'origin': 'materialized', 'afunc': materialized[code]}
        if code in loaded_codes:
            emitted = loaded_codes[code]
            return {'origin': 'exact-fasl-position', 'compiled_code': emitted, 'afunc': materialized.get(emitted)}
        if code in resident_before: return {'origin': 'resident-before'}
        return {'origin': 'not-joined'}
    for call in load_calls: call['code_origin'] = code_origin(call['function'])
    handler_origins = {frame['code']: code_origin(frame['code']) for emission in emissions for frame in emission['frames']}
    calls = [dict(call, owner=fn['function_id']) for fn in functions.values() for call in fn['calls']]
    dynamic = [r for r in calls if not r['dependency']['targets']]
    return {'version': 1, 'counts': dict(counts), 'sources': sorted(paths), 'snapshots': snapshots,
            'functions': list(functions.values()), 'materialized': [{'function': k, 'afunc': v} for k, v in materialized.items()],
            'compile_calls': compile_calls, 'load_calls': load_calls, 'effect_values': effect_values,
            'fasl_reads': reads, 'image_function_reads': image_reads, 'bindings': bindings,
            'emissions': emissions, 'effects': effects, 'expanders': expanders,
            'effect_schedule': effect_schedule,
            'schedule_basis': 'Conservative order of actual native effect calls within each process. Entry/completion phase splits preserve nested evaluation; this is not a minimal read/write dependency analysis.',
            'handler_origins': [{'code': code, **origin} for code, origin in handler_origins.items()],
            'resident_functions': sorted(resident), 'resident_before': sorted(resident_before),
            'resident_after': sorted(resident_after),
            'summary': {'events': last, 'sources': len(paths), 'afuncs': len(functions),
                        'materialized_functions': len(materialized), 'compile_initializers_joined': len(compile_calls),
                        'load_initializers': len(load_calls),
                        'load_initializers_joined': sum(r['code_origin']['origin'] != 'not-joined' for r in load_calls),
                        'functions_read': len(reads), 'functions_joined_by_fasl_position': len(joined_reads),
                        'image_functions_read': len(image_reads),
                        'image_functions_joined_by_fasl_position': sum(bool(r['written']) for r in image_reads),
                        'reader_effects_by_mode': dict(Counter(r['reader_mode'] for r in effects if r['family'] == 'fasl-effect')),
                        'bindings': len(bindings), 'instruction_emissions': len(emissions),
                        'emissions_without_live_handler': missing_stack, 'expansions': len(expanders),
                        'distinct_handler_codes': len(handler_origins),
                        'handler_codes_joined': sum(r['origin'] != 'not-joined' for r in handler_origins.values()),
                        'calls': len(calls), 'dynamic_calls': len(dynamic), 'completed_effects': len(effects)},
            'scope': 'Recorded native execution identities. Dispatch stacks omit tail-elided frames. Dynamic candidates and profile dispositions require the census closure; this is not an accepted LL15 envelope.'}


def write(path, value):
    with gzip.open(path, 'wt', compresslevel=6) as f: json.dump(value, f, separators=(',', ':')); f.write('\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('events', type=Path); p.add_argument('output', type=Path)
    a = p.parse_args(); data = analyze(events(a.events)); write(a.output, data)
    print(json.dumps(data['summary'], sort_keys=True))
