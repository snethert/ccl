"""Deterministic corpus for the checked floating-point operations with oracle expectations."""
import json
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ieee import DOUBLE, SINGLE, STATUS, expected, to_single, bits64, from_bits64, bits32, from_bits32, condition_of, DEFAULT_MASK

INF, NAN = math.inf, math.nan
MIN_SUB = 2.0 ** -1074; MIN_NORMAL = 2.0 ** -1022; MAX = (2 - 2 ** -52) * 2.0 ** 1023
NAMED = [
    ('add-inexact-tenths', 'add', 0.1, 0.2), ('add-halfulp-tie', 'add', 1.0, 2 ** -53), ('add-exact', 'add', 1.5, 2.25), ('add-overflow', 'add', 1e308, 1e308),
    ('add-inf-minus-inf', 'add', INF, -INF), ('add-inf-finite', 'add', INF, 1.0), ('add-nan-propagates', 'add', NAN, 1.0), ('add-max-ulp', 'add', MAX, 2.0 ** 970),
    ('add-subnormals-exact', 'add', 3 * MIN_SUB, 5 * MIN_SUB), ('add-cancel-to-zero', 'add', 1e-310, -1e-310), ('add-negzero', 'add', -0.0, -0.0),
    ('sub-sterbenz', 'sub', 1.0, 0.75), ('sub-inf-inf', 'sub', INF, INF), ('sub-inexact', 'sub', 1e16, 1.5),
    ('mul-exact-powers', 'mul', 2.0 ** 1000, 2.0 ** -10), ('mul-large-inexact', 'mul', (1 + 2 ** -40) * 2.0 ** 1000, 1 + 2 ** -30), ('mul-overflow', 'mul', 1e300, 1e10),
    ('mul-inf-zero', 'mul', INF, 0.0), ('mul-inf-finite', 'mul', -INF, 2.0), ('mul-tenths', 'mul', 3.0, 0.1), ('mul-zero-exact', 'mul', 0.0, 1e300),
    ('mul-tiny-exact', 'mul', 2.0 ** -537, 2.0 ** -537), ('mul-tiny-inexact', 'mul', (1 + 2 ** -30) * 2.0 ** -537, (1 + 2 ** -30) * 2.0 ** -537), ('mul-tiny-to-zero', 'mul', 1e-200, 1e-200),
    ('mul-min-normal-boundary', 'mul', MIN_NORMAL, 1 + 2 ** -52), ('mul-just-normal-inexact', 'mul', (1 + 2 ** -20) * 2.0 ** -500, (1 + 2 ** -20) * 2.0 ** -500), ('mul-tiny-halfway', 'mul', 3 * 2.0 ** -1000, 2.0 ** -75),
    ('div-by-zero', 'div', 5.0, 0.0), ('div-by-negzero', 'div', 5.0, -0.0), ('div-neg-by-zero', 'div', -5.0, 0.0), ('div-zero-by-zero', 'div', 0.0, 0.0), ('div-inf-by-zero', 'div', INF, 0.0),
    ('div-inf-by-inf', 'div', INF, INF), ('div-by-inf', 'div', 1.0, INF), ('div-exact', 'div', 6.0, 3.0), ('div-third', 'div', 1.0, 3.0), ('div-overflow', 'div', 1e308, 1e-10),
    ('div-tiny-inexact', 'div', 1e-308, 1e10), ('div-tiny-exact', 'div', 2.0 ** -1000, 2.0 ** 30), ('div-tiny-large-divisor', 'div', 1.0, 2.0 ** 1023 * 1.5), ('div-zero-dividend', 'div', 0.0, 7.0),
    ('div-to-zero', 'div', MIN_SUB, 4.0), ('div-nan', 'div', NAN, 0.0), ('div-subnormal-dividend', 'div', 2.0 ** -1050, 3.0), ('div-subnormal-exact', 'div', 6 * MIN_SUB, 2.0 ** -100),
    ('mul-subnormal-operand-inexact', 'mul', 3 * MIN_SUB, 1e20), ('mul-subnormal-operand-exact', 'mul', 5 * MIN_SUB, 2.0 ** 100), ('mul-subnormal-second', 'mul', 1e20, 3 * MIN_SUB),
    ('mul-max-by-one', 'mul', MAX, 1.0), ('mul-max-by-half', 'mul', MAX, 0.5), ('mul-one-by-max', 'mul', 1.0, MAX), ('mul-negmax-by-one', 'mul', -MAX, 1.0), ('mul-max-inexact', 'mul', MAX, 0.7),
    ('mul-near-max-rounds-up-split', 'mul', (2 - 2 ** -52) * 2.0 ** 1000, 1.0), ('mul-near-max-exact', 'mul', (1 + 2 ** -30) * 2.0 ** 1020, 0.25), ('mul-near-max-inexact', 'mul', (1 + 2 ** -30) * 2.0 ** 1020, 1 + 2 ** -40),
    ('div-max-by-one', 'div', MAX, 1.0), ('div-max-by-three', 'div', MAX, 3.0), ('div-max-by-negone', 'div', MAX, -1.0), ('div-one-by-max', 'div', 1.0, MAX), ('sqrt-near-max', 'sqrt', (1 + 2 ** -30) * 2.0 ** 1022, None),
    ('add-max-half-ulp', 'add', MAX, 2.0 ** 969), ('sub-max-max', 'sub', MAX, MAX), ('add-negmax-negmax', 'add', -MAX, -MAX),
    # the normal/subnormal boundary: results exactly 2^-1022 that are tiny after rounding (the R2 review's case), the tie, and neighbours
    ('mul-boundary-underflow', 'mul', MIN_NORMAL, 1 - 2 ** -53), ('mul-boundary-underflow-swapped', 'mul', 1 - 2 ** -53, MIN_NORMAL),
    ('mul-boundary-underflow-neg-a', 'mul', -MIN_NORMAL, 1 - 2 ** -53), ('mul-boundary-underflow-neg-b', 'mul', MIN_NORMAL, -(1 - 2 ** -53)), ('mul-boundary-underflow-neg-both', 'mul', -MIN_NORMAL, -(1 - 2 ** -53)),
    ('mul-boundary-inside', 'mul', MIN_NORMAL * (1 + (2 ** 25 + 1) * 2.0 ** -52), 1 - (2 ** 25 + 1) * 2.0 ** -52),
    ('mul-boundary-tie', 'mul', MIN_NORMAL * (1 + 2 ** -27), 1 - 2 ** -27), ('mul-boundary-above-tie', 'mul', MIN_NORMAL * (1 + (2 ** 25 - 1) * 2.0 ** -52), 1 - (2 ** 25 - 1) * 2.0 ** -52),
    ('mul-boundary-below-half', 'mul', MIN_NORMAL * (1 + 2 ** -52), 1 - 3 * 2 ** -53), ('mul-boundary-just-below-normal', 'mul', MIN_NORMAL * (1 + 2 ** -52), 1 - 2 ** -52),
    ('mul-boundary-exact', 'mul', MIN_NORMAL, 1.0), ('mul-boundary-exact-subnormal', 'mul', MIN_NORMAL - MIN_SUB, 1.0),
    ('div-boundary-underflow', 'div', 1 - 2 ** -53, 2.0 ** 1022), ('div-boundary-underflow-scaled-dividend', 'div', (1 - 2 ** -53) * 2.0 ** -1000, 2.0 ** 22),
    ('div-boundary-underflow-neg', 'div', -(1 - 2 ** -53), 2.0 ** 1022), ('div-boundary-underflow-neg-divisor', 'div', 1 - 2 ** -53, -(2.0 ** 1022)),
    ('div-boundary-exact', 'div', 1.0, 2.0 ** 1022), ('div-boundary-exact-subnormal', 'div', 1 - 2 ** -52, 2.0 ** 1022), ('div-boundary-tie-below', 'div', 1 - 3 * 2 ** -53, 2.0 ** 1022),
    ('div-boundary-above-inexact', 'div', MIN_NORMAL * (1 + 2 ** -51), 1 + 2 ** -52), ('div-boundary-below-inexact', 'div', MIN_NORMAL * (1 + 2 ** -52), 1 + 2 ** -51),
    ('sqrt-exact', 'sqrt', 4.0, None), ('sqrt-two', 'sqrt', 2.0, None), ('sqrt-negative', 'sqrt', -1.0, None), ('sqrt-negzero', 'sqrt', -0.0, None), ('sqrt-inf', 'sqrt', INF, None),
    ('sqrt-min-subnormal', 'sqrt', MIN_SUB, None), ('sqrt-subnormal-square', 'sqrt', 2.0 ** -1000, None), ('sqrt-subnormal-inexact', 'sqrt', 3 * MIN_SUB, None), ('sqrt-nan', 'sqrt', NAN, None),
    ('sqrt-max', 'sqrt', MAX, None), ('sqrt-tenth', 'sqrt', 0.1, None),
    # comparisons: the hardware compare (fcmped, comisd) raises invalid for any NaN operand; Wasm compares are quiet
    ('compare-ordered', 'compare', 1.0, 2.0), ('compare-reversed', 'compare', 2.0, 1.0), ('compare-equal', 'compare', 1.5, 1.5), ('compare-nan-left', 'compare', NAN, 1.0),
    ('compare-nan-right', 'compare', 1.0, NAN), ('compare-nan-both', 'compare', NAN, NAN), ('compare-inf', 'compare', -INF, INF), ('compare-zeros', 'compare', -0.0, 0.0),
    ('compare-subnormal', 'compare', MIN_SUB, MIN_NORMAL), ('compare-max-inf', 'compare', MAX, INF),
    ('trunc-nan', 'trunc', NAN, None), ('trunc-inf', 'trunc', INF, None), ('trunc-fixnum-max', 'trunc', 2.0 ** 29 - 1, None), ('trunc-fixnum-overflow', 'trunc', 2.0 ** 29, None),
    ('trunc-fixnum-min', 'trunc', -(2.0 ** 29), None), ('trunc-fixnum-underflow', 'trunc', -(2.0 ** 29) - 1, None), ('trunc-fraction', 'trunc', 3.7, None), ('trunc-negative-fraction', 'trunc', -3.7, None),
    ('trunc-half', 'trunc', 0.5, None), ('trunc-huge', 'trunc', 1e300, None), ('trunc-negzero', 'trunc', -0.0, None),
    ('add32-overflow', 'add32', 3e38, 3e38), ('add32-inf-inf', 'add32', INF, -INF), ('add32-nan', 'add32', NAN, 1.0), ('add32-finite', 'add32', 0.1, 0.2),
    ('mul32-overflow', 'mul32', 1e20, 1e20), ('mul32-inf-zero', 'mul32', INF, 0.0), ('mul32-finite', 'mul32', 3.0, 0.1),
    ('div32-by-zero', 'div32', 5.0, 0.0), ('div32-zero-by-zero', 'div32', 0.0, 0.0), ('div32-overflow', 'div32', 1e30, 1e-10), ('div32-finite', 'div32', 1.0, 3.0), ('div32-inf-by-zero', 'div32', INF, 0.0),
]


class LCG:
    def __init__(self, seed): self.state = seed & 0xffffffffffffffff
    def next(self):
        self.state = (self.state * 6364136223846793005 + 1442695040888963407) & 0xffffffffffffffff
        return self.state >> 11
    def choice(self, n): return self.next() % n


def random_double(g):
    kind = g.choice(16)
    if kind == 0: return [0.0, -0.0, INF, -INF, NAN][g.choice(5)]
    if kind == 1: return from_bits64(g.next() % (1 << 52) | (g.choice(2) << 63))          # subnormal
    if kind == 2: return float(g.choice(2001) - 1000)                                       # small integer
    if kind == 3: return (-1.0 if g.choice(2) else 1.0) * 2.0 ** (g.choice(2046) - 1022)    # power of two
    if kind == 4: return (-1.0 if g.choice(2) else 1.0) * (1 + g.choice(1 << 20) / 2.0 ** 20) * 2.0 ** (g.choice(120) - 1080)  # near the subnormal boundary
    if kind == 5: return (-1.0 if g.choice(2) else 1.0) * (1 + g.choice(1 << 20) / 2.0 ** 20) * 2.0 ** (990 + g.choice(34))       # near the largest exponent
    if kind == 6: return (-1.0 if g.choice(2) else 1.0) * (1 + g.choice(8) / 8.0) * 2.0 ** (g.choice(8) - 4)                          # small exact multiplier
    exponent = g.choice(2046) + 1
    return from_bits64((g.next() % (1 << 52)) | (exponent << 52) | (g.choice(2) << 63))


def random_single(g):
    kind = g.choice(12)
    if kind == 0: return [0.0, -0.0, INF, -INF, NAN][g.choice(5)]
    if kind == 1: return from_bits32(g.next() % (1 << 23) | (g.choice(2) << 31))
    exponent = g.choice(254) + 1
    return from_bits32((g.next() % (1 << 23)) | (exponent << 23) | (g.choice(2) << 31))


MASKS = {'default': DEFAULT_MASK, 'all': 31, 'none': 0, 'inexact-only': 16, 'underflow-only': 8, 'all-but-overflow': 27, 'invalid-only': 1}


def expected_case(op, a, b):
    if op == 'compare':
        return (STATUS['invalid'] if (a != a or b != b) else STATUS['exact']), None, None
    if op == 'trunc':
        if a != a or a in (INF, -INF): return STATUS['invalid'], None, None
        t = math.trunc(a)
        if t >= 2 ** 29 or t < -(2 ** 29): return STATUS['bignum'], float(t), None
        return STATUS['exact'], float(t), t
    if op.endswith('32'):
        base = op[:-2]
        a32, b32 = to_single(a), to_single(b)
        status, result = expected(base, a32, b32, SINGLE)
        if status in (STATUS['exact'], STATUS['underflow'], STATUS['inexact']) and result == result and result not in (INF, -INF):
            status = STATUS['unclassified']
        if result != result: return status, None, None
        return status, to_single(result), None
    status, result = expected(op, a, b, DOUBLE)
    if result != result: return status, None, None
    return status, result, None


def build(seed=20260915):
    g = LCG(seed); cases = []
    def add(ident, op, a, b):
        single = op.endswith('32')
        if single:
            a, b = to_single(a), (to_single(b) if b is not None else None)
        status, result, integer = expected_case(op, a, b)
        rec = dict(id=ident, op=op, a=('%08x' % bits32(a)) if single else ('%016x' % bits64(a)), status=status)
        if b is not None: rec['b'] = ('%08x' % bits32(b)) if single else ('%016x' % bits64(b))
        rec['result'] = None if result is None else (('%08x' % bits32(result)) if single else ('%016x' % bits64(result)))
        if integer is not None: rec['integer'] = integer
        if op == 'compare': rec['result'] = '0' * 16; rec['ordered'] = int(a < b)
        cases.append(rec)
    for ident, op, a, b in NAMED: add(ident, op, a, b)
    for op in ('add', 'sub', 'mul', 'div'):
        for k in range(300): add('%s-r%03d' % (op, k), op, random_double(g), random_double(g))
    for k in range(200): add('sqrt-r%03d' % k, 'sqrt', random_double(g), None)
    for k in range(100):   # products straddling the normal/subnormal boundary: (1 + j 2^-52) (1 - i 2^-53) 2^-1022 with i near 2 j
        j = g.choice(1 << 25); i = max(0, 2 * j + g.choice(5) - 2)
        add('mul-boundary-r%03d' % k, 'mul', (-1.0 if g.choice(2) else 1.0) * MIN_NORMAL * (1 + j * 2.0 ** -52), (-1.0 if g.choice(2) else 1.0) * (1 - i * 2.0 ** -53))
    for k in range(50):    # quotients at the boundary: a significand of ones over a power of two, through both scalings of the small-quotient witness
        i = g.choice(9); m = g.choice(1001) - 1000
        add('div-boundary-r%03d' % k, 'div', (-1.0 if g.choice(2) else 1.0) * (1 - i * 2.0 ** -53) * 2.0 ** m, (-1.0 if g.choice(2) else 1.0) * 2.0 ** (m + 1022))
    for k in range(100): add('trunc-r%03d' % k, 'trunc', random_double(g), None)
    for op in ('add32', 'mul32', 'div32'):
        for k in range(100): add('%s-r%03d' % (op, k), op, random_single(g), random_single(g))
    for mname, mask in MASKS.items():   # policy layer: every status under every mask
        for st in range(8):
            cases.append(dict(id='policy-%s-status%d' % (mname, st), op='policy', status_in=st, mask=mask, status=condition_of(st, mask), result='0' * 16))
    return dict(version=1, seed=seed, statuses=STATUS, cases=cases)


if __name__ == '__main__':
    corpus = build()
    from collections import Counter
    print(len(corpus['cases']), Counter((c['op'], c['status']) for c in corpus['cases']))
