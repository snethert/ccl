"""The extended observation unit uses the reviewed apply/restore mechanism."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))
from reversible import ObservationUnit, digest
from build_patch import FILES, U1


class RichUnit(ObservationUnit):
    def __init__(self, work, fixture=HERE):
        self.work, self.fixture = Path(work).resolve(), Path(fixture).resolve()
        self.source = self.work / 'ccl'
        marker = json.loads((self.work / 'disposable.json').read_text())
        if marker != {'purpose': 'rich-census-disposable-U1', 'source': str(self.source)}:
            raise ValueError('not an owned rich-census archive')
        if (self.source / '.git').exists() or self.source.is_symlink():
            raise ValueError('requires a disposable U1 archive, not a checkout')
        self.manifest = json.loads((self.fixture / 'patch.json').read_text())
        if (self.manifest['source_revision'] != U1 or
                digest(self.fixture / 'observation.patch') != self.manifest['patch_sha256']):
            raise ValueError('rich observation patch identity mismatch')
        if [r['path'] for r in self.manifest['files']] != list(FILES):
            raise ValueError('unexpected rich observation source scope')
        for row in self.manifest['files']:
            p = self.source / row['path']
            if not p.is_file() or p.resolve() != p:
                raise ValueError('missing or redirected observation input')
        self.state = self.work / 'observation-state.json'
