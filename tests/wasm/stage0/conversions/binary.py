"""Bounded interface/element decoder; code bodies are validated by the engine.

This reads final bytes independently of the WAT producer. It is not a general
Wasm validator and does not claim to interpret executable instructions.
"""
import hashlib


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, size):
        require(0 <= size <= len(self.data) - self.pos, 'BINARY_TRUNCATED')
        b = self.data[self.pos:self.pos + size]
        self.pos += size
        return b

    def byte(self):
        return self.take(1)[0]

    def leb(self, signed=False):
        n = 0
        for i in range(5):
            b = self.byte()
            n |= (b & 127) << (7 * i)
            if not b & 128:
                if signed and b & 64:
                    n -= 1 << (7 * (i + 1))
                require(-(1 << 31) <= n < (1 << 31) if signed else 0 <= n < (1 << 32), 'BINARY_INTEGER')
                return n
        raise ValueError('BINARY_LEB_BOUND')

    def vec(self, fn):
        n = self.leb()
        require(n <= 128, 'BINARY_VECTOR_BOUND')
        return [fn() for _ in range(n)]

    def name(self):
        n = self.leb()
        require(n <= 64, 'BINARY_NAME_BOUND')
        return self.take(n).decode('utf-8')

    def limits(self):
        require(self.byte() == 1, 'BINARY_LIMIT_KIND')
        return [self.leb(), self.leb()]

    def constant(self):
        require(self.byte() == 0x41, 'BINARY_INIT_OPCODE')
        value = self.leb(True)
        require(self.byte() == 0x0b, 'BINARY_INIT_END')
        return value

    def end(self):
        require(self.pos == len(self.data), 'BINARY_TRAILING_BYTES')


def decode(data, abi):
    r = Reader(data)
    require(r.take(8) == b'\0asm\x01\0\0\0', 'BINARY_MAGIC')
    types, indices, exports, reservations, declarations, bodies = [], [], {}, [], [], []
    sections = []
    while r.pos < len(data):
        ident = r.byte()
        require(not sections or ident > sections[-1], 'BINARY_SECTION_ORDER')
        sections.append(ident)
        s = Reader(r.take(r.leb()))
        if ident == 1:
            def value_type():
                b = s.byte()
                require(b in (0x7f, 0x7e), 'BINARY_VALUE_TYPE')
                return 'i32' if b == 0x7f else 'i64'

            def signature():
                require(s.byte() == 0x60, 'BINARY_TYPE')
                return '(' + ','.join(s.vec(value_type)) + ')->(' + ','.join(s.vec(value_type)) + ')'
            types = s.vec(signature)
        elif ident == 3:
            indices = s.vec(s.leb)
            require(all(i < len(types) for i in indices), 'BINARY_TYPE_INDEX')
        elif ident == 4:
            require(s.leb() == 1 and s.byte() == 0x70, 'BINARY_TABLE')
            table = s.limits()
        elif ident == 5:
            require(s.leb() == 1, 'BINARY_MEMORY')
            memory = s.limits()
        elif ident == 6:
            def global_value():
                require(s.take(2) == b'\x7f\x01', 'BINARY_GLOBAL')
                return s.constant()
            s.vec(global_value)
        elif ident == 7:
            def export():
                name, kind, index = s.name(), s.byte(), s.leb()
                require(name not in exports, 'BINARY_DUPLICATE_EXPORT')
                if kind == 0:
                    require(index < len(indices), 'BINARY_EXPORT_INDEX')
                    exports[name] = dict(index=index, signature=types[indices[index]])
                else:
                    require(kind == 2 and index == 0 and name == 'memory', 'BINARY_EXPORT_KIND')
            s.vec(export)
        elif ident == 9:
            def element():
                mode = s.leb()
                if mode == 0:
                    base = s.constant()
                    for offset, function in enumerate(s.vec(s.leb)):
                        require(0 <= base + offset < table[0] and function < len(indices), 'BINARY_ELEMENT_INDEX')
                        reservations.append(dict(slot=base + offset, function=function, signature=types[indices[function]]))
                else:
                    require(mode == 3 and s.byte() == 0, 'BINARY_ELEMENT_KIND')
                    declarations.extend(s.vec(s.leb))
            s.vec(element)
        elif ident == 10:
            bodies = s.vec(lambda: hashlib.sha256(s.take(s.leb())).hexdigest())
            require(len(bodies) == len(indices), 'BINARY_BODY_COUNT')
        else:
            raise ValueError('BINARY_UNSUPPORTED_SECTION')
        s.end()
    require(sections == [1, 3, 4, 5, 6, 7, 9, 10], 'BINARY_SECTION_SET')
    require(set(exports) == set(abi['exports']), 'BINARY_EXPORT_SET')
    for name, entry in abi['exports'].items():
        signature = '(' + ','.join('i32' for _ in entry['params']) + ')->(i32,i32)'
        require(exports[name]['signature'] == signature, 'BINARY_EXPORT_SIGNATURE ' + name)
    require(memory == [abi['memory']['initial_pages'], abi['memory']['maximum_pages']], 'BINARY_MEMORY_LIMITS')
    require(table == [abi['table']['initial'], abi['table']['maximum']], 'BINARY_TABLE_LIMITS')
    reservations.sort(key=lambda x: x['slot'])
    require(reservations and [x['slot'] for x in reservations] == list(range(len(reservations))), 'BINARY_RESERVED_PREFIX')
    require(all(x['signature'] == abi['entry']['signature'] for x in reservations), 'BINARY_RESERVED_SIGNATURE')
    require(len(declarations) == 1 and declarations[0] < len(indices) and
            types[indices[declarations[0]]] == abi['entry']['signature'], 'BINARY_INSTALLABLE_SIGNATURE')
    return dict(version=1, binary_sha256=hashlib.sha256(data).hexdigest(), exports=exports,
                memory=memory, table=table, reservations=reservations, reserved_end=len(reservations),
                installable_function=declarations[0], bodies=bodies)
