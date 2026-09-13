"""Use the existing recoverable observation unit on an owned U1 archive."""
import json
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from reversible import ObservationUnit, digest


class BootUnit(ObservationUnit):
    def __init__(self, work, fixture=HERE):
        self.work, self.fixture = Path(work).resolve(), Path(fixture).resolve()
        self.source = self.work / 'ccl'
        if json.loads((self.work / 'disposable.json').read_text()) != {
                'purpose': 'boot-census-disposable-U1', 'source': str(self.source)}:
            raise ValueError('not an owned boot-census archive')
        if (self.source / '.git').exists() or self.source.is_symlink():
            raise ValueError('requires an archive, not a checkout')
        self.manifest = json.loads((self.fixture / 'patch.json').read_text())
        if self.manifest['source_revision'] != 'c994217adc56b3f8a564526cee4695893ac84d86':
            raise ValueError('wrong observation baseline')
        if digest(self.fixture / 'observation.patch') != self.manifest['patch_sha256']:
            raise ValueError('changed observation patch')
        if [r['path'] for r in self.manifest['files']] != [
                'level-0/l0-def.lisp', 'level-0/nfasload.lisp', 'level-1/level-1.lisp']:
            raise ValueError('unexpected observation scope')
        for row in self.manifest['files']:
            p = self.source / row['path']
            if not p.is_file() or p.resolve() != p: raise ValueError('redirected or missing source')
        self.state = self.work / 'observation-state.json'
