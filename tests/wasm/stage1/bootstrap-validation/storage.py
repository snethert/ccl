"""Disposable workspaces and bounded caches, with cross-process GC leases."""
from contextlib import contextmanager, ExitStack
from pathlib import Path
import fcntl
import os
import shutil
import tempfile
import time
import common as c

WORK_ROOT = Path('/private/tmp/ccl-work')
MAX_AGE = 24 * 60 * 60
WABT_BYTES = 2 * 1024**3


def workspace(path, root=WORK_ROOT):
    path, root = Path(path).absolute(), Path(root).resolve()
    resolved = path.resolve()
    try:
        parts = resolved.relative_to(root).parts
    except ValueError:
        raise ValueError('output must be under ' + str(root)) from None
    if len(parts) < 2 or any(part.startswith('.') for part in parts[:2]):
        raise ValueError('output needs an agent and packet directory')
    # Never follow an output alias into another agent or packet.
    if path != resolved:
        raise ValueError('output path must be canonical, without symlinks: ' + str(path))
    return root / parts[0] / parts[1]


@contextmanager
def lock(path, exclusive=False, blocking=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+') as stream:
        flags = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        try:
            fcntl.flock(stream, flags | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def work_lock(path, root=WORK_ROOT):
    return Path(root) / '.locks' / (c.digest(str(path)) + '.lock')


@contextmanager
def lease(paths=(), cache=c.DEFAULT_CACHE, root=WORK_ROOT):
    """Hold for the entire command, including subprocesses and cache copies."""
    with ExitStack() as stack:
        stack.enter_context(lock(Path(cache)/'.gc.lock'))
        for work in sorted({workspace(p, root) for p in paths}):
            stack.enter_context(lock(work_lock(work, root), exclusive=True))
            work.mkdir(parents=True, exist_ok=True)
            marker = work/'.workspace.json'
            c.save(marker, dict(version=1, uid=os.getuid(), last_used=time.time()))
        yield


def size(path):
    return sum(p.stat().st_size for p in Path(path).rglob('*')
               if p.is_file() and not p.is_symlink())


def gc(cache=c.DEFAULT_CACHE, root=WORK_ROOT, now=None):
    now = time.time() if now is None else now
    root, cache = Path(root), Path(cache)
    if root.is_symlink() or cache.is_symlink():
        raise ValueError('GC roots must not be symlinks')
    result = dict(deleted=[], skipped_active=[], skipped_unmanaged=[], bytes_removed=0)
    for work in sorted(root.glob('*/*')):
        if (work.parent.name.startswith('.') or work.parent.is_symlink()
                or work.is_symlink() or not work.is_dir()):
            continue
        marker = work/'.workspace.json'
        if not marker.is_file() or c.read(marker).get('uid') != os.getuid():
            result['skipped_unmanaged'].append(str(work)); continue
        with lock(work_lock(work, root), exclusive=True, blocking=False) as acquired:
            if not acquired:
                result['skipped_active'].append(str(work)); continue
            if now - c.read(marker)['last_used'] < MAX_AGE:
                continue
            result['bytes_removed'] += size(work)
            shutil.rmtree(work); result['deleted'].append(str(work))
    with lock(cache/'.gc.lock', exclusive=True, blocking=False) as acquired:
        if not acquired:
            result['skipped_active'].append(str(cache)); return result
        for kind in ('session', 'wabt', 'failures'):
            if (cache/kind).is_symlink():
                result['skipped_unmanaged'].append(str(cache/kind));continue
            entries = sorted((p for p in (cache/kind).glob('*')
                              if p.is_dir() and not p.is_symlink()),
                             key=lambda p:p.stat().st_mtime, reverse=True)
            kept, used = 0, 0
            for entry in entries:
                stale = now - entry.stat().st_mtime >= MAX_AGE
                if entry.name.startswith('.') or kind == 'failures':
                    remove = stale
                elif kind == 'session':
                    remove = kept >= 2
                    kept += 1
                else:
                    amount = size(entry)
                    remove = used + amount > WABT_BYTES
                    if not remove: used += amount
                if remove:
                    result['bytes_removed'] += size(entry)
                    shutil.rmtree(entry); result['deleted'].append(str(entry))
    return result


def finish(output, destination, root=WORK_ROOT):
    """Publish review evidence atomically; then remove the disposable output.

    Keep all text/JSON inputs and logs, plus hashes for regenerable binaries.
    This is an evidence bundle, not a claim that old restore supports elision.
    """
    output, destination = Path(output).resolve(), Path(destination).resolve()
    work = workspace(output, root)
    if output == work:
        raise ValueError('finalize a run directory, not the workspace root')
    if destination == output or output in destination.parents or destination in output.parents:
        raise ValueError('retained destination overlaps disposable output')
    if destination.exists(): raise ValueError('retained destination exists')
    if not output.is_dir(): raise ValueError('missing output')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.retaining-', dir=destination.parent))
    try:
        hashes = c.inventory(output)
        references = {}
        for name, digest in hashes.items():
            p = output/name
            if p.suffix in ('.wasm', '.image', '.dx64fsl', '.fasl', '.wat'):
                references[name] = digest
            else:
                target = temporary/name; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, target)
        saved = c.inventory(temporary)
        c.verify_files(temporary, saved)
        # Check against the ORIGINAL inventory, not hashes of the copies alone.
        if any(hashes[name] != digest for name, digest in saved.items()):
            raise ValueError('retention copy differs')
        c.save(temporary/'retention.json', dict(version=1, files=saved,
               rebuildable=references, source=str(output), execution_rebuilt=False))
        os.rename(temporary, destination)
    finally:
        if temporary.exists(): shutil.rmtree(temporary)
    shutil.rmtree(output)
    return dict(status='PASS', retained=str(destination), removed=str(output),
                retained_files=len(saved), referenced_files=len(references))
