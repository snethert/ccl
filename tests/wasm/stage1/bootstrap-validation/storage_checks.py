"""Destructive-cleanup controls run only in a fresh disposable test root."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
import common as c
import storage as s


def check(output):
    output=Path(output);output.mkdir()
    checks=[]
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        t=Path(temporary);root=t/'work';cache=t/'cache';now=time.time()
        stale=root/'author'/'stale';active=root/'reviewer'/'active'
        for work in (stale,active):
            work.mkdir(parents=True)
            c.save(work/'.workspace.json',dict(uid=os.getuid(),last_used=now-90000))
            (work/'data').write_text('disposable')
        unmanaged=root/'reviewer'/'unmanaged';unmanaged.mkdir()
        outside=t/'outside';outside.mkdir();(outside/'precious').write_text('keep')
        (root/'author'/'alias').symlink_to(outside,target_is_directory=True)
        (root/'alias-agent').symlink_to(outside,target_is_directory=True)
        # A different process attempts GC while a live command holds its lease.
        with s.lease([active],cache,root):
            c.save(active/'.workspace.json',dict(uid=os.getuid(),last_used=now-90000))
            code=('import storage; storage.gc('+repr(str(cache))+','+repr(str(root))+')')
            subprocess.run([sys.executable,'-c',code],cwd=c.HERE,check=True)
            assert active.exists() and not stale.exists()
        assert unmanaged.exists() and (outside/'precious').read_text()=='keep'
        checks+=['active-workspace-survives','expired-workspace-removed','unmanaged-preserved','symlink-preserved']
        for n in range(4):
            p=cache/'session'/str(n);p.mkdir(parents=True)
            (p/'data').write_bytes(b'x');os.utime(p,(now-n,now-n))
        for n in range(3):
            p=cache/'wabt'/str(n);p.mkdir(parents=True)
            (p/'data').write_bytes(b'x'*6);os.utime(p,(now-n,now-n))
        limit=s.WABT_BYTES;s.WABT_BYTES=12
        try:s.gc(cache,root,now)
        finally:s.WABT_BYTES=limit
        assert sorted(p.name for p in (cache/'session').iterdir())==['0','1']
        assert sorted(p.name for p in (cache/'wabt').iterdir())==['0','1']
        checks+=['newest-two-sessions','wabt-byte-bound']
        with s.lease([active],cache,root):
            result=s.gc(cache,root,now)
            assert str(cache) in result['skipped_active']
        checks.append('active-cache-skips-trimming')
        run=active/'run';run.mkdir()
        (run/'oracle.json').write_text('{"answer":42}\n')
        (run/'module.wasm').write_bytes(b'\0asm')
        binary_hash=c.sha(run/'module.wasm')
        (run/'failure.log').write_text('original failure')
        target=t/'retained'
        s.finish(run,target,root)
        assert not run.exists()
        record=c.read(target/'retention.json');c.verify_files(target,record['files'])
        assert record['rebuildable']['module.wasm']==binary_hash
        assert not (target/'module.wasm').exists()
        assert (target/'failure.log').read_text()=='original failure'
        checks+=['retention-before-deletion','failure-preserved','binary-referenced']
        run.mkdir();(run/'sentinel').write_text('keep on refusal')
        try:s.finish(run,target,root)
        except ValueError:pass
        else:raise AssertionError('overwrote evidence')
        assert (run/'sentinel').is_file()
        original=s.shutil.copyfile
        def corrupt(source,destination):
            result=original(source,destination)
            Path(destination).write_text('corrupt copy')
            return result
        s.shutil.copyfile=corrupt
        try:
            try:s.finish(run,t/'bad-copy',root)
            except ValueError:pass
            else:raise AssertionError('corrupt retention admitted')
        finally:s.shutil.copyfile=original
        assert (run/'sentinel').read_text()=='keep on refusal'
        assert not (t/'bad-copy').exists()
        checks.append('corrupt-retention-preserves-source')
        for forbidden in (root,root/'author',outside,root/'author'/'alias'/'run'):
            try:s.workspace(forbidden,root)
            except ValueError:pass
            else:raise AssertionError('unsafe output admitted: '+str(forbidden))
        checks+=['existing-evidence-refused-with-output-preserved','unsafe-paths-refused']
    result=dict(status='PASS',checks=checks)
    c.save(output/'storage-checks.json',result);return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
    with s.lease([a.output]):print(check(a.output))
