#!/usr/bin/env python3
"""Keep fault mutations when collapsing a control corpus's aliases."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('condition_artifacts', Path(__file__).with_name('verify-condition-frontier.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CanonicalRecords(unittest.TestCase):
    def test_named_identical_counterpart_only(self):
        base = 'numeric/compiled/x.wasm'
        alias = 'numeric/condition-faults/a/compiled/x.wasm'
        unrelated = 'numeric/unrelated.wasm'
        kept, edges = module.canonical_records({base: 'same', alias: 'same', unrelated: 'same'})
        self.assertEqual(edges, {alias: base})
        self.assertEqual(kept, {base: 'same', unrelated: 'same'})

    def test_all_mutation_artifacts_survive(self):
        records = {}
        for filename in ('x.wasm', 'x.wat', 'native.json'):
            records['numeric/compiled/' + filename] = 'base'
            records['numeric/condition-faults/a/compiled/' + filename] = 'changed'
        kept, edges = module.canonical_records(records)
        self.assertEqual(kept, records)
        self.assertFalse(edges)

    def test_missing_counterpart_survives(self):
        records = {'numeric/condition-faults/a/compiled/new.wat': 'same'}
        kept, edges = module.canonical_records(records)
        self.assertEqual(kept, records)
        self.assertFalse(edges)


if __name__ == '__main__':
    unittest.main()
