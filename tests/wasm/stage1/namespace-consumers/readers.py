"""Compare namespace source forms with CCL's reader for every existing target."""
from pathlib import Path
import os, shutil, sys, tarfile, tempfile
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import proposal
import storage

def top_forms(text):
    depth=0;start=0;i=0;quote=None;block=0
    while i<len(text):
        ch=text[i]
        if block:
            if text.startswith('#|',i):block+=1;i+=2;continue
            if text.startswith('|#',i):block-=1;i+=2;continue
        elif quote:
            if ch=='\\':i+=2;continue
            if ch==quote:quote=None
        elif text.startswith('#|',i):block=1;i+=2;continue
        elif ch==';':i=text.find('\n',i);i=len(text) if i<0 else i;continue
        elif text.startswith('#\\',i):
            i+=3
            while i<len(text) and not text[i].isspace() and text[i] not in '()':i+=1
            continue
        elif ch in ('"','|'):quote=ch
        elif ch=='(':
            if depth==0:start=i
            depth+=1
        elif ch==')':
            depth-=1;assert depth>=0
            if depth==0:yield text[start:i+1]
        i+=1
    assert depth==0 and not quote and not block

def run(out):
    out.mkdir(parents=True,exist_ok=True)
    sources={name:body for name,body in proposal.sources().items() if '/WASM32/' not in name}
    omitted=[];full={}
    for name,body in sources.items():
        old=(c.ROOT/name).read_text();full[name]={'before':c.sha(c.ROOT/name),'after':__import__('hashlib').sha256(body.encode()).hexdigest()}
        # Foreign entries for Windows are unavailable in the macOS CDB. An
        # unchanged complete form needs no reread to establish equivalence.
        # Keep its original conditional prefix and replace only that proven
        # identical form on both sides. Every changed form remains intact.
        for form in top_forms(old):
            if ('#_' in form or '#$' in form) and old.count(form)==body.count(form)==1:
                digest=__import__('hashlib').sha256(form.encode()).hexdigest()
                omitted.append(dict(file=name,sha256=digest,bytes=len(form.encode())))
                (out/(digest+'.unchanged.lisp')).write_text(form+'\n')
                old=old.replace(form,'(progn)');body=body.replace(form,'(progn)')
        for label,text in [('before',old),('after',body)]:
            p=out/label/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(text)
    script=(HERE.parent/'bootstrap-core-acceptance/readers.lisp').read_text()
    script=script.replace('(getenv "READER_U1"))))','(getenv "READER_ARCH_SOURCE"))))',1)
    old='''(dolist (stem '("l0-def" "l0-pred" "l0-utils"))
            (let* ((relative (concatenate 'string "level-0/" stem ".lisp"))'''
    new='''(dolist (relative '("'''+ '" "'.join(sources)+'''"))
            (let* ((stem (substitute #\\- #\\/ relative))'''
    assert script.count(old)==1
    script=script.replace(old,new)
    # Pathname reader literals allocate fresh objects on each read. Compare
    # their type and all six components, preserving string case and versions.
    script=script.replace('  (cond ((consp a)', '''  (cond ((pathnamep a)
         (and (pathnamep b) (eq (type-of a) (type-of b))
              (every (lambda (accessor)
                       (same-reader-forms (funcall accessor a) (funcall accessor b)))
                     '(pathname-host pathname-device pathname-directory
                       pathname-name pathname-type pathname-version))))
        ((consp a)''')
    (out/'readers.lisp').write_text(script)
    with tempfile.TemporaryDirectory(prefix='u1-',dir=out) as tmp:
        source=Path(tmp)
        for name in ('source.tar','bootstrap.tar.gz'):
            with tarfile.open(c.STORE/'macos-u1-inputs'/name) as a:a.extractall(source,filter='data')
        # A stable executable pathname avoids repeating Rosetta preparation.
        kernel=out.parent/'namespace-compiler'
        if not kernel.exists():shutil.copyfile(c.KERNEL,kernel);kernel.chmod(0o755)
        env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(source)+'/',READER_ARCH_SOURCE=str(source)+'/',
                 READER_U1=str(out/'before')+'/',READER_PROPOSAL=str(out/'after')+'/',READER_OUTPUT=str(out)+'/')
        c.command([kernel,'-I',c.IMAGE,'--no-init','--batch','--load',c.ROOT/'tests/wasm/native-census/observer.lisp',
                   '--load',out/'readers.lisp'],out/'run.log',env,source,timeout=240)
    result=c.read(out/'readers.json');assert len(result['rows'])==17*len(sources)
    assert all(row['equal'] for row in result['rows'])
    c.save(out/'summary.json',dict(status='PASS',profiles=17,files=len(sources),comparisons=len(result['rows']),
        full_sources=full,unchanged_foreign_forms=omitted,
        before=c.inventory(out/'before'),after=c.inventory(out/'after'),forms={p.name:c.sha(p) for p in out.glob('*.forms')}))
    for p in out.glob('*.forms'):p.unlink()
    return c.read(out/'summary.json')

if __name__=='__main__':
    with storage.lease([Path(sys.argv[1])]):
        result=run(Path(sys.argv[1]).resolve())
        print({k:result[k] for k in ('status','profiles','files','comparisons')})
