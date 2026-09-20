import importlib.util,json,sys
from pathlib import Path
from backend import generate,HERE

def run(e,work,out):
 reg=HERE.parent/'registration';sys.path.insert(0,str(reg));spec=importlib.util.spec_from_file_location('float_r6',reg/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 original=m.proposal
 def proposal(src,dest):
  manifest=original(src,dest);p=dest/'files/compiler/WASM32/wasm32-backend.lisp';p.write_text(generate());next(x for x in manifest['added'] if x['path']=='compiler/WASM32/wasm32-backend.lisp')['sha256']=m.sha(p);m.save(dest/'unit.json',manifest);return manifest
 m.proposal=proposal
 assert m.run(e/'macos-u1-inputs',e/'2026-09-12-native-census-r7/baseline/build/dx86cl64',work,out,e/'2026-09-16-stage1-1a-r2/native')==0
if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve(),Path(sys.argv[3]).resolve())
