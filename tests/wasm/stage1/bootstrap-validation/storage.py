"""Disposable workspaces and bounded caches, with cross-process GC leases."""
from contextlib import contextmanager, ExitStack
from pathlib import Path
import fcntl
import os
import shutil
import tempfile
import time
import subprocess
import plistlib
import common as c

WORK_ROOT = Path('/private/tmp/ccl-work')
MAX_AGE = 24 * 60 * 60
WABT_BYTES = 2 * 1024**3


def ensure_ram():
    def mounted():
        images = plistlib.loads(subprocess.check_output(
            ['/usr/bin/hdiutil', 'info', '-plist']))['images']
        for image in images:
            if image.get('image-path') != 'ram://33554432' or image.get('owner-uid') != os.getuid():
                continue
            devices = {e['dev-entry'] for e in image['system-entities']}
            for path in (WORK_ROOT, c.DEFAULT_CACHE):
                if not os.path.ismount(path): break
                info = plistlib.loads(subprocess.check_output(
                    ['/usr/sbin/diskutil', 'info', '-plist', str(path)]))
                if info.get('DeviceNode') not in devices or info.get('MountPoint') != str(path): break
            else: return True
        return False
    if mounted(): return
    helper = Path.home()/'Library/Application Support/CCLBuildRAMDisk/ramdisk.py'
    subprocess.run(['/usr/bin/python3', str(helper)], check=True,
                   stdout=subprocess.DEVNULL, timeout=60)
    if not mounted(): raise ValueError('CCL work and cache must share the 16 GiB RAM image')


def reset_run(output, root=WORK_ROOT):
    """Reuse a purpose's output while the caller holds its workspace lease."""
    output = Path(output)
    workspace(output, root)
    if output.exists() and any(output.iterdir()):
        marker = output/'.run.json'
        if not marker.exists() or c.read(marker).get('status') not in ('PASS', 'BUILT'):
            raise ValueError('retain unfinished run before reusing its directory: '+str(output))
        if any(c.read(p) for p in output.rglob('failure-inputs.json')):
            raise ValueError('retain original failure inputs before reusing: '+str(output))
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    c.save(output/'.run.json', dict(status='RUNNING'))


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
    if Path(root) == WORK_ROOT: ensure_ram()
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
        for kind in ('session', 'compiler', 'wabt', 'binary', 'failures'):
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
                elif kind in ('session','compiler'):
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
    """Publish verified review evidence before removing the run."""
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
        import artifacts
        result = artifacts.snapshot(output, temporary, oracle_store=c.STORE/'shared-inputs/oracles')
        os.rename(temporary, destination)
    finally:
        if temporary.exists(): shutil.rmtree(temporary)
    shutil.rmtree(output)
    return dict(status='PASS', retained=str(destination), removed=str(output),
                **result)
