"""Exact IEEE 754 binary rounding and flag classification over rationals.

round_binary rounds a rational to the nearest representable value (ties to
even) in a binary format with p significand bits and exponent range
[emin, emax], and reports the IEEE flags: overflow, underflow (tininess after
rounding, together with inexactness) and inexact. It is the oracle for the
checked operations; it uses only integer arithmetic.
"""
from fractions import Fraction
import math
import struct

DOUBLE = dict(p=53, emin=-1022, emax=1023)
SINGLE = dict(p=24, emin=-126, emax=127)
STATUS = {'exact': 0, 'overflow': 1, 'division-by-zero': 2, 'invalid': 3, 'underflow': 4, 'inexact': 5, 'bignum': 6, 'unclassified': 7}


def floor_log2(x):
    """floor(log2(x)) for a positive rational."""
    n, d = x.numerator, x.denominator
    e = n.bit_length() - d.bit_length()
    if Fraction(2) ** e > x:
        e -= 1
    if Fraction(2) ** (e + 1) <= x:
        e += 1
    return e


def round_to_quantum(x, q):
    """Nearest multiple of the positive rational q, ties to even."""
    m, r = divmod(x, q)
    r = Fraction(r) / q
    if r > Fraction(1, 2) or (r == Fraction(1, 2) and m % 2 == 1):
        m += 1
    return m * q


def round_binary(x, fmt):
    """Return (value, flags) where value is a Fraction or ±inf and flags is a set."""
    p, emin, emax = fmt['p'], fmt['emin'], fmt['emax']
    if x == 0:
        return Fraction(0), set()
    sign = -1 if x < 0 else 1
    mag = abs(x)
    e = floor_log2(mag)
    unbounded = round_to_quantum(mag, Fraction(2) ** (e - p + 1))
    quantum = Fraction(2) ** (max(e, emin) - p + 1)
    value = round_to_quantum(mag, quantum)
    flags = set()
    if value != mag:
        flags.add('inexact')
    if value >= Fraction(2) ** (emax + 1):
        flags.add('overflow'); flags.add('inexact')
        return sign * math.inf, flags
    if unbounded < Fraction(2) ** emin and 'inexact' in flags:
        flags.add('underflow')
    return sign * value, flags


def status_of(flags, tiny_zero_from_nonzero=False):
    if 'overflow' in flags: return STATUS['overflow']
    if 'underflow' in flags or tiny_zero_from_nonzero: return STATUS['underflow']
    if 'inexact' in flags: return STATUS['inexact']
    return STATUS['exact']


def expected(op, a, b=None, fmt=DOUBLE):
    """Expected (status, result) for op on floats a, b (Python floats holding format values)."""
    isnan = lambda v: v != v
    inf = math.inf
    if op == 'sqrt':
        if isnan(a): return STATUS['exact'], math.nan
        if a < 0: return STATUS['invalid'], math.nan
        if a == inf or a == 0: return STATUS['exact'], math.sqrt(a) if a != 0 else a
        exact = Fraction(a)
        root = exact.numerator; den = exact.denominator
        # exact rational square root when both parts are perfect squares; otherwise inexact
        rn, rd = math.isqrt(root), math.isqrt(den)
        if rn * rn == root and rd * rd == den:
            value, flags = round_binary(Fraction(rn, rd), fmt)
            return status_of(flags), float(value)
        value = round_binary_sqrt(exact, fmt)
        return STATUS['inexact'], value
    if isnan(a) or isnan(b): return STATUS['exact'], math.nan
    if op in ('add', 'sub'):
        bb = -b if op == 'sub' else b
        if a in (inf, -inf) or bb in (inf, -inf):
            if a in (inf, -inf) and bb in (inf, -inf) and a != bb: return STATUS['invalid'], math.nan
            return STATUS['exact'], a + bb
        exact = Fraction(a) + Fraction(bb)
        value, flags = round_binary(exact, fmt)
        if exact == 0:
            value = a + bb  # signed zero rule: -0 + -0 = -0, otherwise +0
        return status_of(flags), float(value)
    if op == 'mul':
        if a in (inf, -inf) or b in (inf, -inf):
            if a == 0 or b == 0: return STATUS['invalid'], math.nan
            return STATUS['exact'], a * b
        if a == 0 or b == 0: return STATUS['exact'], a * b
        exact = Fraction(a) * Fraction(b)
        value, flags = round_binary(exact, fmt)
        result = float(value) if value != 0 else math.copysign(0.0, a * b)
        return status_of(flags, tiny_zero_from_nonzero=(value == 0)), result
    if op == 'div':
        if b == 0:
            if a == 0 or isnan(a): return STATUS['invalid'], math.nan
            if a in (inf, -inf): return STATUS['exact'], a / b if False else math.copysign(inf, a) * math.copysign(1.0, b)
            return STATUS['division-by-zero'], math.copysign(inf, a) * math.copysign(1.0, b)
        if a in (inf, -inf):
            if b in (inf, -inf): return STATUS['invalid'], math.nan
            return STATUS['exact'], math.copysign(inf, a) * math.copysign(1.0, b)
        if b in (inf, -inf): return STATUS['exact'], math.copysign(0.0, a) * math.copysign(1.0, b)
        if a == 0: return STATUS['exact'], math.copysign(0.0, a) * math.copysign(1.0, b)
        exact = Fraction(a) / Fraction(b)
        value, flags = round_binary(exact, fmt)
        result = float(value) if value != 0 else math.copysign(0.0, a) * math.copysign(1.0, b)
        return status_of(flags, tiny_zero_from_nonzero=(value == 0)), result
    raise ValueError(op)


def round_binary_sqrt(x, fmt):
    """Correctly rounded square root of a positive rational that is not a perfect square: nearest float."""
    p, emin = fmt['p'], fmt['emin']
    e = floor_log2(x) // 2
    quantum = Fraction(2) ** (max(e, emin) - p + 1)
    # integer square root of x / quantum^2, then ties cannot occur (irrational)
    scaled = x / (quantum * quantum)
    n, d = scaled.numerator, scaled.denominator
    m = math.isqrt(n // d)
    # nearest integer to sqrt(scaled): compare (m + 1/2)^2 with scaled
    if Fraction(2 * m + 1, 2) ** 2 < scaled:
        m += 1
    return float(m * quantum)


def to_single(value):
    """Round a Python float or Fraction to the nearest float32 and return it as a Python float."""
    if isinstance(value, float) and (value != value or value in (math.inf, -math.inf) or value == 0):
        return value
    v, flags = round_binary(Fraction(value), SINGLE)
    return float(v) if v not in (math.inf, -math.inf) else v


def bits64(f): return struct.unpack('<Q', struct.pack('<d', f))[0]
def from_bits64(b): return struct.unpack('<d', struct.pack('<Q', b))[0]
def bits32(f): return struct.unpack('<I', struct.pack('<f', f))[0]
def from_bits32(b): return struct.unpack('<f', struct.pack('<I', b))[0]


# D6 policy layer, the ARM model: hardware-style flags per status and the condition chosen by ARM's priority among the enabled flags.
FLAG = {'invalid': 1, 'division-by-zero': 2, 'overflow': 4, 'underflow': 8, 'inexact': 16}
DEFAULT_MASK = FLAG['invalid'] | FLAG['division-by-zero'] | FLAG['overflow']
PRIORITY = (('invalid', STATUS['invalid']), ('division-by-zero', STATUS['division-by-zero']), ('overflow', STATUS['overflow']), ('underflow', STATUS['underflow']), ('inexact', STATUS['inexact']))


def flags_of(status):
    """Cumulative flags a hardware FPU would set for a result of this status: overflow and underflow are inexact as well."""
    return {STATUS['invalid']: FLAG['invalid'], STATUS['division-by-zero']: FLAG['division-by-zero'], STATUS['overflow']: FLAG['overflow'] | FLAG['inexact'],
            STATUS['underflow']: FLAG['underflow'] | FLAG['inexact'], STATUS['inexact']: FLAG['inexact']}.get(status, 0)


def condition_of(status, mask):
    enabled = flags_of(status) & mask
    for name, code in PRIORITY:
        if enabled & FLAG[name]:
            return code
    return STATUS['exact']
