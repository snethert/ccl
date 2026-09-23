#!/usr/bin/env python3
"""Keep fault mutations when collapsing a control corpus's aliases."""
import importlib.util
from pathlib import Path
import unittest
import hashlib
import json
import subprocess
import tempfile

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


class ModuleDigests(unittest.TestCase):
    def test_manifest_from_emitted_modules(self):
        with tempfile.TemporaryDirectory() as directory:
            env = Path(directory)
            (env / 'files/x').mkdir(parents=True)
            (env / 'files/x/a.wat').write_bytes(b'(module)')
            (env / 'files/x/skip.json').write_text('{}')
            module.write_module_digests(env)
            self.assertEqual(json.loads((env / 'module-digests.json').read_text()),
                             {'files/x/a.wat': hashlib.sha256(b'(module)').hexdigest()})


class SourceSnapshot(unittest.TestCase):
    def test_uses_committed_bytes_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'checkout'
            root.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL, text=True).strip()
            git('init')
            path = root / 'input'
            path.write_text('reviewed')
            git('add', 'input')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'input')
            revision = git('rev-parse', 'HEAD')
            path.write_text('integrated')
            with module.source_snapshot(root, revision) as (snapshot, commit):
                self.assertEqual(commit, revision)
                self.assertEqual((snapshot / 'input').read_text(), 'reviewed')
                self.assertEqual(path.read_text(), 'integrated')
                self.assertEqual((snapshot.parent / 'ccl-evidence').resolve(), (root.parent / 'ccl-evidence').resolve())
            self.assertFalse(snapshot.exists())
            with self.assertRaises(subprocess.CalledProcessError):
                with module.source_snapshot(root, 'missing-revision'):
                    self.fail('invalid revision admitted')


if __name__ == '__main__':
    unittest.main()
