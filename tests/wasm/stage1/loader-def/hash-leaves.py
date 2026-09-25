"""Reuse the accepted EQ-table service and internal B adapter by exact identity."""
import hashlib
import tarfile
import product

c = product.c


def prepare(out):
    packet = c.PARENT / 'packet.json'
    assert c.sha(packet) == '509d916f2255a6707c3779744240f7a025b6a4499ca45e69c4e52100659d05a1'
    records = {row['path']: row['sha256'] for row in c.read(packet)['files']}
    for name in ('deterministic.json', 'source-pins.json'):
        assert c.sha(c.PARENT / name) == records[name]
    expected = c.read(c.PARENT / 'deterministic.json')
    pins = c.read(c.PARENT / 'source-pins.json')
    sources = {name: c.sha(c.ROOT / name) for name in
               ('runtime/wasm32/hash.c', 'runtime/wasm32/hash-adapter.wat')}
    assert all(pins[name] == digest for name, digest in sources.items())
    runtime = out / 'runtime'
    runtime.mkdir(exist_ok=True)
    binaries = {}
    with tarfile.open(c.PARENT / 'execution.tar.gz') as archive:
        for name in ('hash.wasm', 'hash-adapter.wasm'):
            body = archive.extractfile(name).read()
            binaries[name] = hashlib.sha256(body).hexdigest()
            assert binaries[name] == expected[name]
            (runtime / name).write_bytes(body)
    c.save(out / 'hash-leaves.json', dict(sources=sources, binaries=binaries,
        reference=str(c.PARENT.name) + '/packet.json', packet=c.sha(packet)))
