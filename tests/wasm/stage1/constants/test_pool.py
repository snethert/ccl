import copy
import unittest
from pool import compile_pool

NIL = {'kind': 'singleton', 'value': 'nil'}
def integer(n): return {'kind': 'integer', 'value': str(n)}
def ref(n): return {'ref': n}
def graph(objects, roots): return {'version': 1, 'objects': [{'id': k, 'value': v} for k, v in objects], 'roots': roots}
def cons(car, cdr): return {'kind': 'cons', 'car': car, 'cdr': cdr}
def vector(*values): return {'kind': 'general-vector', 'elements': list(values)}
def word(image, offset): return int.from_bytes(image[offset:offset+4], 'little')


class PoolTests(unittest.TestCase):
    def test_identity_cycles_and_layout(self):
        g = graph([('pool', vector(ref('loop'), ref('loop'), ref('equal'), ref('a'), ref('b'))),
                   ('loop', cons(integer(7), ref('loop'))),
                   ('equal', cons(integer(7), ref('loop'))),
                   ('a', {'kind': 'string', 'value': [65]}),
                   ('b', {'kind': 'string', 'value': [65]})], [ref('pool'), ref('loop')])
        original = copy.deepcopy(g)
        p = compile_pool(g)
        self.assertEqual(g, original)
        # Offsets derived literally from D1: vector 24, two conses 16, strings 16.
        for base in (0x1000, 0x7ffffff8, 0x80000000, 0xffffffc8):
            with self.subTest(base=base):
                m = p.at(base)
                self.assertEqual(len(m.image), 56)
                self.assertEqual(m.roots, (base+6, base+25))
                self.assertEqual([word(m.image, i) for i in range(0, 40, 4)],
                                 [0x5fa, base+25, base+25, base+33, base+46, base+54,
                                  base+25, 28, base+25, 28])
                self.assertEqual(m.image[40:], bytes.fromhex('bf01000041000000bf01000041000000'))
                self.assertNotEqual(dict(m.objects)['a'], dict(m.objects)['b'])
        # Plan has no retained source graph or dependency on its later mutation.
        g['objects'].clear()
        self.assertEqual(p.at(0x1000).roots, (0x1006, 0x1019))

    def test_mutual_forward_and_cold_pools(self):
        p = compile_pool(graph([('parent', vector(ref('child'))),
                                ('child', vector(ref('parent'))),
                                ('cold', vector(integer(123)))], [ref('parent')]))
        m = p.at(0x2000)
        self.assertEqual(m.image.hex(), 'fa0100000e200000fa01000006200000fa010000ec010000')
        self.assertEqual(dict(m.objects)['cold'], 0x2016)
        self.assertEqual(len(m.image), 24)

    def test_owner_symbols_and_immediate_roots(self):
        g = graph([('p', vector({'symbol': 'P::X'}, NIL, integer(-1)))],
                  [ref('p'), {'symbol': 'P::X'}, NIL, integer(1)])
        p = compile_pool(g, {'P::X': 0x4006})
        for base in (0x1000, 0x80000000):
            m = p.at(base)
            self.assertEqual(m.roots, (base+6, 0x4006, 77825, 4))
            self.assertEqual(m.image.hex(), 'fa0300000640000001300100fcffffff')
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            p.at(0x4000)
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            p.at(77824)
        # Symbol aliases remain aliases; case and package spelling are not folded.
        with self.assertRaisesRegex(ValueError, 'unresolved'):
            compile_pool(g, {'p::x': 0x4006})

    def test_heap_scalars_and_empty_graph(self):
        p = compile_pool(graph([('big', integer(536870912)),
                                ('empty', vector())], [ref('big'), ref('empty')]))
        self.assertEqual(p.at(0x1000).image.hex(), '0701000000000020fa00000000000000')
        self.assertEqual(compile_pool(graph([], [integer(1)])).at(8).roots, (4,))

    def test_refusals(self):
        bad = [graph([('a', cons(integer(1), ref('missing')))], [ref('a')]),
               graph([('a', vector()), ('a', vector())], []),
               graph([('a', integer(1))], []),
               graph([], [integer(536870912)]),
               graph([('a', vector({'ref': 'a', 'ignored': 1}))], []),
               graph([('a', vector({'symbol': 'missing'}))], []),
               graph([('', vector())], []),
               graph([('cold', cons(integer(1), ref('missing')))], []),
               {'version': True, 'objects': [], 'roots': []}]
        for g in bad:
            with self.subTest(graph=g), self.assertRaises(ValueError):
                compile_pool(g)
        for symbols in ({'X': True}, {'X': -2}, {'X': 2**32+6}, {'X': 4}):
            with self.assertRaises(ValueError):
                compile_pool(graph([], []), symbols)
        with self.assertRaisesRegex(ValueError, 'aggregate'):
            compile_pool(graph([('a', vector()), ('b', vector())], []), max_bytes=8)

    def test_extent_refusals_preserve_plan(self):
        p = compile_pool(graph([('a', cons(integer(1), ref('a')))], [ref('a')]))
        original = p.at(0x1000)
        for base, limit in [(0, 2**32), (9, 2**32), (-8, 2**32), (2**32, 2**32),
                            (0xfffffff8, 0xffffffff), (8, 15), (8, 2**32+1), (True, 16)]:
            with self.subTest(base=base, limit=limit), self.assertRaises(ValueError):
                p.at(base, limit)
        self.assertEqual(p.at(0x1000), original)
        self.assertEqual(p.at(0xfffffff8).roots, (0xfffffff9,))


if __name__ == '__main__':
    unittest.main()
