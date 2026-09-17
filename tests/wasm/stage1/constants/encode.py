"""D1 pointer-free constant payloads; no allocation, graph linking or publication."""
import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCHEMA = ROOT / 'doc/WASM/contracts/wasm32-layout.v1.json'


@dataclass(frozen=True)
class Constant:
    immediate: int | None
    image: bytes  # Includes header and zero alignment padding; empty for immediates.


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def decimal(value):
    require(isinstance(value, str) and re.fullmatch(r'0|-?[1-9][0-9]*', value),
            'integer requires canonical decimal string')
    return int(value)


def bits(value, width):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{%d}' % (width // 4), value),
            'float requires exact-width lowercase hexadecimal bits')
    return int(value, 16).to_bytes(width // 8, 'little')


class Encoder:
    def __init__(self, schema=SCHEMA, max_bytes=16 * 1024 * 1024):
        s = json.loads(Path(schema).read_text())
        require((s['schema'], s['version'], s['word_bytes'], s['endianness'],
                 s['object_alignment']) == ('wasm32-layout', 1, 4, 'little', 8),
                'unsupported layout')
        require(type(max_bytes) is int and 0 <= max_bytes <= 2**32, 'invalid byte budget')
        self.budget = max_bytes
        self.c = {r['name']: r['value'] for r in s['constants']}
        self.tags = {r['name'][7:]: r['value'] for r in s['subtags']
                     if r['disposition'] == 'inherited'}
        self.objects = {r['name']: r for r in s['objects']}

    def extent(self, count, payload_bytes, offset=4):
        require(type(count) is int and 0 <= count < 2**(32 - self.c['num-subtag-bits']),
                'header count overflow')  # D1: 24 count bits in a 32-bit word.
        size = (offset + payload_bytes + 7) & ~7
        require(size <= self.budget and size <= 2**32, 'constant exceeds byte budget')
        return size

    def object(self, kind, count, payload, offset=4):
        size = self.extent(count, len(payload), offset)
        header = (count << self.c['num-subtag-bits']) | self.tags[kind]
        return Constant(None, header.to_bytes(4, 'little') + bytes(offset - 4)
                        + payload + bytes(size - offset - len(payload)))

    def fixnum(self, n):
        require(self.c['target-most-negative-fixnum'] <= n <=
                self.c['target-most-positive-fixnum'], 'not a target fixnum')
        return (n << self.c['fixnum-shift']) & 0xffffffff

    def encode(self, spec):
        require(type(spec) is dict and 'kind' in spec, 'invalid constant descriptor')
        kind = spec['kind']
        require(type(kind) is str, 'invalid constant kind')
        field = 'elements' if kind == 'vector' else 'value'
        expected = {'kind', field} | ({'type'} if kind == 'vector' else set())
        require(set(spec) == expected, 'unknown or missing descriptor fields')
        value = spec[field]
        if kind == 'integer':
            n = decimal(value)
            if self.c['target-most-negative-fixnum'] <= n <= self.c['target-most-positive-fixnum']:
                return Constant(self.fixnum(n), b'')
            # Minimum signed two's-complement limb count, including positive sign limb.
            width = ((n if n >= 0 else ~n).bit_length() + 1 + 31) // 32
            self.extent(width, width * 4)
            return self.object('bignum', width, n.to_bytes(width * 4, 'little', signed=True))
        if kind == 'character':
            self.character(value)
            return Constant((value << self.c['charcode-shift']) | self.tags['character'], b'')
        if kind == 'singleton':
            require(value in ('nil', 't'), 'unknown singleton')
            return Constant(self.c['canonical-nil-value'] + (self.c['t-offset'] if value == 't' else 0), b'')
        if kind in ('single-float', 'double-float'):
            obj = self.objects[kind]
            offset = next(c['raw_offset'] for c in obj['cells'] if c['name'] == 'value')
            return self.object(kind, obj['element_count'], bits(value, 32 if kind == 'single-float' else 64), offset)
        if kind == 'string':
            require(type(value) is list, 'string requires character-code list')
            self.extent(len(value), len(value) * 4)
            for c in value:
                self.character(c)
            return self.object('simple-base-string', len(value), b''.join(c.to_bytes(4, 'little') for c in value))
        require(kind == 'vector', 'unsupported constant kind')
        return self.vector(spec['type'], value)

    @staticmethod
    def character(c):
        # CCL CHAR-CODE-LIMIT is #x110000; preserve its code domain, including surrogates.
        require(type(c) is int and 0 <= c < 0x110000, 'invalid character code')

    def vector(self, kind, values):
        require(type(kind) is str, 'invalid vector type')
        require(type(values) is list, 'vector requires element list')
        numeric = {'s8': (1, True), 'u8': (1, False), 's16': (2, True),
                   'u16': (2, False), 's32': (4, True), 'u32': (4, False),
                   'fixnum': (4, True)}
        floating = {'single-float': (32, 1), 'double-float': (64, 1),
                    'complex-single-float': (32, 2), 'complex-double-float': (64, 2)}
        count = len(values)
        if kind in numeric:
            width, signed = numeric[kind]
            self.extent(count, count * width)
            low, high = (-(1 << (8 * width - 1)), (1 << (8 * width - 1)) - 1) if signed else (0, (1 << (8 * width)) - 1)
            payload = bytearray()
            for v in values:
                n = decimal(v)
                if kind == 'fixnum':
                    # x862-vset unboxes even fixnum-vector elements.
                    self.fixnum(n)  # Validate against target, not host range.
                    payload.extend(n.to_bytes(4, 'little', signed=True))
                else:
                    require(low <= n <= high, 'vector element out of range')
                    payload.extend(n.to_bytes(width, 'little', signed=signed))
            return self.object(kind + '-vector', count, bytes(payload))
        if kind in floating:
            width, parts = floating[kind]
            # x8632-misc-byte-count reserves a pad for all 64/128-bit elements.
            offset = 8 if width * parts >= 64 else 4
            self.extent(count, count * width * parts // 8, offset)
            payload = bytearray()
            for v in values:
                if parts == 2:
                    require(type(v) is list and len(v) == 2, 'complex vector needs real/imaginary bit pair')
                    for component in v:
                        payload.extend(bits(component, width))
                else:
                    payload.extend(bits(v, width))
            return self.object(kind + '-vector', count, bytes(payload), offset)
        require(kind == 'bit', 'unsupported vector type')
        self.extent(count, (count + 7) // 8)
        payload = bytearray((count + 7) // 8)
        for i, bit in enumerate(values):
            require(type(bit) is int and bit in (0, 1), 'invalid bit')
            payload[i // 8] |= bit << (i % 8)
        return self.object('bit-vector', count, bytes(payload))
