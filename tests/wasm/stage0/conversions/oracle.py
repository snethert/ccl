"""Literal case expectations plus independent Python integer and set models."""
import json
from collections import Counter
from binary import decode, require

MASK = (1 << 32) - 1
MIN, MAX = -(1 << 29), (1 << 29) - 1


def signed(n):
    n &= MASK
    return n if n < 1 << 31 else n - (1 << 32)


def check(observed, cases, bundle):
    abi = json.loads((bundle / 'abi.json').read_text())
    mapping = decode((bundle / 'module.wasm').read_bytes(), abi)
    require(mapping == json.loads((bundle / 'map.json').read_text()), 'RETAINED_BINARY_MAP')
    bias = json.loads((bundle / 'options.json').read_text())['bias']
    require(observed['status'] == 'OBSERVED' and observed['instantiated'] and
            observed['scope'] == 'HAND-BUILT WASM CONVERSIONS', 'EXECUTION_SCOPE')
    require(len(observed['records']) == len(cases) and len({c['name'] for c in cases}) == len(cases), 'CASE_BOUND')
    memory, words = 65536, {}
    issued, slots = set(), set()
    next_id, reserve, capacity = 0, range(0), 0
    refusals = Counter()
    for c, row in zip(cases, observed['records']):
        reason = 'CASE ' + c['name']
        op = c['op']
        args = [mapping['reserved_end'] if a == '$reserved' else a for a in c['args']]
        require((row['name'], row['family'], row['args']) == (c['name'], c['family'], args), reason)
        expected = c['expected'].copy()
        if c.get('bias_result'):
            expected[0] += bias - 7
        value, error = 0, 0
        host_refusal = False
        if op != 'grow':
            params = abi['exports'][op]['params']
            require(len(params) == len(args), 'CASE_ARITY')
            for a, kind in zip(args, params):
                low, high = (0 if kind == 'u32' else -(1 << 31)), ((1 << 31) - 1 if kind == 'i32' else MASK)
                if type(a) is not int or not low <= a <= high:
                    host_refusal = True
        if host_refusal:
            error = 13
        elif op == 'box':
            if MIN <= args[0] <= MAX:
                value = signed(args[0] * 4)
            else:
                error = 1
        elif op == 'unbox':
            word = signed(args[0])
            if word % 4:
                error = 2
            else:
                value = word // 4
        elif op == 'raw_as_fixnum':
            if args[0] <= MAX:
                value = args[0] * 4
            else:
                error = 1
        elif op == 'tag':
            raw, tag = args
            error = 2 if tag not in (1, 6) else 3 if raw % 8 else 0
            value = raw + tag if not error else 0
        elif op == 'untag':
            word = args[0] & MASK
            error = 0 if word % 8 in (1, 6) else 2
            value = word - word % 8 if not error else 0
        elif op == 'effective':
            total = (args[0] & MASK) + args[1]
            if 0 <= total <= MASK:
                value = total
            else:
                error = 4
        elif op == 'grow':
            value = memory // 65536
            memory += args[0] * 65536
            require(row.get('growth') == dict(before_bytes=65536, after_bytes=2147549184, old_view_detached=True), reason)
        elif op in ('cons_store', 'header_store', 'cons_car', 'cons_cdr', 'header_load'):
            writing = op.endswith('_store')
            tag = 6 if op.startswith('header') else 1
            ptr = args[0] & MASK
            raw = ptr if writing else ptr - ptr % 8
            if not writing and ptr % 8 != tag:
                error = 2
            elif raw % 8:
                error = 3
            elif not 4096 <= raw <= memory - 8:
                error = 4
            elif writing:
                data = (args[2], args[1]) if op == 'cons_store' else (args[1], 287454020)
                words[raw], words[raw + 4] = map(signed, data)
                value = raw + tag
                raw_bytes = b''.join((n & MASK).to_bytes(4, 'little') for n in data)
                require(row.get('bytes') == list(raw_bytes), reason)
            else:
                value = words[raw + (4 if op == 'cons_car' else 0)]
        elif op == 'ids_reset':
            start, lo, hi = args
            if not (0 <= start <= MAX + 1 and 0 <= lo <= hi <= MAX + 1):
                error = 1
            else:
                issued, next_id, reserve = set(), start, range(lo, hi)
                value = start
        elif op == 'id_alloc':
            candidate = reserve.stop if next_id in reserve else next_id
            if candidate > MAX:
                error = 6
            else:
                issued.add(candidate)
                next_id = candidate + 1
                value = candidate * 4
        elif op == 'id_encode':
            if 0 <= args[0] <= MAX:
                value = args[0] * 4
            else:
                error = 1
        elif op == 'id_valid':
            word = signed(args[0])
            if word < 0 or word % 4:
                error = 2
            elif word // 4 not in issued:
                error = 5
            else:
                value = word // 4
        elif op == 'slots_reset':
            cap, bound = args
            if not (0 <= cap <= mapping['table'][0] and 0 <= bound <= mapping['table'][0]):
                error = 7
            else:
                capacity, slots, value = cap, set(), cap
        elif op.startswith('slot_'):
            reserved = {r['slot'] for r in mapping['reservations']}
            available = set(range(capacity)) - reserved
            if op == 'slot_alloc':
                free = available - slots
                if not free:
                    error = 6
                else:
                    index = min(free)
                    sig, role = args
            else:
                index, kind = args[:2]
                if kind != 3:
                    error = 9
                elif index not in range(capacity):
                    error = 7
                elif index in reserved:
                    error = 8
                if op == 'slot_install':
                    sig, role = args[2:]
            if not error:
                if op in ('slot_alloc', 'slot_install'):
                    error = 10 if sig != 1 else 11 if role != 1 else 0
                    if not error:
                        slots.add(index)
                        value = index
                elif op == 'slot_call':
                    if index not in slots:
                        error = 12
                    else:
                        value = signed(args[2] + bias)
        else:
            raise ValueError('UNKNOWN_CASE_OPERATION')
        require([value, error] == expected, 'LITERAL_EXPECTATION ' + c['name'])
        require('error' not in row and row['pair'] == expected and row['called'] == (not host_refusal), reason)
        engine = None if host_refusal else [signed(value), error]
        require(row['engine_pair'] == engine, reason)
        refusals[str(error)] += 1
    require(observed['final_memory_bytes'] == 2147549184, 'REAL_HIGH_MEMORY')
    return dict(status='PASS',cases=len(cases),families=dict(Counter(c['family'] for c in cases)),
                refusal_counts=dict(sorted(refusals.items())),memory_bytes=memory,registered_slots=mapping['reservations'])
