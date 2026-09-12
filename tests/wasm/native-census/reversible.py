"""Apply/remove the complete observation unit only in an owned disposable tree."""
import hashlib
import json
import os
from pathlib import Path
import subprocess


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    data = json.dumps(value, indent=2) + '\n'
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(data)
    os.replace(tmp, path)


class ObservationUnit:
    def __init__(self, work, fixture):
        self.work, self.fixture = Path(work).resolve(), Path(fixture).resolve()
        self.source = self.work / 'ccl'
        marker = json.loads((self.work / 'disposable.json').read_text())
        if marker != {'purpose': 'native-census-disposable-U1', 'source': str(self.source)}:
            raise ValueError('not an owned census checkout')
        if (self.source / '.git').exists() or self.source.is_symlink():
            raise ValueError('instrumentation requires a disposable source archive, not a checkout')
        self.manifest = json.loads((self.fixture / 'patch.json').read_text())
        if digest(self.fixture / 'observation.patch') != self.manifest['patch_sha256']:
            raise ValueError('observation patch hash mismatch')
        if self.manifest['source_revision'] != 'c994217adc56b3f8a564526cee4695893ac84d86':
            raise ValueError('observation patch is not for U1')
        expected = {'compiler/nx.lisp', 'lib/nfcomp.lisp', 'lib/dumplisp.lisp'}
        if {r['path'] for r in self.manifest['files']} != expected or len(self.manifest['files']) != 3:
            raise ValueError('unexpected patch scope')
        for r in self.manifest['files']:
            p = self.source / r['path']
            if p.resolve() != p or not p.is_file():
                raise ValueError('observation input is missing or redirected')
        self.state = self.work / 'observation-state.json'

    def check(self, key):
        for r in self.manifest['files']:
            if digest(self.source / r['path']) != r[key]:
                raise ValueError('unexpected source bytes: ' + r['path'])

    def apply(self):
        self.check('original_sha256')
        if self.state.exists() and json.loads(self.state.read_text())['active']:
            raise ValueError('observation unit already active; restore first')
        backup = self.work / 'original-source'
        for r in self.manifest['files']:
            dest = backup / r['path']; dest.parent.mkdir(parents=True, exist_ok=True)
            data = (self.source / r['path']).read_bytes()
            if dest.exists() and dest.read_bytes() != data:
                raise ValueError('original-source backup mismatch')
            if not dest.exists(): dest.write_bytes(data)
        # Persist recovery metadata before the first source mutation.
        save(self.state, {'active': True, 'patch_sha256': self.manifest['patch_sha256']})
        argv = ['git', 'apply', str(self.fixture / 'observation.patch')]
        subprocess.run(argv[:2] + ['--check'] + argv[2:], cwd=self.source, check=True, capture_output=True)
        subprocess.run(argv, cwd=self.source, check=True, capture_output=True)
        self.check('observed_sha256')

    def restore(self):
        state = json.loads(self.state.read_text())
        if state['patch_sha256'] != self.manifest['patch_sha256']:
            raise ValueError('recovery patch differs from the applied unit')
        # Accept mixed original/patched states after an interrupted apply/remove,
        # but refuse to overwrite any unexplained external modification.
        for r in self.manifest['files']:
            if digest(self.source / r['path']) not in (r['original_sha256'], r['observed_sha256']):
                raise ValueError('unexplained source modification: ' + r['path'])
            if digest(self.work / 'original-source' / r['path']) != r['original_sha256']:
                raise ValueError('damaged recovery backup: ' + r['path'])
        for r in self.manifest['files']:
            p = self.source / r['path']; tmp = p.with_name(p.name + '.census-restore')
            tmp.write_bytes((self.work / 'original-source' / r['path']).read_bytes())
            os.replace(tmp, p)
        self.check('original_sha256')
        save(self.state, {'active': False, 'patch_sha256': self.manifest['patch_sha256'],
                          'restored': 'all original source SHA-256 digests match'})
        return json.loads(self.state.read_text())

    def __enter__(self):
        try:
            self.apply()
        except BaseException:
            if self.state.exists(): self.restore()
            raise
        return self

    def __exit__(self, *_):
        self.restore()
