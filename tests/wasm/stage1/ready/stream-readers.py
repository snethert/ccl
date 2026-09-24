"""Actual CCL reader equivalence for the stream pool's target-only branch."""
from pathlib import Path
import importlib.util
import os
import shutil
import sys
import tarfile
import tempfile
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import compiler
import storage
spec=importlib.util.spec_from_file_location('prior_readers',HERE.parent/'ready-runtime-acceptance/readers.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)

def run(out):
    out.mkdir(parents=True)
    name='level-1/l1-streams.lisp'
    old=(c.ROOT/name).read_text();new=compiler.sources()[name]
    insertion="       #+wasm32-target (%wasm-thread-local-value '%string-output-stream-ioblocks%)\n       #-wasm32-target\n"
    assert new.count(insertion)==1 and new.replace(insertion,'')==old
    anchor='(defun %string-stream-ioblock-freelist '
    for label,text in [('before',old),('after',new)]:
        path=out/label/name;path.parent.mkdir(parents=True)
        path.write_text('(in-package :ccl)\n'+prior.definition(text,text.index(anchor))+'\n')
    with tempfile.TemporaryDirectory(dir=out,prefix='u1-') as tmp:
        source=Path(tmp)
        for archive in ('source.tar','bootstrap.tar.gz'):
            with tarfile.open(c.STORE/'macos-u1-inputs'/archive) as a:a.extractall(source,filter='data')
        shutil.copyfile(c.KERNEL,source/'dx86cl64');(source/'dx86cl64').chmod(0o755)
        script=(HERE.parent/'bootstrap-core-acceptance/readers.lisp').read_text()
        script=script.replace('(getenv "READER_U1"))))','(getenv "READER_ARCH_SOURCE"))))',1)
        script=script.replace('\'(\"l0-def\" \"l0-pred\" \"l0-utils\")','\'(\"l1-streams\")').replace('"level-0/" stem','"level-1/" stem')
        path=out/'readers.lisp';path.write_text(script)
        env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(source)+'/',READER_U1=str(out/'before')+'/',READER_PROPOSAL=str(out/'after')+'/',READER_ARCH_SOURCE=str(source)+'/',READER_OUTPUT=str(out)+'/')
        c.command([source/'dx86cl64','--no-init','--batch','--load',c.ROOT/'tests/wasm/native-census/observer.lisp','--load',path],out/'run.log',env,source,timeout=120)
    rows=c.read(out/'readers.json')['rows'];assert len(rows)==17 and all(r['equal'] for r in rows)
    c.save(out/'summary.json',dict(status='PASS',profiles=17,file=name,before=c.sha(c.ROOT/name),after=c.digest_bytes(new.encode()) if hasattr(c,'digest_bytes') else __import__('hashlib').sha256(new.encode()).hexdigest(),unchanged_surrounding_bytes=True))
    for path in out.glob('*.forms'):path.unlink()
    return c.read(out/'summary.json')
if __name__=='__main__':
    out=Path(sys.argv[1]).resolve()
    with storage.lease([out]):print(run(out))
