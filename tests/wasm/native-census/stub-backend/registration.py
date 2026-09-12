"""Apply and reverse the census registration unit only in an owned U1 archive."""
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reversible import digest, save


class Registration:
    def __init__(self, work, fixture):
        self.work = Path(work).resolve(); self.fixture = Path(fixture).resolve()
        self.source = self.work / 'ccl'
        if json.loads((self.work / 'disposable.json').read_text()) != {
                'purpose': 'census-stub-disposable-U1', 'source': str(self.source)}:
            raise ValueError('requires an owned disposable U1 archive')
        if (self.source / '.git').exists() or self.source.is_symlink():
            raise ValueError('refuse registration in a checkout or redirected source')
        self.manifest = json.loads((self.fixture / 'patch.json').read_text())
        if (self.manifest['source_revision'] != 'c994217adc56b3f8a564526cee4695893ac84d86' or
                digest(self.fixture / 'registration.patch') != self.manifest['patch_sha256']):
            raise ValueError('registration source/patch identity mismatch')
        if ([r['path'] for r in self.manifest['modified']] != ['lib/systems.lisp'] or
                {r['path'] for r in self.manifest['added']} != {
                    'compiler/WASM-CENSUS/census-arch.lisp', 'compiler/WASM-CENSUS/census-backend.lisp'}):
            raise ValueError('unexpected registration scope')
        for r in self.manifest['modified'] + self.manifest['added']:
            p = self.source / r['path']
            if p.resolve() != p: raise ValueError('redirected registration path')
        self.state = self.work / 'registration-state.json'

    def apply(self):
        if self.state.exists() and json.loads(self.state.read_text())['active']:
            raise ValueError('registration already active')
        for r in self.manifest['modified']:
            if digest(self.source / r['path']) != r['before_sha256']:
                raise ValueError('shared source differs from U1')
        for r in self.manifest['added']:
            if (self.source / r['path']).exists() or digest(self.fixture / r['fixture']) != r['sha256']:
                raise ValueError('added source already exists or fixture identity differs')
        backup = self.work / 'original-systems.lisp'
        original = (self.source / 'lib/systems.lisp').read_bytes()
        if backup.exists() and backup.read_bytes() != original: raise ValueError('recovery backup differs')
        backup.write_bytes(original)
        save(self.state, {'active': True, 'patch_sha256': self.manifest['patch_sha256']})
        argv = ['git', 'apply', str(self.fixture / 'registration.patch')]
        subprocess.run(argv[:2] + ['--check'] + argv[2:], cwd=self.source, check=True, capture_output=True)
        subprocess.run(argv, cwd=self.source, check=True, capture_output=True)
        for r in self.manifest['added']:
            dest = self.source / r['path']; dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((self.fixture / r['fixture']).read_bytes())
        for r in self.manifest['modified']:
            if digest(self.source / r['path']) != r['after_sha256']: raise ValueError('patched bytes differ')

    def restore(self):
        state = json.loads(self.state.read_text())
        if state['patch_sha256'] != self.manifest['patch_sha256']: raise ValueError('recovery unit differs')
        for r in self.manifest['modified']:
            if digest(self.source / r['path']) not in (r['before_sha256'], r['after_sha256']):
                raise ValueError('unexplained shared source edit')
        for r in self.manifest['added']:
            p = self.source / r['path']
            if p.exists() and digest(p) != r['sha256']: raise ValueError('unexplained added source edit')
        if digest(self.work / 'original-systems.lisp') != self.manifest['modified'][0]['before_sha256']:
            raise ValueError('damaged recovery backup')
        destination = self.source / 'lib/systems.lisp'
        temporary = destination.with_name('systems.lisp.census-restore')
        temporary.write_bytes((self.work / 'original-systems.lisp').read_bytes())
        os.replace(temporary, destination)
        for r in self.manifest['added']: (self.source / r['path']).unlink(missing_ok=True)
        directory = self.source / 'compiler/WASM-CENSUS'
        if directory.exists() and not any(directory.iterdir()): directory.rmdir()
        result = {'active': False, 'patch_sha256': state['patch_sha256'], 'restored': 'original shared source; both additions removed'}
        save(self.state, result); return result

    def __enter__(self):
        try: self.apply()
        except BaseException:
            if self.state.exists() and json.loads(self.state.read_text())['active']: self.restore()
            raise
        return self

    def __exit__(self, *_): self.restore()
