"""Small I/O and loading helpers for the integrated development closure."""
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def require(ok,reason):
    if not ok: raise ValueError(reason)

def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def read(path):
    raw=path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)

def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)

def compressed(value,sort_keys=True,level=9,legacy_stream=False):
    # Match the historical materializers' explicit gzip header and JSON options.
    out=io.BytesIO()
    with gzip.GzipFile(filename='',fileobj=out,mode='wb',mtime=0,compresslevel=level) as stream:
        if legacy_stream:
            # Closing the historical text wrapper flushes before gzip closes.
            # That flush affects compressed bytes even when JSON is identical.
            with io.TextIOWrapper(stream,encoding='utf-8') as text:
                json.dump(value,text,sort_keys=sort_keys,separators=(',',':'),ensure_ascii=False)
                text.write('\n')
        else:
            stream.write((json.dumps(value,sort_keys=sort_keys,separators=(',',':'),ensure_ascii=False)+'\n').encode())
    return out.getvalue()

def save(path,value):
    path.write_bytes(compressed(value) if path.suffix=='.gz' else (canonical(value)+'\n').encode())

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def legacy_tools():
    sys.path.insert(0,str(HERE.parent/'startup-closure'))
    import lowering_join,boot_join,candidates
    # The old binding materializer imports its own common.py. No new common.py
    # is supplied by this directory, and a foreign preloaded module is refused.
    sys.path.insert(0,str(HERE.parent/'binding-versions'))
    if 'common' in sys.modules:
        require(Path(sys.modules['common'].__file__).resolve()==HERE.parent/'binding-versions/common.py','MATERIALIZER_IMPORT')
    return dict(emission=lowering_join,boot=boot_join,candidates=candidates,
                wrappers=load_module('closure_wrappers',HERE.parent/'boot-wrappers/join.py'),
                bindings=load_module('closure_bindings',HERE.parent/'binding-versions/links.py'),
                literals=load_module('closure_literals',HERE.parent/'resident-literals/join.py'),
                contract=load_module('closure_contract',ROOT/'doc/WASM/tools/check-census.py'))

def source_files():
    files=list(HERE.glob('*.py'))+[HERE/'inputs.json']
    files += [HERE.parent/p for p in ('startup-closure/lowering_join.py','startup-closure/boot_join.py',
              'startup-closure/exchange.py','startup-closure/identity_join.py','startup-closure/effects.py',
              'startup-closure/candidates.py','boot-wrappers/join.py','binding-versions/links.py',
              'binding-versions/common.py','resident-literals/join.py')]
    files += [ROOT/p for p in ('doc/WASM/tools/check-census.py','doc/WASM/contracts/census.schema.json',
                              'doc/WASM/stage0/baseline.json','doc/WASM/stage0/inventory.json')]
    return sorted(files)

def load_inputs(store,pins):
    values={}
    for name,pin in pins['inputs'].items():
        base=ROOT if pin['repository']=='source' else store
        path=(base/pin['path']).resolve()
        require(base.resolve() in path.parents,'INPUT_PATH '+name)
        require(digest(path)==pin['sha256'],'INPUT_IDENTITY '+name)
        if path.suffix in ('.gz','.json'): values[name]=read(path)
        else: values[name]=path.read_text()
    return values
