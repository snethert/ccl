"""Bound inputs and atomic, content-addressed validation caches."""
from pathlib import Path
from contextlib import contextmanager
import errno
import hashlib
import gzip
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import threading

FAILURE_LOCK = threading.Lock()

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STORE = ROOT.parent / 'ccl-evidence'
PARENT = STORE / '2026-09-23-stage1-class-growth-r1'
NODE = Path('/usr/local/bin/node')
WABT = Path('/usr/local/bin/wat2wasm')
KERNEL = STORE / '2026-09-12-native-census-r7/baseline/build/dx86cl64'
IMAGE = STORE / '2026-09-16-stage1-1a-r2/native/baseline.image'
FLAGS = ['--enable-threads', '--enable-exceptions', '--enable-tail-call']
DEFAULT_CACHE = Path.home() / 'Library/Caches/ccl-wasm-validation'


def sha(path):
    h = hashlib.sha256()
    path = Path(path)
    stream = path.open('rb') if path.is_file() else gzip.open(path.with_name(path.name+'.gz'),'rb')
    with stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read(path):
    path = Path(path)
    if path.suffix == '.gz':
        with gzip.open(path,'rt') as stream:return json.load(stream)
    if not path.is_file():
        with gzip.open(path.with_name(path.name+'.gz'),'rt') as stream:return json.load(stream)
    return json.loads(path.read_text())


def exists(path):
    path = Path(path)
    return path.is_file() or path.with_name(path.name+'.gz').is_file()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write('\n')
        temporary = Path(stream.name)
    os.replace(temporary, path)


def files(path):
    return sorted(p for p in Path(path).rglob('*') if p.is_file() and '__pycache__' not in p.parts)


def inventory(path):
    return {str(p.relative_to(path)): sha(p) for p in files(path) if p.name != 'cache-manifest.json'}


def verify_files(root, hashes):
    for name, expected in hashes.items():
        path = Path(root) / name
        if not path.is_file() or sha(path) != expected:
            raise ValueError('artifact identity: ' + str(path))


def clone(source, destination, **options):
    """Copy mutable run inputs; reference the two large, immutable inputs."""
    source = Path(source).resolve()
    def copy(src, dst):
        src, dst = Path(src), Path(dst)
        if src.name in ('compiler.image', 'native.json'):
            if dst.exists() or dst.is_symlink(): dst.unlink()
            dst.symlink_to(src.resolve())
            return str(dst)
        return shutil.copyfile(src, dst)
    return shutil.copytree(source, destination, copy_function=copy,
                           symlinks=True, **options)


def wat_digest(out, name):
    path = Path(out)/'compiled'/name
    if path.exists(): return sha(path)
    for row in read(Path(out)/'assembly.json')['rows']:
        if row['name'] == name: return row['identity']['wat']
    raise ValueError('missing assembly identity: '+name)


def restore_wat(entry, destination, names):
    """Export exact diagnostic WAT from the shared checkpoint, without compiling."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    names = sorted(set(names))
    if any(Path(n).name != n or not n.endswith('.wat') for n in names):
        raise ValueError('invalid diagnostic module name')
    request = destination/'wat-request.lisp'
    request.write_text('('+ ' '.join(json.dumps(n[:-4]) for n in names) +')\n')
    try:
        with tempfile.TemporaryDirectory(prefix='wat-export-', dir=destination) as temporary:
            kernel = Path(temporary)/'dx86cl64'
            shutil.copyfile(KERNEL, kernel);kernel.chmod(0o755)
            command([kernel, '-I', Path(entry)/'compiled/compiler.image', '--no-init',
                     '--batch', '--load', HERE/'restore-wat.lisp'],
                    destination/'restore-wat.log',
                    dict(os.environ, CCL_DEFAULT_DIRECTORY=str(ROOT)+'/',
                         WAT_OUTPUT=str(destination)+'/', WAT_REQUEST=str(request)))
        expected = {r['name']:r['identity']['wat'] for r in read(Path(entry)/'assembly.json')['rows']}
        verify_files(destination, {name:expected[name] for name in names})
    finally:
        request.unlink(missing_ok=True)


def parent_inputs():
    if sha(PARENT/'packet.json') != '509d916f2255a6707c3779744240f7a025b6a4499ca45e69c4e52100659d05a1':
        raise ValueError('parent packet identity')
    rows = {r['path']: r['sha256'] for r in read(PARENT/'packet.json')['files']}
    for name in ('review-artifacts.json', 'review-artifacts.tar.gz', 'execution.tar.gz',
                 'deterministic.json', 'source-pins.json', 'dependencies.json'):
        if sha(PARENT/name) != rows[name]:
            raise ValueError('parent packet: '+name)
    return rows


def extract(archive, target, predicate=lambda name: True):
    with tarfile.open(archive) as stream:
        for member in stream:
            if not member.isfile() or not predicate(member.name):
                continue
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('archive path: '+member.name)
            destination = target/path
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('wb') as output:
                shutil.copyfileobj(stream.extractfile(member), output)


def cache_read(cache, kind, key):
    path = Path(cache)/kind/key
    if not path.exists():
        return None
    manifest = read(path/'cache-manifest.json')
    if manifest['key'] != key or manifest['kind'] != kind:
        raise ValueError('cache identity: '+str(path))
    actual_names = {str(p.relative_to(path)) for p in files(path) if p.name != 'cache-manifest.json'}
    if actual_names != set(manifest['files']):
        raise ValueError('cache inventory: '+str(path))
    verify_files(path, manifest['files'])
    os.utime(path, None)
    return path


@contextmanager
def cache_write(cache, kind, key):
    parent = Path(cache)/kind
    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.building-', dir=parent))
    try:
        yield stage
        for path in files(stage):
            if path.name in ('compiler.image', 'native.json') and not path.is_symlink():
                path.chmod(0o444)
        save(stage/'cache-manifest.json', dict(kind=kind, key=key, files=inventory(stage)))
        destination = parent/key
        if destination.exists():
            # A concurrent writer must have produced the same deterministic
            # entry. Session images may have source-position differences;
            # their environment identity still must match and be intact.
            cache_read(cache, kind, key)
        else:
            try:
                os.rename(stage, destination)
            except OSError as error:
                if error.errno not in (errno.EEXIST,errno.ENOTEMPTY):raise
                cache_read(cache,kind,key)
    except BaseException:
        failure = Path(cache)/'failures'/stage.name
        failure.parent.mkdir(parents=True, exist_ok=True)
        if stage.exists():
            import artifacts
            try:
                artifacts.snapshot(stage, failure)
            except BaseException:
                # An unclassified failure cannot be silently thrown away.
                shutil.rmtree(failure, ignore_errors=True)
                os.rename(stage, failure)
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def command(argv, log, env=None, cwd=None, timeout=600):
    start = time.monotonic()
    with Path(log).open('w') as stream:
        subprocess.run([str(x) for x in argv], cwd=cwd, env=env,
                       stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=timeout)
    return time.monotonic()-start


def assembly_key(path):
    return dict(wat=sha(path), tool=sha(WABT), flags=FLAGS)


def assemble(path, cache, cold=False, discard=True):
    path = Path(path)
    identity = assembly_key(path)
    key = digest(identity)
    hit = cache_read(cache, 'wabt', key)
    if hit is None or cold:
        with cache_write(cache, 'wabt', key) as stage:
            try:
                seconds = command([WABT, *FLAGS, path, '-o', stage/'module.wasm'], stage/'wabt.log')
            except BaseException:
                with FAILURE_LOCK:
                    marker = path.parent/'failure-inputs.json'
                    names = read(marker) if marker.exists() else []
                    save(marker, sorted(set(names+[path.name])))
                raise
            save(stage/'identity.json', identity)
            if hit and sha(hit/'module.wasm') != sha(stage/'module.wasm'):
                raise ValueError('non-reproducible WABT output')
            # Logs/timings do not participate in output equivalence.
        hit = cache_read(cache, 'wabt', key)
        rebuilt = True
    else:
        seconds, rebuilt = 0, False
    shutil.copyfile(hit/'module.wasm', path.with_suffix('.wasm'))
    result = dict(name=path.name, key=key, identity=identity,
                  wasm=sha(hit/'module.wasm'), rebuilt=rebuilt, seconds=seconds)
    if discard: path.unlink()
    return result
