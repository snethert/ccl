"""Fresh U1 archive and read-only native image; no compiler/kernel patch."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)


def save(path, value):
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()
    path.write_bytes(gzip.compress(raw, mtime=0) if path.suffix=='.gz' else raw)


def prepare(store, work):
    require(platform.system()=='Darwin' and platform.machine()=='x86_64', 'MACOS_X8664')
    pins = read(HERE/'inputs.json')
    work.mkdir(parents=True, exist_ok=False)
    source = work/'ccl'; source.mkdir()
    for name, pin in pins['inputs'].items():
        require(digest(store/pin['path'])==pin['sha256'], 'INPUT '+name)
    with tarfile.open(store/pins['inputs']['source']['path']) as archive:
        archive.extractall(source, filter='data')
    with tarfile.open(store/pins['inputs']['bootstrap']['path']) as archive:
        archive.extract(archive.getmember(pins['image_member']), source, filter='data')
    shutil.copyfile(store/pins['inputs']['kernel']['path'], source/'dx86cl64')
    (source/'dx86cl64').chmod(0o755)
    require(digest(source/pins['image_member'])==pins['image_sha256'], 'BOOTSTRAP_IMAGE')
    return source


def execute(source, out, mode, independent=False):
    capture = out/(mode+'.json')
    argv = [str(source/'dx86cl64'), '--no-init', '--batch',
            '--load', str(HERE.parent/'observer.lisp'), '--load', str(HERE/'inspect.lisp'),
            '--eval', '(progn (ccl-dispatch-registry::export-state '+json.dumps(str(capture))+') (ccl:quit))']
    if independent:
        argv = [str(source/'dx86cl64'), '--no-init', '--batch', '--load', str(HERE/'removal-probe.lisp')]
    env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin', LANG='C', LC_ALL='C',
               CCL_DEFAULT_DIRECTORY=str(source))
    report = dict(argv=argv, environment=env, cwd=str(source), timeout_seconds=60)
    save(out/(mode+'-command.json'), report)
    try:
        with (out/(mode+'.log')).open('wb') as log:
            child = subprocess.Popen(argv, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                rc = child.wait(timeout=60)
            except BaseException:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait(); raise
        report['exit_code'] = rc
        marker = ('NATIVE-EMPTY-METHOD-ESCAPE methods=0 retained-dcode=true before=10,11 after=10,11'
                  if independent else 'DISPATCH-REGISTRY-PASS')
        require(rc==0 and marker in (out/(mode+'.log')).read_text(), 'NATIVE_EXECUTION '+mode)
        if independent:
            return dict(status='KNOWN_NATIVE_DEFECT_REPRODUCED', marker=marker)
        data = capture.read_bytes()
        (out/(mode+'.json.gz')).write_bytes(gzip.compress(data, mtime=0))
        return json.loads(data)
    finally:
        save(out/(mode+'-command.json'), report)


def source_files():
    return sorted(HERE.glob('*.py'))+sorted(HERE.glob('*.lisp'))+[HERE/'inputs.json', HERE.parent/'observer.lisp']+[
        ROOT/p for p in ('library/lispequ.lisp', 'level-1/l1-dcode.lisp', 'level-1/l1-clos.lisp',
                         'level-1/l1-clos-boot.lisp', 'level-0/X86/x86-clos.lisp')]


def capture(args):
    out = args.output.resolve(); work = args.work.resolve(); store = args.evidence.resolve()
    require(all(a!=b and a not in b.parents and b not in a.parents for a,b in ((out,work),(out,store),(work,store))), 'SEPARATE_PATHS')
    require(ROOT not in work.parents and ROOT not in out.parents, 'DISPOSABLE_PATHS')
    out.mkdir(parents=True, exist_ok=False)
    report = dict(status='FAIL', timestamp=datetime.now(timezone.utc).isoformat(), command=sys.argv,
                  inputs=read(HERE/'inputs.json'), source_sha256={str(p.relative_to(ROOT)):digest(p) for p in source_files()})
    for p in source_files():
        dest = out/'sources'/p.relative_to(ROOT); dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(p,dest)
    save(out/'run.json',report)
    try:
        source = prepare(store,work)
        first = execute(source,out,'first')
        second = execute(source,out,'repeat')
        require((out/'first.json').read_bytes()==(out/'repeat.json').read_bytes(), 'NATIVE_REPRODUCTION')
        independent = execute(source,out,'independent',True)
        save(out/'independent.json',independent)
        pins = report['inputs']
        require(digest(source/'dx86cl64')==pins['inputs']['kernel']['sha256']
                and digest(source/pins['image_member'])==pins['image_sha256'], 'NATIVE_INPUT_CHANGED')
        report.update(status='PASS', native_sessions=3, byte_identical=True, shared_source_changes=False,
                      registry_rows=len(first['registry']), functions=len(first['functions']))
        return first, report
    except BaseException:
        (out/'failure.txt').write_text(traceback.format_exc()); raise
    finally:
        save(out/'run.json',report)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('evidence','work','output'):
        p.add_argument('--'+name,type=Path,required=True)
    capture(p.parse_args())
