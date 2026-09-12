"""Decode the fully printed, evaluated opcode alists; no Lisp evaluation or source scan."""
import re


def read_alist(text):
    # The retained alists contain lists, shared tails, strings, integers and NIL.
    # Accept that grammar only. Never accept unreadable/truncated print output,
    # reader evaluation, arbitrary symbols or unresolved/circular reader labels.
    token = re.compile(r'\s*(#[0-9]+[=#]|[()]|\.|"(?:\\.|[^"\\])*"|-?[0-9]+|(?:COMMON-LISP::?)?NIL)')
    pos, labels, busy = 0, {}, set()

    def peek():
        nonlocal pos
        if not text[pos:].strip():
            return None
        match = token.match(text, pos)
        if not match:
            raise ValueError('unsupported evaluated opcode print syntax at ' + text[pos:pos + 45])
        return match

    def read():
        nonlocal pos
        match = peek()
        if match is None:
            raise ValueError('incomplete opcode alist')
        item = match[1]
        pos = match.end()
        if item == '(':
            result = []
            while True:
                following = peek()
                if following is None:
                    raise ValueError('unterminated opcode list')
                if following[1] == ')':
                    pos = following.end()
                    return result
                if following[1] == '.':
                    if not result:
                        raise ValueError('empty dotted list')
                    pos = following.end()
                    tail = read()
                    end = peek()
                    if not isinstance(tail, list) or end is None or end[1] != ')':
                        raise ValueError('improper opcode alist tail')
                    pos = end.end()
                    return result + tail
                result.append(read())
        if item.startswith('#'):
            ident = int(item[1:-1])
            if item[-1] == '=':
                if ident in labels or ident in busy:
                    raise ValueError('duplicate opcode reader label')
                busy.add(ident)
                labels[ident] = read()
                busy.remove(ident)
                return labels[ident]
            if ident not in labels or ident in busy:
                raise ValueError('unknown/circular opcode reader label')
            return labels[ident]
        if item.startswith('"'):
            return re.sub(r'\\(.)', r'\1', item[1:-1])
        if item.endswith('NIL'):
            return []
        if re.fullmatch(r'-?[0-9]+', item):
            return int(item)
        raise ValueError('unexpected opcode delimiter')

    result = read()
    if peek() is not None or not isinstance(result, list):
        raise ValueError('trailing/non-list opcode alist')
    if any(not isinstance(row, list) or len(row) < 2 or type(row[0]) is not int or
           not isinstance(row[1], str) or not row[1] for row in result):
        raise ValueError('malformed evaluated opcode entry')
    if len({r[0] for r in result}) != len(result):
        raise ValueError('duplicate evaluated opcode number')
    return result


def collect(image):
    return [{'name': v['name'], 'defined': v['defined'], 'attributes': v['attributes'],
             'opcodes': read_alist(v['opcodes']) if v['defined'] else []}
            for v in image['vinsns']]
