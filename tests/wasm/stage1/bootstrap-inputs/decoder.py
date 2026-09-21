"""Decode UTF-8 FASL strings as data, following U1 $fasl-vstr."""
from fasl import CompilerFasl as Prior, require

class CompilerFasl(Prior):
    def expr(self, depth=0):
        if self.pos < len(self.data) and self.data[self.pos] & 127 in (8, 46):
            require(depth < 64, 'FASL_DEPTH')
            start, raw = self.pos, self.byte()
            op = raw & 127
            self.ops.append({'offset': start, 'opcode': op, 'epush': bool(raw & 128)})
            value = {'double-bits' if op == 8 else 'single-bits': self.take(8 if op == 8 else 4).hex()}
            if raw & 128:
                self.refs.append(value)
                require(len(self.refs) <= self.capacity, 'FASL_TABLE_CAPACITY')
            self.spans[id(value)] = (start, self.pos)
            return value
        if self.pos < len(self.data) and self.data[self.pos] & 127 == 6:
            require(depth < 64, 'FASL_DEPTH')
            start, raw = self.pos, self.byte()
            self.ops.append({'offset': start, 'opcode': 6, 'epush': bool(raw & 128)})
            code = 0
            for shift in range(0, 35, 7):
                b = self.byte()
                code |= (b & 127) << shift
                if b & 128:
                    break
            else:
                raise ValueError('FASL_CHARACTER_COUNT')
            require(code <= 0x10ffff, 'FASL_CHARACTER_RANGE')
            value = {'char': code}
            if raw & 128:
                self.refs.append(value)
                require(len(self.refs) <= self.capacity, 'FASL_TABLE_CAPACITY')
            self.spans[id(value)] = (start, self.pos)
            return value
        if self.pos < len(self.data) and self.data[self.pos] & 127 == 21:
            require(depth < 64, 'FASL_DEPTH')
            start, raw = self.pos, self.byte()
            push = bool(raw & 128)
            self.ops.append({'offset': start, 'opcode': 21, 'epush': push})
            nchars, extra = self.count(), self.count()
            value = self.take(nchars + extra).decode('utf-8')
            require(len(value) == nchars, 'FASL_UTF8_LENGTH')
            if push:
                self.refs.append(value)
                require(len(self.refs) <= self.capacity, 'FASL_TABLE_CAPACITY')
            return value
        return super().expr(depth)
