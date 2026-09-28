#!/usr/bin/env python3
"""Compact reproducible products, preserving historical manifests and failures.

Dry-run is the default. --apply publishes a checked compaction manifest before
unlinking an original. Unpinned packs and live prerequisite packs are reported,
not guessed at. Git history is never rewritten.
"""
from pathlib import Path, PurePosixPath
import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[3]
STORE = ROOT.parent/'ccl-evidence'
LIMIT = 50_000_000
SUFFIXES = {'.wasm', '.wat', '.image', '.dx64fsl', '.fasl', '.w32fsl',
            '.w32bundle', '.o', '.a', '.dylib', '.so', '.pyc', '.bin'}
GENERATED_JSON = {'records.json', 'code-set.json', 'pools.json', 'moving-pools.json',
                  'materialized.json', 'modules.json'}
FAILURE = re.compile(r'(^|[/_-])(failure|failures|failing|mutant|mutants|refusal|refusals)([/_.-]|$)')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2)+'\n')


def regular_files(root):
    return sorted(p for p in root.rglob('*') if p.is_file() and not p.is_symlink()
                  and '.git' not in p.relative_to(root).parts)


def protected_packs():
    # Follow executable prerequisites, including retained restore scripts.
    names = {'macos-u1-inputs', 'shared-inputs', '2026-09-28-artifact-retention'}
    code = {'.py', '.mjs', '.lisp', '.sh'}
    pending = [p for base in (ROOT/'tests/wasm', ROOT/'doc/WASM/tools')
               for p in base.rglob('*') if p.suffix in code]
    seen = set()
    pattern = re.compile(r"(20\d\d-\d\d-\d\d-[\w-]+)(/[^\s\"'\)]+)?")
    while pending:
        p = pending.pop()
        if p in seen or p == Path(__file__).resolve() or not p.is_file(): continue
        seen.add(p)
        if p.name in ('packet.py', 'retain.py'): continue
        body = '\n'.join(line for line in p.read_text(errors='replace').splitlines() if 'artifactOrigin=' not in line)
        for match in pattern.finditer(body):
            name, suffix = match.group(1), match.group(2)
            if not (STORE/name).is_dir(): continue
            if suffix and Path(suffix).suffix in code:
                pending.append(STORE/name/suffix.lstrip('/'))
            elif suffix and (Path(suffix).suffix in ('.json','.md','.log') or suffix.endswith('.json.gz')):
                continue  # These original observations stay available.
            else: names.add(name)
    return names


def source_pin(pack):
    if (pack/'compaction.json').is_file():
        return json.loads((pack/'compaction.json').read_text())['source_commit']
    candidates = []
    paths=list(pack.iterdir())
    for name in ('build.json','environment.json','source.json','source-revision.json','unit.json','identity.json'):
        paths.extend(p for p in pack.glob('**/'+name) if len(p.relative_to(pack).parts)<=4)
    for p in dict.fromkeys(paths):
        if not p.is_file() or p.suffix not in ('.json', '.md') or p.stat().st_size > 64_000_000: continue
        for line in p.read_text(errors='replace').splitlines():
            if re.search(r'commit|revision|source.parent|source_parent|base_commit|git_head', line, re.I):
                candidates.extend(re.findall(r'(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])', line))
    for value in dict.fromkeys(candidates):
        if subprocess.run(['git', 'cat-file', '-e', value+'^{commit}'], cwd=ROOT,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return value
    return None


def generated(name):
    path = PurePosixPath(name)
    if any(x in ('sources', 'source', 'submitted', 'proposal', 'failure-inputs') for x in path.parts): return False
    return (path.suffix in SUFFIXES or path.name in GENERATED_JSON
            or path.name.endswith(('.records.json', '.sections.txt', '.instructions.txt'))
            or path.name in ('dx86cl64', 'namespace-compiler', 'control-dx86cl64'))


def archive_name(path):
    return path.name.endswith(('.tar.gz', '.tgz', '.tar'))


def candidates(pack):
    result = []
    for p in regular_files(pack):
        name = str(p.relative_to(pack))
        if name.startswith('compacted/') or FAILURE.search(name): continue
        if any(part in ('inputs', 'sources', 'source', 'proposal') for part in Path(name).parts): continue
        if generated(name) or archive_name(p): result.append(p)
    return result


def retain_stream(stream, name, size, stage, *, force=False):
    """Hash every byte. Keep text/results once; retain native expected data once."""
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts: raise ValueError('unsafe archive member: '+name)
    native = path.name == 'native.json'
    discard = generated(name) and not force and not FAILURE.search(name)
    temporary = stage/'member.tmp'
    h = hashlib.sha256()
    with temporary.open('wb') as out:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
            if not discard or native: out.write(block)
    digest = h.hexdigest()
    row = dict(sha256=digest, bytes=size)
    if native:
        dest = stage/'oracles'/(digest+'.json')
        dest.parent.mkdir(exist_ok=True)
        os.replace(temporary, dest)
        row['shared_input'] = 'shared-inputs/oracles/'+dest.name
    elif discard:
        temporary.unlink()
        row['regenerate'] = 'pinned source plus retained source deltas and build commands'
    else:
        # Deduplicate repeated sources/results within the deliverable. Large
        # result JSON is gzip data, never a tarball of compiler artifacts.
        suffix = path.suffix if path.suffix else '.data'
        compressed = size > 1_000_000 and suffix in ('.json', '.jsonl', '.log', '.txt', '.sexp')
        relative = 'files/'+digest+suffix+('.gz' if compressed else '')
        dest = stage/relative
        dest.parent.mkdir(exist_ok=True)
        if not dest.exists():
            if compressed:
                with temporary.open('rb') as source, gzip.GzipFile(filename=str(dest), mode='wb', mtime=0) as out:
                    shutil.copyfileobj(source, out)
            else: os.replace(temporary, dest)
        temporary.unlink(missing_ok=True)
        row['retained'] = 'compacted/'+relative
        row['encoding'] = 'gzip' if compressed else 'identity'
        row['stored_sha256'] = sha(dest)
        if not compressed and row['stored_sha256'] != digest:
            raise ValueError('retained copy changed: '+name)
        if compressed:
            with gzip.open(dest, 'rb') as check:
                if hashlib.file_digest(check, 'sha256').hexdigest() != digest:
                    raise ValueError('retained compression changed: '+name)
    return row


def compact(pack, pin, apply, selected=None):
    selected = candidates(pack) if selected is None else selected
    result = dict(pack=pack.name, source_commit=pin, candidates=len(selected),
                  candidate_bytes=sum(p.stat().st_size for p in selected))
    if not selected: return dict(result, status='NO_PRODUCTS')
    if not apply: return dict(result, status='PLANNED')
    previous = json.loads((pack/'compaction.json').read_text()) if (pack/'compaction.json').exists() else None
    if (pack/'compacted').exists() and previous is None: raise ValueError('compacted destination already exists')
    if previous and previous['source_commit'] != pin: raise ValueError('compaction source pin changed')
    stats = {p:p.stat() for p in selected}
    original_bytes = sum(p.stat().st_size for p in regular_files(pack))
    with tempfile.TemporaryDirectory(prefix='.compacting-', dir=STORE) as temporary:
        stage = Path(temporary)
        entries = dict(previous['original_files']) if previous else {}
        for p in selected:
            name = str(p.relative_to(pack))
            row = dict(sha256=sha(p), bytes=p.stat().st_size)
            if archive_name(p):
                members = {}
                with tarfile.open(p, 'r|*') as archive:
                    for member in archive:
                        part = PurePosixPath(member.name)
                        if part.is_absolute() or '..' in part.parts:
                            raise ValueError('unsafe archive member: '+member.name)
                        if member.isfile():
                            members[member.name] = retain_stream(archive.extractfile(member), member.name, member.size, stage)
                        elif member.issym() or member.islnk():
                            members[member.name] = dict(link=member.linkname)
                row['members'] = members
            else:
                # Individual generated files need only their already computed
                # identity; original result JSON and source files stay in place.
                row['regenerate'] = 'pinned source plus retained source deltas and build commands'
            entries[name] = row
        manifest = dict(version=1, source_commit=pin, original_files=entries,
                        original_manifests_preserved=True, rebuild_executed=False,
                        note='Historical manifests describe original artifacts. This manifest records their elision; no test verdict was changed.')
        save(stage/'compaction.json', manifest)
        remaining = original_bytes-result['candidate_bytes']
        retained_bytes = sum(p.stat().st_size for p in regular_files(stage) if 'oracles' not in p.relative_to(stage).parts)
        # Compaction may still make useful progress for a pack containing large
        # original failures. Report that exception explicitly; never discard
        # those failures to meet the cap.
        for p in (stage/'oracles').glob('*'):
            dest = STORE/'shared-inputs/oracles'/p.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                if sha(dest) != p.stem: raise ValueError('shared oracle changed')
            else: os.replace(p, dest)
        for p, before in stats.items():
            after = p.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError('original changed during compaction: '+str(p))
        if (stage/'files').exists():
            destination = pack/'compacted/files'
            destination.mkdir(parents=True,exist_ok=True)
            for source in (stage/'files').iterdir():
                dest = destination/source.name
                if dest.exists():
                    if sha(dest)!=sha(source):raise ValueError('compacted identity collision')
                else: os.replace(source,dest)
        os.replace(stage/'compaction.json', pack/'compaction.json')
        # Publish verified replacements before removing originals. A partial
        # interruption leaves redundant originals, never lost observations.
        for p in selected: p.unlink()
        final_bytes = sum(p.stat().st_size for p in regular_files(pack))
        return dict(result, status='COMPACTED' if final_bytes <= LIMIT else 'COMPACTED_WITH_RETAINED_EXCESS',
                    before_bytes=original_bytes, after_bytes=final_bytes,
                    removed_bytes=original_bytes-final_bytes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--pack', action='append')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    protected = protected_packs()
    rows = []
    packs = [STORE/n for n in args.pack] if args.pack else sorted(p for p in STORE.iterdir() if p.is_dir() and not p.name.startswith('.'))
    for pack in packs:
        if pack.parent != STORE or pack.is_symlink(): raise ValueError('invalid pack')
        if pack.name in protected:
            rows.append(dict(pack=pack.name, status='REQUIRED_INPUT')); continue
        pin = source_pin(pack)
        if pin is None:
            rows.append(dict(pack=pack.name, status='NO_SOURCE_COMMIT')); continue
        try: row = compact(pack, pin, args.apply)
        except (ValueError, tarfile.TarError, OSError) as error:
            row = dict(pack=pack.name, status='PRESERVED_ON_ERROR', error=str(error))
        rows.append(row)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        save(args.report, dict(apply=args.apply, packs=rows))
        if row['status'].startswith('COMPACTED'): print(json.dumps(row), flush=True)
    save(args.report, dict(apply=args.apply, packs=rows,
                          removed_bytes=sum(r.get('removed_bytes', 0) for r in rows)))
    print(json.dumps(dict(packs=len(rows), statuses={s:sum(r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})},
                          removed_bytes=sum(r.get('removed_bytes', 0) for r in rows))))


if __name__ == '__main__': main()
