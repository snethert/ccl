"""Count static instructions in emitted function bodies, never dynamic costs."""
import collections
import hashlib
import json
from pathlib import Path
import re
import sys


def expressions(wat):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|;;[^\n]*|[()]|[^\s()]+', wat)
    stack, roots = [], []
    for token in tokens:
        if token.startswith(';;'):
            continue
        if token == '(':
            node = []
            (stack[-1] if stack else roots).append(node)
            stack.append(node)
        elif token == ')':
            assert stack
            stack.pop()
        else:
            assert stack
            stack[-1].append(token)
    assert not stack and len(roots) == 1
    return roots[0]


def inspect(build, out):
    out.mkdir(parents=True, exist_ok=True)
    names = {r['wire']:r['name'] for r in json.loads((build/'function-names.json').read_text())}
    units = json.loads((build/'benchmark.records.json').read_text())['units']
    result = []
    for unit in units:
        wat = unit['record'][4]
        tree = expressions(wat)
        body = next(n for n in tree if isinstance(n,list) and n[:2] == ['func','$body'])
        counts = collections.Counter()
        def walk(node):
            if not isinstance(node,list) or not node:
                return
            head = node[0]
            if isinstance(head,str):
                counts[head] += 1
                if head == 'call':
                    counts['call '+node[1]] += 1
                if head == 'i32.store':
                    if 'offset=128' in node[:3]: counts['rootHeadStores'] += 1
                    if node[-1] == ['i32.const','77825']: counts['nilStores'] += 1
            for child in node: walk(child)
        walk(body)
        name = names[unit['name']]
        (out/(unit['name']+'.wat')).write_text(wat)
        result.append(dict(name=name, wire=unit['name'], watSha256=hashlib.sha256(wat.encode()).hexdigest(),
            bodySha256=hashlib.sha256(json.dumps(body).encode()).hexdigest(),
            calls={k:v for k,v in counts.items() if k.startswith('call ')},
            counts={k:counts[k] for k in ['loop','call_indirect','return_call_indirect','i32.load','i32.store',
                'rootHeadStores','nilStores','f32.add','f64.add','i32.add','if']}))
    value = dict(kind='SOURCE INSPECTION', functions=result,
        scope='Static counts in $body only, including its prologue/epilogue and untaken branches. Helpers are excluded. Counts are not dynamic instruction counts or machine instructions. rootHeadStores counts stores at TCR offset 128; nilStores counts constant NIL stores. Typed loops are compiler output, not presumed unboxed.')
    (out/'code-shapes.json').write_text(json.dumps(value,indent=2)+'\n')
    return value


if __name__ == '__main__':
    inspect(Path(sys.argv[1]),Path(sys.argv[2]))
