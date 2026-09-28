"""Regenerate disposable diagnostic records from the bound build recipe."""
from pathlib import Path
import importlib.util
import json
import shutil
import tempfile


def read_records(path):
    path = Path(path)
    if path.exists(): return json.loads(path.read_text())
    root = path.parent
    spec = importlib.util.spec_from_file_location('record_regeneration', Path(__file__).with_name('build.py'))
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    c = builder.c
    recipe = c.read(root/'build-recipe.json')
    if c.sha(Path(__file__).with_name('build.py')) != recipe['driver']:
        raise ValueError('record producer changed; use the pinned checkout')
    c.verify_files(c.ROOT, c.read(root/'sources.json'))
    options = recipe['options']
    if options['source_file'] and c.sha(options['source_file']) != recipe['source']:
        raise ValueError('diagnostic source changed')
    diagnostics = builder.storage.WORK_ROOT/'codex/record-diagnostics'
    builder.storage.ensure_ram()
    diagnostics.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='records-', dir=diagnostics) as temporary:
        temp = Path(temporary)
        builder.run(temp, **options, diagnostic_records=True)
        expected = c.read(root/'record-summaries.json')[path.name]
        if c.sha(temp/path.name) != expected['sha256']:
            raise ValueError('regenerated records differ')
        return c.read(temp/path.name)


if __name__ == '__main__':
    import contextlib
    import sys
    with contextlib.redirect_stdout(sys.stderr):
        value = read_records(Path(sys.argv[1]))
    json.dump(value, sys.stdout)
