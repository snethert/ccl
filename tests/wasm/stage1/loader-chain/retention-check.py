"""Check that saved host images are bound separately from reproducible output."""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'bootstrap-validation'))
import common as c
import storage
import retain


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out) as directory:
        root = Path(directory)
        source = root / 'input'
        source.mkdir()
        (source / 'registered.image').write_bytes(b'host heap layout A')
        (source / 'module.wasm').write_bytes(b'reproducible module')
        c.save(source / 'run.json', dict(status='PASS'))
        packs = []
        for name in ('a', 'b'):
            pack = root / name
            retain.retain(c, pack, dict(native=source), 'RETENTION-CONTROL', {})
            packs.append(pack)
            (source / 'registered.image').write_bytes(b'host heap layout B')
        first, second = packs
        images = [c.read(p / 'non-reproducible.json') for p in packs]
        assert all(set(rows) == {'native/registered.image'} for rows in images)
        assert images[0] != images[1]
        assert c.read(first / 'regenerable.json') == c.read(second / 'regenerable.json')
        assert set(c.read(first / 'regenerable.json')) == {'native/module.wasm'}
        for pack in packs:
            assert not (pack / 'native/registered.image').exists()
            assert c.read(pack / 'native/run.json') == dict(status='PASS')
            c.verify_files(pack, c.read(pack / 'packet.json')['files'])
        c.save(out / 'retention-check.json', dict(status='PASS',
            changed_host_images_separate=True, reproducible_inventory_equal=True,
            reports_preserved=True, packets_verified=True,
            source=c.sha(Path(retain.__file__)), check=c.sha(Path(__file__))))


if __name__ == '__main__':
    out = Path(sys.argv[1]).resolve()
    with storage.lease([out]):
        run(out)
