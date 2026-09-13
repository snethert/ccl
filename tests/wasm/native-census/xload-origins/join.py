"""Bind xload queue insertions to boot execution, FASLs and source contexts."""
import gzip
import hashlib
import json
from pathlib import Path


def sha(data): return hashlib.sha256(data).hexdigest()
def events(path):
    with gzip.open(path, 'rt') if path.suffix == '.gz' else path.open() as f:
        return [json.loads(s) for s in f]

def relative(path, root):
    path = Path(path).resolve(); root = Path(root).resolve()
    if root not in path.parents: raise ValueError('PATH_SCOPE')
    return str(path.relative_to(root))

def source_name(logical):
    if not isinstance(logical, str) or not logical.startswith('ccl:level-0;') or not logical.endswith('.lisp.newest'):
        raise ValueError('SOURCE_NAME')
    return logical[4:-7].replace(';', '/')


def join(origins, boot, source, fasls, source_overrides=None):
    def require(ok, reason):
        if not ok: raise ValueError(reason)
    source_overrides = source_overrides or {}
    require(set(origins) == {'version', 'target_nil', 'paths', 'entries', 'host_queue', 'image_queue'} and origins['version'] == 1, 'ORIGIN_SCHEMA')
    entries = origins['entries']; queue = boot[0]['original_cold_queue']
    require(len(entries) == len(queue) == len(origins['host_queue']) == len(origins['image_queue']) and len(entries) > 0, 'QUEUE_COUNT')
    require([e['position'] for e in entries] == list(range(1, len(queue) + 1)), 'QUEUE_POSITION')
    require([e['target_function'] for e in entries] == origins['host_queue'] == origins['image_queue'], 'SAVED_QUEUE_ORDER')
    require(len(set(origins['image_queue'])) == len(queue), 'DISTINCT_THUNKS')
    require([e['payload']['function'] for e in boot if e['kind'] == 'cold-enter'] == queue and
            [e['payload']['function'] for e in boot if e['kind'] == 'cold-return'] == queue, 'BOOT_QUEUE_EXECUTION')
    objects = {r['object']['id']: r['object'] for r in boot if r['kind'] == 'object'}
    require(all(objects[i]['kind'] == 'function' for i in queue), 'BOOT_FUNCTION_IDENTITY')
    paths = [relative(p, source) for p in origins['paths']]
    require(len(paths) == len(set(paths)) and all(p in fasls for p in paths), 'XLOAD_INPUTS')
    require(paths == sorted(paths, key=lambda p: (not p.startswith('level-0/X86/'), p)), 'XLOAD_LOAD_ORDER')
    position = {p: i for i, p in enumerate(paths)}; result = []; files = {}; sources = {}; last = None
    for entry, function in zip(entries, queue):
        require(set(entry) == {'position', 'file', 'opcode_offset', 'target_function', 'source_file', 'location_word', 'location'}, 'ENTRY_FIELDS')
        name = relative(entry['file'], source)
        require(name in position, 'ENTRY_MODULE')
        data = (source / name).read_bytes()
        require(sha(data) == fasls[name], 'FASL_IDENTITY')
        offset = entry['opcode_offset']
        require(type(offset) is int and 0 <= offset < len(data) and data[offset] == 4, 'INITIALIZER_OPCODE')
        key = (position[name], offset)
        require(last is None or last < key, 'INSERTION_ORDER'); last = key
        src = source_name(entry['source_file'])
        require(src == str(Path(name).with_suffix('.lisp')), 'SOURCE_MODULE_JOIN')
        content = source_overrides.get(src, source / src).read_bytes()
        files[name] = {'path': name, 'sha256': fasls[name]}
        sources[src] = {'path': src, 'sha256': sha(content), 'bytes': len(content)}
        loc = entry['location']; context = None
        require((loc is None) == (entry['location_word'] in (None, origins['target_nil'])), 'SOURCE_LOCATION_PRESENCE')
        if loc is not None:
            require(set(loc) == {'address','header','words','filename','range_encoding','range_words','start','end'}, 'LOCATION_FIELDS')
            require(loc['header'] == (4 << 8 | 54) and len(loc['words']) == 4, 'SOURCE_NOTE_LAYOUT')
            require(loc['address'] == entry['location_word'], 'SOURCE_NOTE_ADDRESS')
            require(loc['filename'] == entry['source_file'], 'SOURCE_NOTE_FILE')
            words = loc['range_words']
            require(all(type(w) is int and w >= 0 and w & 7 == 0 for w in words), 'RANGE_TAGS')
            if loc['range_encoding'] == 'packed':
                require(len(words) == 1 and words[0] == loc['words'][3], 'PACKED_RANGE')
                packed = words[0] >> 3; start = packed >> 14; end = start + (packed & 16383)
            else:
                require(loc['range_encoding'] == 'pair' and len(words) == 2 and loc['words'][3] & 15 == 3, 'PAIR_RANGE')
                start, end = [w >> 3 for w in words]
            require((start, end) == (loc['start'], loc['end']), 'RANGE_DECODE')
            require(0 <= start < end <= len(content), 'SOURCE_RANGE_BOUNDS')
            context = {'start': start, 'end': end, 'sha256': sha(content[start:end]),
                       'text': content[start:end].decode('utf-8')}
        result.append({'position': entry['position'], 'boot_function': function, 'xload_function': entry['target_function'],
                       'fasl': name, 'opcode_offset': offset, 'source': src, 'context': context})
    return {'version': 1, 'status': 'OBSERVED_ORIGINS_NOT_FULL_CENSUS', 'entries': result,
            'fasls': [files[p] for p in paths], 'sources': [sources[p] for p in sorted(sources)],
            'summary': {'initializers': len(result), 'modules': len(sources),
                        'with_source_context': sum(r['context'] is not None for r in result),
                        'without_source_context': [r['position'] for r in result if r['context'] is None]},
            'rule': 'Same pinned FASLs in U1 directory order; each lfuncall reader adds exactly one head cons. U1 reverses once; observed insertion order equals the host final list and the saved target list. Fresh boot drains that queue in order. Source ranges are compiler contexts, not a claim of one form per thunk.'}
