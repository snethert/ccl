"""Retention regressions: immutable sharing, failure survival and atomic publication."""
from pathlib import Path
import gzip
import importlib.util
import io
import json
import shutil
import tarfile
import tempfile
import subprocess
import unittest
from unittest.mock import patch
import artifacts
import common as c
import storage
import checkpoint


class Artifacts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=storage.WORK_ROOT/'codex/artifact-retention')
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_shared_oracle_is_not_overwritten_by_probe(self):
        source = self.root/'cache';source.mkdir()
        (source/'native.json').write_text('[42]')
        (source/'compiler.image').write_bytes(b'compiler')
        c.clone(source,self.root/'run')
        self.assertTrue((self.root/'run/compiler.image').is_symlink())
        c.save(self.root/'run/native.json',[7])
        self.assertEqual(c.read(source/'native.json'),[42])

    def test_compressed_report_keeps_original_identity(self):
        from execute import bound_report
        report=self.root/'report.json'
        value=dict(status='PASS',environment={},environment_key=c.digest({}))
        body=c.canonical(value)
        with gzip.open(str(report)+'.gz','wb') as stream:stream.write(body)
        c.save(report.with_suffix('.identity.json'),dict(sha256=c.digest(value),environment=c.digest({})))
        self.assertTrue(c.exists(report))
        self.assertEqual(bound_report(report)[0],value)
        with gzip.open(str(report)+'.gz','wb') as stream:stream.write(body+b' ')
        with self.assertRaises(ValueError):bound_report(report)

    def test_recount_checkpoint_reuses_and_invalidates_on_source_change(self):
        kernel=self.root/'kernel';kernel.write_bytes(b'kernel')
        image=self.root/'baseline.image';image.write_bytes(b'baseline')
        calls=[]
        def setup(command,log,env,cwd,timeout):
            calls.append(command)
            dest=Path(env['RECOUNT_OUTPUT'])
            (dest/'compiler.image').write_bytes(b'checkpoint')
            c.save(dest/'worklist.json',['level-0/l0-utils.lisp'])
            Path(log).write_text('setup completed')
        with patch.object(c,'DEFAULT_CACHE',self.root/'cache'),patch.object(c,'command',setup):
            for i,source in enumerate(('first','first','changed')):
                out=self.root/str(i);(out/'proposal').mkdir(parents=True)
                (out/'proposal/input.lisp').write_text(source)
                checkpoint.prepare(out,self.root,['setup'],{},c.HERE,{'inputs':{'source':'pin'}},kernel,image)
                self.assertTrue((out/'compiler.image').is_symlink())
                self.assertEqual(c.read(out/'compiler-reference.json')['rebuilt'],i!=1)
            self.assertEqual(len(calls),2)

    def test_assembly_discards_success_keeps_failure(self):
        good=self.root/'good.wat';good.write_text('(module)')
        result=c.assemble(good,self.root/'cache')
        self.assertFalse(good.exists())
        self.assertEqual(c.sha(good.with_suffix('.wasm')),result['wasm'])
        bad=self.root/'bad.wat';bad.write_text('(invalid)')
        with self.assertRaises(Exception): c.assemble(bad,self.root/'cache')
        self.assertEqual(bad.read_text(),'(invalid)')
        self.assertEqual(c.read(self.root/'failure-inputs.json'),['bad.wat'])

    def test_atomic_publication_and_size_guideline_preserve_failure(self):
        work=self.root/'work';out=work/'author/purpose/run';out.mkdir(parents=True)
        (out/'results.json').write_text('{"status":"PASS"}')
        (out/'good.wasm').write_bytes(b'good')
        (out/'bad.wat').write_text('failing input')
        c.save(out/'failure-inputs.json',['bad.wat'])
        with patch.object(artifacts.shutil,'copyfile',side_effect=OSError('copy failed')):
            with self.assertRaises(OSError):storage.finish(out,self.root/'retained',work)
        self.assertTrue((out/'bad.wat').exists())
        self.assertFalse((self.root/'retained').exists())
        with patch.object(artifacts,'PACK_BYTES',1):
            result=storage.finish(out,self.root/'retained',work)
        self.assertTrue(result['above_target'])
        self.assertEqual((self.root/'retained/bad.wat').read_text(),'failing input')
        self.assertFalse((self.root/'retained/good.wasm').exists())

    def test_release_and_restore_detect_corrupt_cache(self):
        out=self.root/'run';out.mkdir()
        (out/'good.wasm').write_bytes(b'\0asm')
        (out/'bad.wasm').write_bytes(b'bad')
        c.save(out/'failure-inputs.json',['bad.wasm'])
        artifacts.release(out,self.root/'cache')
        self.assertFalse((out/'good.wasm').exists())
        self.assertTrue((out/'bad.wasm').exists())
        artifacts.restore(out)
        self.assertEqual((out/'good.wasm').read_bytes(),b'\0asm')
        (out/'good.wasm').unlink()
        row=c.read(out/'artifact-references.json')['good.wasm']
        Path(row['cache']).write_bytes(b'changed')
        with self.assertRaises(ValueError):artifacts.restore(out)

    def test_execution_failure_retains_only_its_case_and_module(self):
        import execute
        out=self.root/'run';(out/'compiled').mkdir(parents=True)
        (out/'probe-output').mkdir()
        c.save(out/'execution-environment.json',{})
        c.save(out/'case-ids.json',['bad','good'])
        c.save(out/'compiled/native.json',[dict(name='bad',args=[7]),dict(name='good',args=[9])])
        (out/'compiled/bad.wasm').write_bytes(b'bad bytes')
        (out/'compiled/good.wasm').write_bytes(b'good bytes')
        (out/'probe-output/bad.wat').write_text('original failing assembly')
        def fail(argv,*args,**kwargs):
            c.save(out/'parallel-results.json',dict(status='FAIL',failures=[dict(caseId='bad',name='bad')]))
            raise subprocess.CalledProcessError(1,argv)
        with patch.object(execute,'prepare',lambda p:None),patch.object(c,'command',fail):
            with self.assertRaises(subprocess.CalledProcessError):execute.execute(out,controls=False)
        artifacts.snapshot(out,self.root/'retained')
        self.assertEqual(c.read(self.root/'retained/failure-inputs/cases.json'),[dict(name='bad',args=[7])])
        self.assertEqual((self.root/'retained/failure-inputs/bad.wasm').read_bytes(),b'bad bytes')
        self.assertFalse((self.root/'retained/compiled/good.wasm').exists())

    def test_unfinished_run_and_alias_are_not_overwritten(self):
        work=self.root/'work';out=work/'author/purpose/run'
        storage.reset_run(out,work)
        (out/'failure.log').write_text('original failure')
        with self.assertRaises(ValueError):storage.reset_run(out,work)
        alias=out.parent/'alias';alias.symlink_to(out)
        with self.assertRaises(ValueError):storage.reset_run(alias,work)
        c.save(out/'.run.json',dict(status='PASS'))
        storage.reset_run(out,work)
        self.assertFalse((out/'failure.log').exists())

    def test_archive_compaction_preserves_sources_results_and_failure_inputs(self):
        spec=importlib.util.spec_from_file_location('compaction',c.ROOT/'doc/WASM/tools/compact-evidence.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.STORE=self.root
        pack=self.root/'pack';pack.mkdir()
        original=pack/'packet.json';original.write_text('{"historical":"unchanged"}')
        values={'sources/input.wat':b'(module)', 'run/good.wasm':b'\0asm',
                'run/results.json':b'{"status":"PASS"}',
                'failure-inputs/bad.wasm':b'bad', 'compiled/native.json':b'[42]'}
        with tarfile.open(pack/'artifacts.tar.gz','w:gz') as archive:
            for name,body in values.items():
                info=tarfile.TarInfo(name);info.size=len(body);archive.addfile(info,io.BytesIO(body))
        result=module.compact(pack,'pinned-test-commit',True)
        self.assertEqual(result['status'],'COMPACTED')
        self.assertEqual(original.read_text(),'{"historical":"unchanged"}')
        self.assertFalse((pack/'artifacts.tar.gz').exists())
        rows=c.read(pack/'compaction.json')['original_files']['artifacts.tar.gz']['members']
        for name in ('sources/input.wat','run/results.json','failure-inputs/bad.wasm'):
            self.assertEqual((pack/rows[name]['retained']).read_bytes(),values[name])
        self.assertIn('regenerate',rows['run/good.wasm'])
        self.assertEqual((self.root/rows['compiled/native.json']['shared_input']).read_bytes(),b'[42]')

    def test_unsafe_archive_preserves_originals(self):
        spec=importlib.util.spec_from_file_location('compaction',c.ROOT/'doc/WASM/tools/compact-evidence.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.STORE=self.root;pack=self.root/'pack';pack.mkdir()
        with tarfile.open(pack/'artifacts.tar','w') as archive:
            info=tarfile.TarInfo('../outside');info.size=1;archive.addfile(info,io.BytesIO(b'x'))
        with self.assertRaises(ValueError):module.compact(pack,'pinned-test-commit',True)
        self.assertTrue((pack/'artifacts.tar').exists())
        self.assertFalse((pack/'compaction.json').exists())
        self.assertFalse((self.root/'outside').exists())


if __name__=='__main__':
    storage.ensure_ram()
    (storage.WORK_ROOT/'codex/artifact-retention').mkdir(parents=True,exist_ok=True)
    unittest.main()
