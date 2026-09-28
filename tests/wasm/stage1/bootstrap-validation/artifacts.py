"""Small review evidence and explicit references for disposable products."""
from pathlib import Path
import json
import gzip
import hashlib
import os
import shutil
import tempfile
import common as c

PACK_BYTES = 50_000_000
PRODUCT_SUFFIXES = {'.wasm', '.image', '.dx64fsl', '.fasl', '.w32fsl',
                    '.w32bundle', '.o', '.dylib', '.so', '.pyc'}


def shared_oracle(path, store=None):
    store = Path(store) if store else c.STORE/'shared-inputs/oracles'
    digest = c.sha(path)
    target = store/(digest+'.json');store.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if c.sha(target)!=digest: raise ValueError('shared oracle identity')
    else:
        with tempfile.NamedTemporaryFile(dir=store,delete=False) as stream:
            temporary=Path(stream.name)
        try:
            shutil.copyfile(path,temporary)
            if c.sha(temporary)!=digest:raise ValueError('oracle copy identity')
            os.replace(temporary,target)
        finally:temporary.unlink(missing_ok=True)
    return dict(sha256=digest,shared_input=str(target))


def records_summary(path):
    value = c.read(path)
    units = value.get('units', []) if isinstance(value, dict) else value
    def count(record):
        return 1 + sum(count(r) for r in (record[8] or [])) if len(record) > 8 else 1
    return dict(sha256=c.sha(path), bytes=path.stat().st_size, units=len(units),
                records=sum(count(u['record']) for u in units if 'record' in u))


def explicit_failures(root):
    names = set()
    for manifest in root.rglob('failure-inputs.json'):
        for name in c.read(manifest):
            path = manifest.parent/name
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                raise ValueError('failure input escapes run: '+name)
            if not path.is_file(): raise ValueError('missing failure input: '+name)
            names.add(str(path.relative_to(root)))
    return names


def product(name):
    path = Path(name)
    return (path.suffix in PRODUCT_SUFFIXES or path.suffix == '.wat'
            or path.name.endswith(('.records.json', '.instructions.txt', '.sections.txt', '.census-wat'))
            or path.name in ('records.json', 'native.json', 'dx86cl64', 'code-set.json',
                             'pools.json', 'moving-pools.json', 'materialized.json'))


def check_size(root):
    # The user's 50 MB figure is a guideline, not a publication gate.
    return sum(p.stat().st_size for p in c.files(root))


def snapshot(source, target, *, oracle_store=None):
    """Copy sources/results/failures, with an inventory of every elided file.

    The caller publishes target atomically. Never alters the source. Failure
    inputs are declared by relative path; failure-inputs/ is also preserved.
    """
    source, target = Path(source), Path(target)
    target.mkdir(parents=True, exist_ok=True)
    failures = explicit_failures(source)
    kept, references, records, compressed = {}, {}, {}, {}
    for p in c.files(source):
        name = str(p.relative_to(source))
        parts = Path(name).parts
        digest = c.sha(p)
        failure = name in failures or 'failure-inputs' in parts
        is_source = any(part in ('source', 'sources', 'driver', 'proposal', 'submitted') for part in parts)
        omit = product(name) and not failure and not (is_source and p.suffix == '.wat')
        if p.name.endswith(('.tar.gz', '.tar', '.zip', '.tgz')):
            raise ValueError('expand archive before retaining evidence: '+name)
        if omit:
            row = dict(sha256=digest, bytes=p.stat().st_size)
            if p.name.endswith('.records.json') or p.name == 'records.json':
                records[name] = records_summary(p)
            if p.name == 'native.json' and oracle_store is not None:
                row.update(shared_oracle(p,oracle_store))
            references[name] = row
        else:
            dest = target/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if p.stat().st_size > 131072 and p.suffix in ('.json','.jsonl','.log','.txt','.sexp','.lisp','.mjs','.py','.c','.h','.wat'):
                dest = dest.with_name(dest.name+'.gz')
                with p.open('rb') as source_stream, gzip.GzipFile(filename=str(dest),mode='wb',mtime=0) as stream:
                    shutil.copyfileobj(source_stream,stream)
                with gzip.open(dest,'rb') as stream:
                    if hashlib.file_digest(stream,'sha256').hexdigest()!=digest:
                        raise ValueError('retention compression differs: '+name)
                compressed[name] = dict(file=name+'.gz',sha256=digest,bytes=p.stat().st_size)
                kept[name+'.gz'] = c.sha(dest)
            else:
                shutil.copyfile(p, dest)
                if c.sha(dest) != digest: raise ValueError('retention copy differs: '+name)
                kept[name] = digest
    c.save(target/'retention.json', dict(version=2, files=kept, rebuildable=references,
           records=records, compressed=compressed, source=str(source), execution_rebuilt=False))
    size = check_size(target)
    return dict(retained_files=len(kept), referenced_files=len(references),
                bytes=size, target_bytes=PACK_BYTES, above_target=size > PACK_BYTES)


def compact_records(root):
    """Call only after all consumers of build records have completed."""
    root = Path(root)
    summary = {}
    for p in sorted(root.glob('*.records.json')) + list(root.glob('records.json')):
        summary[p.name] = records_summary(p)
    if summary:
        c.save(root/'record-summaries.json', summary)
        for name in summary: (root/name).unlink()
    return summary


def release(out, cache=c.DEFAULT_CACHE):
    """Remove successful run binaries; keep bounded RAM cache references for reuse."""
    out = Path(out)
    failures = explicit_failures(out)
    references = c.read(out/'artifact-references.json') if (out/'artifact-references.json').exists() else {}
    for p in c.files(out):
        name = str(p.relative_to(out))
        if name in failures or 'failure-inputs' in Path(name).parts: continue
        if p.suffix in ('.wat','.census-wat') and not any(x in ('driver', 'proposal', 'runtime', 'sources', 'submitted') for x in Path(name).parts):
            references[name] = dict(sha256=c.sha(p), regeneration='compiler checkpoint or pinned source')
            p.unlink()
        elif p.suffix == '.wasm':
            digest = c.sha(p)
            entry = c.cache_read(cache, 'binary', digest)
            if entry is None:
                with c.cache_write(cache, 'binary', digest) as stage:
                    shutil.copyfile(p, stage/'module.wasm')
                entry = Path(cache)/'binary'/digest
            references[name] = dict(sha256=digest, cache=str(entry/'module.wasm'))
            p.unlink()
    c.save(out/'artifact-references.json', references)
    c.save(out/'.run.json', dict(status='PASS'))


def restore(out):
    out = Path(out)
    path = out/'artifact-references.json'
    if not path.exists(): return
    for name, row in c.read(path).items():
        if 'cache' not in row or (out/name).exists(): continue
        source = Path(row['cache'])
        if not source.exists() or c.sha(source) != row['sha256']:
            raise ValueError('disposable input expired; rebuild the run: '+name)
        (out/name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, out/name)
