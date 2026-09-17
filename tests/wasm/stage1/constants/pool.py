"""Identity-preserving D1 pool graph linker. No target writes or code installation."""
from dataclasses import dataclass
from encode import Encoder, require


def name(value):
    require(type(value) is str and bool(value), 'empty or invalid identity')
    return value


def shape(value, keys):
    require(type(value) is dict and set(value) == set(keys), 'invalid graph record')


@dataclass(frozen=True)
class Materialized:
    base: int
    image: bytes
    roots: tuple
    objects: tuple  # (identity, tagged address), in source order.


@dataclass(frozen=True)
class Pool:
    # Internal linker product, not an authenticated external serialization format.
    image: bytes
    objects: tuple  # (identity, raw offset, tag).
    fixups: tuple  # (word offset, target raw offset, tag).
    roots: tuple  # (is-relative, raw offset or immediate word, tag).
    external_words: tuple

    def at(self, base, limit=2**32):
        require(type(base) is int and base >= 8 and base % 8 == 0, 'invalid pool base')
        require(type(limit) is int and 0 <= limit <= 2**32, 'invalid memory limit')
        end = base + len(self.image)
        require(base < limit and end <= limit, 'pool exceeds memory')
        # External objects must not alias storage owned by this pool.
        for word, tag in self.external_words:
            require(not base <= word - tag < end, 'external object overlaps pool')
        image = bytearray(self.image)
        for where, target, tag in self.fixups:
            image[where:where+4] = (base + target + tag).to_bytes(4, 'little')
        roots = tuple(base + value + tag if relative else value
                      for relative, value, tag in self.roots)
        return Materialized(base, bytes(image), roots,
                            tuple((ident, base + offset + tag) for ident, offset, tag in self.objects))


def compile_pool(graph, symbols=None, max_bytes=16*1024*1024):
    """Build a relocatable plan from explicit identities, never structural equality.

    Graph v1: objects [{id, value}], roots [value]. Values are encoder immediates,
    {ref: id}, or {symbol: owner-key}. Heap nodes add cons {car,cdr} and general
    vector {elements}; pointer-free heap nodes use the encoder descriptors.
    Symbol values are trusted owner-issued tagged words, not names resolved here.
    """
    shape(graph, ('version', 'objects', 'roots'))
    require(type(graph['version']) is int and graph['version'] == 1, 'unsupported graph version')
    require(type(graph['objects']) is list and type(graph['roots']) is list, 'invalid graph lists')
    symbols = {} if symbols is None else symbols
    require(type(symbols) is dict, 'invalid symbol registry')
    enc = Encoder(max_bytes=max_bytes)
    for key, word in symbols.items():
        name(key)
        require(type(word) is int and 0 <= word < 2**32 and word & 7 == enc.c['fulltag-misc'],
                'invalid owner symbol word')
    entries, indices, image, pending = [], {}, bytearray(), []
    cons = enc.objects['cons']
    cons_offsets = {c['name']: c['raw_offset'] for c in cons['cells']}
    # Allocate every declared object, including cold/unreached function pools.
    for row in graph['objects']:
        shape(row, ('id', 'value'))
        ident = name(row['id'])
        require(ident not in indices, 'duplicate object identity')
        spec = row['value']
        require(type(spec) is dict and type(spec.get('kind')) is str, 'invalid object descriptor')
        offset = len(image)
        kind = spec['kind']
        if kind == 'cons':
            shape(spec, ('kind', 'car', 'cdr'))
            data, tag = bytes(cons['size_bytes']), enc.c['fulltag-cons']
            fields = [(cons_offsets['cdr'], spec['cdr']), (cons_offsets['car'], spec['car'])]
        elif kind == 'general-vector':
            shape(spec, ('kind', 'elements'))
            require(type(spec['elements']) is list, 'invalid vector elements')
            count = len(spec['elements'])
            enc.extent(count, count*4)
            data = enc.object('simple-vector', count, bytes(count*4)).image
            tag = enc.c['fulltag-misc']
            fields = [(4+4*i, value) for i, value in enumerate(spec['elements'])]
        else:
            encoded = enc.encode(spec)
            require(encoded.immediate is None, 'object identity requires heap object')
            data, tag, fields = encoded.image, enc.c['fulltag-misc'], []
        require(offset + len(data) <= max_bytes, 'aggregate pool exceeds byte budget')
        indices[ident] = (offset, tag)
        entries.append((ident, offset, tag))
        image.extend(data)
        pending.extend((offset + where, value) for where, value in fields)

    external = set()
    def resolve(value):
        require(type(value) is dict, 'invalid pool value')
        if 'ref' in value:
            shape(value, ('ref',))
            ident = name(value['ref'])
            require(ident in indices, 'unknown object reference')
            offset, tag = indices[ident]
            return True, offset, tag
        if 'symbol' in value:
            shape(value, ('symbol',))
            key = name(value['symbol'])
            require(key in symbols, 'unresolved owner symbol')
            word = symbols[key]
            external.add((word, enc.c['fulltag-misc']))
            return False, word, 0
        encoded = enc.encode(value)
        require(encoded.immediate is not None, 'heap literal requires explicit identity')
        if value['kind'] == 'singleton':
            # NIL and T are external canonical objects, not pool allocations.
            word = encoded.immediate
            external.add((word, word & 7))
        return False, encoded.immediate, 0

    fixups = []
    for where, value in pending:
        relative, target, tag = resolve(value)
        if relative:
            fixups.append((where, target, tag))
        else:
            image[where:where+4] = target.to_bytes(4, 'little')
    roots = tuple(resolve(value) for value in graph['roots'])
    return Pool(bytes(image), tuple(entries), tuple(fixups), roots, tuple(sorted(external)))
