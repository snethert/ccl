#!/usr/bin/env python3
"""Query retained census observations or witness one native call site."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile
import traceback
from native import digest, save, execute
from capture import query

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
U1 = 'c994217adc56b3f8a564526cee4695893ac84d86'


def relative(name):
    p = Path(name)
    if p.is_absolute() or '..' in p.parts: raise ValueError('expected a source-relative path')
    return p


def prepare(evidence, work, source_archive=None):
    inputs = evidence / 'macos-u1-inputs'
    pins = json.loads((inputs / 'pins.json').read_text())
    if pins['source_revision'] != U1: raise ValueError('pristine U1 revision required')
    archive = source_archive or inputs / 'source.tar'
    bootstrap = inputs / 'bootstrap.tar.gz'
    kernel = evidence / '2026-09-12-native-census-r7/baseline/build/dx86cl64'
    identities = dict(source=digest(archive), bootstrap=digest(bootstrap), kernel=digest(kernel))
    if identities['source'] != pins['inputs']['source.tar'] or identities['bootstrap'] != pins['inputs']['bootstrap.tar.gz']:
        raise ValueError('U1 input archive identity differs')
    marker = work / 'prepared.json'
    if work.exists():
        if not marker.is_file() or json.loads(marker.read_text())['inputs'] != identities:
            raise ValueError('work directory is not this query tool\'s prepared U1 copy')
    else:
        work.mkdir(parents=True)
        source = work / 'ccl'; source.mkdir()
        for path in (archive, bootstrap):
            with tarfile.open(path) as data: data.extractall(source, filter='data')
        shutil.copyfile(kernel, source / 'dx86cl64'); (source / 'dx86cl64').chmod(0o755)
        save(marker, dict(version=1, source_revision=U1, inputs=identities,
                          scope='Disposable observation only; never an implementation baseline.'))
    source = work / 'ccl'
    if digest(source / 'dx86cl64') != identities['kernel']: raise ValueError('prepared kernel changed')
    with tarfile.open(bootstrap) as data:
        image = data.extractfile('dx86cl64.image')
        if image is None or hashlib.file_digest(image, 'sha256').hexdigest() != digest(source / 'dx86cl64.image'):
            raise ValueError('prepared bootstrap image changed')
    with tarfile.open(archive) as data:
        if data.extractfile('lib/x8664env.lisp').read() != (source / 'lib/x8664env.lisp').read_bytes():
            raise ValueError('prepared compiler environment changed')
    return source, archive


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence', type=Path, default=ROOT.parent / 'ccl-evidence')
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('query', help='Answer a structured question from a retained capture')
    q.add_argument('--capture', type=Path, required=True, help='Retained packet.json')
    q.add_argument('--question', type=Path, required=True, help='JSON question; see README.md')
    q.add_argument('--cache', type=Path, required=True, help='Reusable, content-bound SQLite index')
    q.add_argument('--output', type=Path, required=True)
    for name in ('sites', 'probe'):
        q = sub.add_parser(name)
        q.add_argument('--source-archive', type=Path, help='Optional pristine U1 source archive; defaults to retained input')
        q.add_argument('--work', type=Path, required=True)
        q.add_argument('--source', required=True, help='Source path relative to U1')
        q.add_argument('--function', required=True, help='Package-qualified DEFUN name')
        q.add_argument('--output', type=Path, required=True)
        q.add_argument('--timeout', type=int, default=120)
        if name == 'probe':
            q.add_argument('--selection', type=Path, required=True, help='One exact selection object from sites answer.json')
            q.add_argument('--scenario', type=Path, required=True, help='Lisp lambda receiving the recompiled function')
            q.add_argument('--event-limit', type=int, default=10000)
    a = p.parse_args(); a.output = a.output.resolve()
    if a.output.exists(): p.error('output already exists; preserve earlier runs and choose a fresh directory')
    try:
        if a.command == 'query':
            a.output.mkdir(parents=True)
            question = json.loads(a.question.read_text())
            answer = query(a.capture.resolve(), a.cache.resolve(), question)
            save(a.output / 'question.json', question)
            save(a.output / 'answer.json', answer)
        else:
            source_root, archive = prepare(a.evidence.resolve(), a.work.resolve(), a.source_archive)
            source = source_root / relative(a.source)
            with tarfile.open(archive) as data:
                stream = data.extractfile(a.source)
                if stream is None or source.read_bytes() != stream.read(): raise ValueError('requested source no longer equals U1')
            selection = json.loads(a.selection.read_text()) if a.command == 'probe' else None
            answer = execute(source_root, source, a.function, source_root / 'dx86cl64.image',
                source_root / 'dx86cl64', a.output, scenario=a.scenario.resolve() if a.command == 'probe' else None,
                selection=selection, timeout=a.timeout, limit=a.event_limit if a.command == 'probe' else 10000)
            save(a.output / 'u1-inputs.json', json.loads((a.work / 'prepared.json').read_text()))
        print(json.dumps(dict(status=answer['status'], kind=answer['kind'], answer=str(a.output / 'answer.json'))))
        return 2 if answer['status'] in ('TRUNCATED', 'NOT_REACHED', 'NOT_OBSERVED') else 0
    except BaseException:
        a.output.mkdir(parents=True, exist_ok=True)
        (a.output / 'failure.txt').write_text(traceback.format_exc())
        for name in ('run.py', 'native.py', 'capture.py', 'site-probe.lisp'):
            shutil.copyfile(HERE / name, a.output / ('failed-' + name))
        raise


if __name__ == '__main__': sys.exit(main())
