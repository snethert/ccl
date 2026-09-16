"""An additive proposal, applicable only to an owned pristine U1 archive."""
import difflib, hashlib, importlib.util, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
U1='c994217adc56b3f8a564526cee4695893ac84d86'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def replace_once(text,old,new):
    if text.count(old)!=1:raise ValueError('U1 patch anchor changed: '+old)
    return text.replace(old,new)
def proposal(source,output):
    spec=importlib.util.spec_from_file_location('archgen',HERE.parent/'architecture/generate.py');gen=importlib.util.module_from_spec(spec);spec.loader.exec_module(gen)
    arch,descriptions=gen.generate(json.loads(gen.LAYOUT.read_text()),json.loads(gen.TCR.read_text()))
    additions={'compiler/WASM32/wasm32-arch.lisp':arch,
      'compiler/WASM32/wasm32-backend.lisp':(HERE/'payload/wasm32-backend.lisp').read_text(),
      'xdump/xwasm32-fasload.lisp':(HERE/'payload/xwasm32-fasload.lisp').read_text()}
    systems=(source/'lib/systems.lisp').read_text()
    anchor='    (backend          "ccl:bin;backend"          ("ccl:compiler;backend.lisp"))'
    updated=replace_once(systems,anchor,anchor+'\n    (wasm32-arch "ccl:bin;wasm32-arch" ("ccl:compiler;WASM32;wasm32-arch.lisp"))\n    (wasm32-backend "ccl:bin;wasm32-backend" ("ccl:compiler;WASM32;wasm32-backend.lisp"))\n    (xwasm32fasload "ccl:bin;xwasm32fasload" ("ccl:xdump;xwasm32-fasload.lisp"))')
    before=(source/'lib/compile-ccl.lisp').read_text()
    after=replace_once(before,'    (:arm *arm-xload-modules*)))',"    (:wasm32 '(xwasm32fasload xfasload))\n    (:arm *arm-xload-modules*)))")
    after=replace_once(after,'    (:arm (append *arm-compiler-modules*',"    (:wasm32 '(wasm32-arch wasm32-backend))\n    (:arm (append *arm-compiler-modules*")
    edits={'lib/systems.lisp':updated,'lib/compile-ccl.lisp':after}
    output.mkdir(parents=True,exist_ok=False)
    for name,text in {**edits,**additions}.items():
        p=output/'files'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    patch=''.join(''.join(difflib.unified_diff((source/n).read_text().splitlines(True),t.splitlines(True),fromfile='a/'+n,tofile='b/'+n)) for n,t in edits.items())
    (output/'registration.patch').write_text(patch)
    save(output/'descriptions.json',descriptions)
    manifest={'source_revision':U1,'modified':[{'path':n,'before':sha(source/n),'after':sha(output/'files'/n)} for n in edits], 'added':[{'path':n,'sha256':sha(output/'files'/n)} for n in additions]}
    save(output/'unit.json',manifest);return manifest
class Unit:
    def __init__(self,source,proposal):
        self.source=source.resolve();self.proposal=proposal;self.manifest=json.loads((proposal/'unit.json').read_text());self.originals={}
        if (self.source/'.git').exists() or not (self.source.parent/'stage1-disposable.json').is_file():raise ValueError('owned archive required')
    def __enter__(self):
        for r in self.manifest['modified']:
            if sha(self.source/r['path'])!=r['before']:raise ValueError('non-U1 source')
        for r in self.manifest['added']:
            if (self.source/r['path']).exists():raise ValueError('addition already exists')
        try:
            for r in self.manifest['modified']+self.manifest['added']:
                p=self.source/r['path'];self.originals[p]=p.read_bytes() if p.exists() else None
                p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((self.proposal/'files'/r['path']).read_bytes())
        except BaseException:self.__exit__(None,None,None);raise
        return self
    def __exit__(self,*args):
        for p,data in self.originals.items():
            if data is None:p.unlink(missing_ok=True)
            else:p.write_bytes(data)
