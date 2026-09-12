"""Read retained event identities. Printed forms are previews, never parsed as code."""
import json


def module(source):
    if source is None:
        return '@rebuild-driver'
    if '/ccl/' in source:
        return source.split('/ccl/', 1)[1]
    if source.lower().startswith('ccl:'):
        return source[4:].removesuffix('.newest').replace(';', '/')
    return source


def read_events(path):
    complete = False
    with path.open() as stream:
        for count, line in enumerate(stream, 1):
            event = json.loads(line)
            if complete or event['sequence'] != count:
                raise ValueError('event sequence/completion mismatch')
            if event['kind'] == 'complete':
                if event['payload']['events_before_complete'] != count - 1:
                    raise ValueError('event completion count mismatch')
                complete = True
            yield event
    if not complete:
        raise ValueError('incomplete event stream')


def collect(rebuild, cold, image):
    compile_effects, load_effects, stack = [], [], []
    for e in read_events(rebuild):
        kind, seq = e['kind'], e['sequence']
        if kind == 'compile-initializer-enter':
            row = {'enter': seq, 'return': None, 'module': module(e['source']),
                   'source_position': e['source_position'], 'preview': e['payload'],
                   'parent': stack[-1]['enter'] if stack else None,
                   'compiled_during': []}
            compile_effects.append(row)
            stack.append(row)
        elif kind == 'compile-initializer-return':
            if not stack:
                raise ValueError('initializer return without entry')
            row = stack.pop()
            if (row['module'], row['source_position']) != (module(e['source']), e['source_position']):
                raise ValueError('initializer return identity mismatch')
            row['return'] = seq
            # GC can relocate objects printed in the preview. The paired hooks
            # surround one dynamic invocation, not an immutable textual form.
            row['return_preview'] = e['payload']
        elif kind == 'before-pass2' and stack:
            # This witnesses compilation DURING evaluation. It does not identify
            # the evaluator's callee, all its reads/writes, or its prerequisites.
            stack[-1]['compiled_during'].append(e['payload']['function_id'])
        elif kind == 'load-initializer-emitted':
            load_effects.append({'sequence': seq, 'module': module(e['source']),
                                 'source_position': e['source_position'],
                                 'preview': e['payload']})
    if stack:
        raise ValueError('initializer did not return')
    callbacks = [(group['group'], index, fn) for group in image['startup_groups']
                 for index, fn in enumerate(group['functions'])]
    startup, pending = [], None
    for e in read_events(cold):
        if e['kind'] == 'startup-enter':
            if pending is not None or len(startup) >= len(callbacks):
                raise ValueError('unexpected startup entry')
            group, index, fn = callbacks[len(startup)]
            if e['payload'] != fn['name']:
                raise ValueError('startup order/identity differs from image')
            pending = {'group': group, 'index': index, 'name': fn['name'],
                       'function': fn['function'], 'enter': e['sequence']}
        elif e['kind'] == 'startup-return':
            if pending is None or e['payload'] != pending['name']:
                raise ValueError('startup return without matching entry')
            startup.append({**pending, 'return': e['sequence']})
            pending = None
    if pending or len(startup) != len(callbacks):
        raise ValueError('startup callback completion missing')
    return {'compile': compile_effects, 'load': load_effects, 'startup': startup}
