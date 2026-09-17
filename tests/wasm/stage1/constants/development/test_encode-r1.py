"""Literal byte oracles; deliberately independent of encoder tables/formulas."""
import unittest
from encode import Encoder


def scalar(kind, value):
    return {'kind': kind, 'value': value}


def vector(kind, values):
    return {'kind': 'vector', 'type': kind, 'elements': values}


class EncodingTests(unittest.TestCase):
    def setUp(self):
        self.e = Encoder()

    def golden(self, spec, expected):
        result = self.e.encode(spec)
        self.assertIsNone(result.immediate)
        self.assertEqual(result.image.hex(), expected.replace(' ', ''))

    def test_immediates(self):
        for n, word in [('-536870912', 0x80000000), ('536870911', 0x7ffffffc),
                        ('-1', 0xfffffffc), ('0', 0), ('1', 4)]:
            with self.subTest(n=n):
                r = self.e.encode(scalar('integer', n))
                self.assertEqual((r.immediate, r.image), (word, b''))
        for kind, value, word in [('character', 0x1f642, 0x1f6424b),
                                   ('character', 0, 0x4b), ('singleton', 'nil', 77825),
                                   ('singleton', 't', 77838)]:
            self.assertEqual(self.e.encode(scalar(kind, value)).immediate, word)

    def test_bignum_signed_limbs(self):
        cases = [('536870912', '07010000 00000020'),
                 ('-536870913', '07010000 ffffffdf'),
                 ('2147483648', '07020000 00000080 00000000 00000000'),
                 ('-2147483648', '07010000 00000080'),
                 ('-2147483649', '07020000 ffffff7f ffffffff 00000000'),
                 ('4294967295', '07020000 ffffffff 00000000 00000000'),
                 ('9223372036854775808', '07030000 00000000 00000080 00000000'),
                 ('-9223372036854775809', '07030000 ffffffff ffffff7f ffffffff')]
        for n, expected in cases:
            with self.subTest(n=n):
                self.golden(scalar('integer', n), expected)

    def test_float_payloads(self):
        for v, little in [('00000000','00000000'), ('80000000','00000080'),
                          ('00000001','01000000'), ('7f800000','0000807f'),
                          ('ff800000','000080ff'), ('7fc12345','4523c17f'),
                          ('7f812345','4523817f')]:
            self.golden(scalar('single-float', v), '0f010000' + little)
        for v, little in [('0000000000000000','0000000000000000'),
                          ('8000000000000000','0000000000000080'),
                          ('0000000000000001','0100000000000000'),
                          ('7ff0000000000000','000000000000f07f'),
                          ('7ff8123456789abc','bc9a78563412f87f'),
                          ('7ff0123456789abc','bc9a78563412f07f')]:
            self.golden(scalar('double-float', v), '1703000000000000' + little)

    def test_strings_and_vectors(self):
        cases = [(scalar('string', []), 'bf00000000000000'),
                 (scalar('string', [65, 0, 0x1f642]), 'bf030000410000000000000042f60100'),
                 (vector('u8', ['0','255','17']), 'c703000000ff1100'),
                 (vector('s8', ['-128','127','-1']), 'cf030000807fff00'),
                 (vector('u16', ['0','65535','256']), 'd70300000000ffff0001000000000000'),
                 (vector('s16', ['-32768','32767']), 'df0200000080ff7f0000000000000000'),
                 (vector('u32', ['4294967295']), 'a7010000ffffffff'),
                 (vector('s32', ['-2147483648','2147483647']), 'af02000000000080ffffff7f00000000'),
                 (vector('fixnum', ['-536870912','536870911']), 'b7020000000000e0ffffff1f00000000'),
                 (vector('single-float', ['80000000']), '9f01000000000080'),
                 (vector('double-float', ['8000000000000000']), 'e7010000000000000000000000000080'),
                 (vector('complex-single-float', [['3f800000','80000000']]), 'ef010000000000000000803f00000080'),
                 (vector('complex-double-float', [['3ff0000000000000','8000000000000000']]), 'f701000000000000000000000000f03f0000000000000080'),
                 (vector('bit', [1,0,1,0,0,0,0,1,1]), 'ff09000085010000'),
                 (vector('double-float', []), 'e700000000000000')]
        for spec, golden in cases:
            with self.subTest(spec=spec):
                self.golden(spec, golden)
        self.golden(vector('bit', [1] + [0]*30 + [1,1]), 'ff210000010000800100000000000000')

    def test_refusals(self):
        bad = [scalar('integer', v) for v in [True, 1, 1.0, '01', '-0', '+1', '1.0']]
        bad += [scalar('character', v) for v in [True, -1, 0x110000, '65']]
        bad += [scalar('single-float', v) for v in [1.0,'7FC12345','0000000','000000000']]
        bad += [scalar('string', 'hi'), scalar('string', [0x110000]),
                scalar('singleton', 'other'), scalar('ratio', '1/2'),
                {'kind': 'integer', 'value': '1', 'ignored': 2},
                vector('s8', ['128']), vector('u8', ['-1']),
                vector('s16', ['32768']), vector('u16', ['65536']),
                vector('s32', ['2147483648']), vector('u32', ['4294967296']),
                vector('fixnum', ['536870912']), vector('fixnum', ['-536870913']),
                vector('bit', [True]), vector('bit', [2]), vector('u64', ['0']),
                vector('complex-single-float', ['00000000']),
                vector('complex-double-float', [['0000000000000000']])]
        for spec in bad:
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                self.e.encode(spec)

    def test_limits_and_padding(self):
        with self.assertRaisesRegex(ValueError, 'header count'):
            self.e.extent(1 << 24, 0)
        self.assertEqual(self.e.extent((1 << 24)-1, 0), 8)
        with self.assertRaisesRegex(ValueError, 'byte budget'):
            Encoder(max_bytes=7).encode(scalar('integer', '536870912'))
        with self.assertRaisesRegex(ValueError, 'byte budget'):
            Encoder(max_bytes=8).encode(vector('u8', ['0'] * 5))
        self.assertEqual(len(Encoder(max_bytes=8).encode(vector('u8', ['0'] * 4)).image), 8)
        self.assertEqual(Encoder(max_bytes=0).encode(scalar('integer', '1')).immediate, 4)


if __name__ == '__main__':
    unittest.main()
