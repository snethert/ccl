"""Exact inverse edits plus real-reader equality for the two lock source files."""
from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage
BASE='7668f42d'
FILES=['level-0/l0-aprims.lisp','level-0/l0-misc.lisp','compiler/WASM32/wasm32-arch.lisp']

def definition(text,start):
    depth=0;string=False;escape=False;comment=False
    for i in range(start,len(text)):
        char=text[i]
        if comment:
            if char=='\n':comment=False
        elif string:
            if escape:escape=False
            elif char=='\\':escape=True
            elif char=='"':string=False
        elif char==';':comment=True
        elif char=='"':string=True
        elif char=='(':depth+=1
        elif char==')':
            depth-=1
            if depth==0:return text[start:i+1]
    raise AssertionError('incomplete definition')

def run(out):
    out.mkdir(parents=True)
    before=out/'before';after=out/'after'
    before.mkdir();after.mkdir()
    with tempfile.TemporaryDirectory(dir=out,prefix='u1-') as tmp:
        source=Path(tmp)
        for name in ('source.tar','bootstrap.tar.gz'):
            with tarfile.open(c.STORE/'macos-u1-inputs'/name) as archive:archive.extractall(source,filter='data')
        shutil.copyfile(c.KERNEL,source/'dx86cl64');(source/'dx86cl64').chmod(0o755)
        baseline=out/'baseline'
        for name in FILES:
            p=baseline/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT))
        spec=importlib.util.spec_from_file_location('lock_source',HERE.parent/'ready/lock_source.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        proposed=module.sources(baseline);proof=[]
        for name in FILES[:2]:
            old=(baseline/name).read_text();new=proposed[name]
            retained=c.STORE/'2026-09-24-stage1-ready-join-r12/proposal'/name
            assert new.encode()==retained.read_bytes(),name
            append=(HERE.parent/'ready/locks.lisp').read_text()
            split=append.index('#+wasm32-target\n(defun %wasm-recursive-lock-state')
            extra=append[:split] if name==FILES[0] else append[split:]
            assert new.endswith('\n'+extra)
            inverse=new[:-len('\n'+extra)]
            names=['%make-recursive-lock-ptr'] if name==FILES[0] else ['%lock-recursive-lock-ptr','%try-recursive-lock-object','%unlock-recursive-lock-ptr']
            original=[];changed=[]
            for function in names:
                anchor='(defun '+function+' '
                positions=[];start=0
                while (start:=old.find(anchor,start))>=0:positions.append(start);start+=len(anchor)
                assert len(positions)==(1 if name==FILES[0] else 2)
                for start in positions:
                    form=definition(old,start)
                    if name==FILES[0]:
                        a=form;b='#-wasm32-target\n'+form
                    else:
                        feature=old[:start].rstrip().splitlines()[-1]
                        assert feature in ('#+futex','#-futex')
                        replacement='#+(and futex (not wasm32-target))' if feature=='#+futex' else '#-(or futex wasm32-target)'
                        a=feature+'\n'+form;b=replacement+'\n'+form
                    assert inverse.count(b)==1
                    inverse=inverse.replace(b,a);original.append(a);changed.append(b)
            assert inverse==old,'surrounding bytes changed'
            for directory,forms in [(before,original),(after,changed+[extra])]:
                p=directory/name;p.parent.mkdir(exist_ok=True)
                p.write_text('(in-package :ccl)\n'+'\n'.join(forms)+'\n')
            proof.append(dict(file=name,before=c.sha(baseline/name),after=c.sha(retained),unchanged_surrounding_bytes=True,definitions=len(original)))
        text=(HERE.parent/'bootstrap-core-acceptance/readers.lisp').read_text()
        text=text.replace('(getenv "READER_U1"))))','(getenv "READER_ARCH_SOURCE"))))',1)
        text=text.replace('\'(\"l0-def\" \"l0-pred\" \"l0-utils\")','\'(\"l0-aprims\" \"l0-misc\")')
        for variable in ('READER_U1','READER_PROPOSAL'):
            old='(reader-forms (merge-pathnames relative (getenv "'+variable+'")))'
            new='(loop for futex in \'(nil t) collect (let ((*features* (if futex (adjoin :futex *features*) (remove :futex *features*)))) '+old+'))'
            assert text.count(old)==1;text=text.replace(old,new)
        script=out/'readers.lisp';script.write_text(text)
        env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(source)+'/',READER_U1=str(before)+'/',READER_PROPOSAL=str(after)+'/',READER_OUTPUT=str(out)+'/',READER_ARCH_SOURCE=str(source)+'/')
        c.command([source/'dx86cl64','--no-init','--batch','--load',ROOT/'tests/wasm/native-census/observer.lisp','--load',script],out/'run.log',env,cwd=source,timeout=120)
        rows=c.read(out/'readers.json')['rows'];assert len(rows)==34 and all(r['equal'] for r in rows)
        c.save(out/'summary.json',dict(status='PASS',source_proof=proof,profiles=17,files=2,futex_modes=2,comparisons=68,
            scope='Compositional proof: seven actual changed native definitions and all new target definitions read identically for every existing target with FUTEX on and off; exact inverse edits prove all surrounding bytes unchanged. No foreign interface loading is claimed.'))
        c.save(out/'forms.json',{p.name:c.sha(p) for p in out.glob('*.forms')})
        for p in out.glob('*.forms'):p.unlink()
        shutil.rmtree(baseline)
    return c.read(out/'summary.json')
if __name__=='__main__':
    out=Path(sys.argv[1]).resolve()
    with storage.lease([out]):print(json.dumps(run(out)))
