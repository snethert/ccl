"""Prove reader substitutions and surrounding-byte identity for seventeen targets."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
from sources import FILES, CONSTANTS, derive
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]

def run(source,proposal,out):
    out.mkdir()
    # Each edit replaces one reader token with two mutually exclusive forms.
    # Inverse replacement proves every surrounding source byte is unchanged.
    # Compare those substitutions with the real reader, including TARGET and
    # all seventeen feature sets. This needs no foreign database for untouched
    # Windows calls in the surrounding function.
    before_dir=out/'before';after_dir=out/'after'
    before_dir.mkdir();after_dir.mkdir()
    substitutions=[]
    changed=derive(ROOT)
    for name in list(FILES):
        original=(source/name).read_text();proposed=(proposal/name).read_text()
        assert proposed==changed[name],name
        inverse=proposed
        before=[];after=[]
        from foreign import sites
        for key,value in CONSTANTS.items():
            old='#$'+key
            new='#+wasm32-target target::'+value+' #-wasm32-target '+old
            count=sum(m.group(0)==old for m in sites(original))
            if count:
                assert inverse.count(new)==count
                inverse=inverse.replace(new,old)
                before.append(old);after.append(new)
                substitutions.append(dict(file=name,token=old,occurrences=count))
        assert inverse==original,name
        for directory,forms in ((before_dir,before),(after_dir,after)):
            p=directory/name;p.parent.mkdir(exist_ok=True)
            p.write_text('(in-package :ccl)\n'+'\n'.join(forms)+'\n')
    (out/'substitutions.json').write_text(json.dumps(substitutions,indent=2)+'\n')
    text=(HERE.parent/'bootstrap-core-acceptance/readers.lisp').read_text()
    old='(dolist (stem \'("l0-def" "l0-pred" "l0-utils"))\n            (let* ((relative (concatenate \'string "level-0/" stem ".lisp"))'
    paths=list(FILES)
    new='(dolist (relative \'('+ ' '.join('"'+p+'"' for p in paths)+'))\n            (let* ((stem (pathname-name relative))'
    assert text.count(old)==1
    text=text.replace(old,new)
    text=text.replace('(getenv "READER_U1"))))', '(getenv "READER_ARCH_SOURCE"))))', 1)
    script=out/'readers.lisp';script.write_text(text)
    env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(source)+'/',READER_U1=str(before_dir)+'/',READER_PROPOSAL=str(after_dir)+'/',READER_OUTPUT=str(out)+'/',READER_ARCH_SOURCE=str(source)+'/')
    command=[str(source/'dx86cl64'),'--no-init','--batch','--load',str(ROOT/'tests/wasm/native-census/observer.lisp'),'--load',str(script)]
    with (out/'run.log').open('w') as log:
        subprocess.run(command,cwd=source,env=env,stdout=log,stderr=log,check=True,timeout=120)
    rows=json.loads((out/'readers.json').read_text())['rows']
    assert len(rows)==17*len(paths) and all(x['equal'] for x in rows)
    # The bounded comparison is in the pinned Lisp runner; keep hashes and
    # counts of its full form dumps, avoiding repeated copies of source forms.
    forms={p.name:dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in out.glob('*.forms')}
    for p in out.glob('*.forms'):p.unlink()
    (out/'summary.json').write_text(json.dumps(dict(status='PASS',reader_comparisons=len(rows),substitutions=substitutions,form_dumps=forms,scope='Compositional reader proof: exact inverse edit restores every surrounding byte; each substituted form reads identically under all seventeen existing target profiles. Full-file foreign interface loading is not claimed.'),indent=2,sort_keys=True)+'\n')

if __name__=='__main__':run(*(Path(x).resolve() for x in sys.argv[1:]))


def replay(evidence, proposal, out):
    import shutil, tarfile, tempfile
    with tempfile.TemporaryDirectory(prefix='ccl-input-reader-') as temp:
        source=Path(temp)
        for name in ('source.tar','bootstrap.tar.gz'):
            with tarfile.open(evidence/'macos-u1-inputs'/name) as archive:
                archive.extractall(source,filter='data')
        shutil.copy(evidence/'2026-09-12-native-census-r7/baseline/build/dx86cl64',source/'dx86cl64')
        (source/'dx86cl64').chmod(0o755)
        run(source,proposal,out)
