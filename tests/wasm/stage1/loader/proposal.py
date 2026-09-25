"""Loader source provider: the historical proposal, or verified integrated files."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c


def integration():
    path=ROOT/'doc/WASM/stage1/integration-loader.json'
    return c.read(path) if path.exists() else None


def replace(text,before,after,count=1):
    assert text.count(before)==count,(before,text.count(before))
    return text.replace(before,after)


def patched():
    pins=json.loads((HERE/'provenance.json').read_text())['sources']
    originals={name:(ROOT/name).read_text() for name in pins}
    for name,body in originals.items():
        assert hashlib.sha256(body.encode()).hexdigest()==pins[name],name
    lines=[line+'\n' for line in (HERE/'shared.patch').read_text().split('\n')[:-1]]
    result={};name=None;cursor=0;output=[];i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith('+++ b/'):
            if name:output.extend(old[cursor:]);result[name]=''.join(output)
            name=line[6:].strip();old=[line+'\n' for line in originals[name].split('\n')[:-1]];output=[];cursor=0
        elif line.startswith('@@ '):
            match=re.match(r'@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@',line);assert match
            start=int(match[1])-1;assert start>=cursor
            output.extend(old[cursor:start]);cursor=start;i+=1
            while i<len(lines) and lines[i][:1] in (' ','+','-') and not lines[i].startswith('--- '):
                mark,body=lines[i][0],lines[i][1:]
                if mark in (' ','-'):assert old[cursor]==body,(name,cursor);cursor+=1
                if mark in (' ','+'):output.append(body)
                i+=1
            continue
        i+=1
    if name:output.extend(old[cursor:]);result[name]=''.join(output)
    assert result.keys()==pins.keys()
    return result


def sources():
    installed=integration()
    if installed:
        identity=installed['qualification']['source_identity']
        c.verify_files(ROOT,identity)
        return {name:(ROOT/name).read_text() for name in identity}
    inherited=c.read(c.STORE/'2026-09-24-namespace-consumers-r1/native/qualification.json')['source_identity']
    c.verify_files(ROOT,inherited)
    bodies={name:(ROOT/name).read_text() for name in inherited};bodies.update(patched())
    arch='compiler/WASM32/wasm32-arch.lisp'
    bodies[arch]=replace(bodies[arch],'#x67','#x80',3)
    backend='compiler/WASM32/wasm32-backend.lisp';body=bodies[backend]
    body=replace(body,'(source &rest options &key (target :wasm32) &allow-other-keys)',
                 '(source &rest options &key (target :wasm32) (save-source-locations nil) &allow-other-keys)')
    body=replace(body,'(let ((*wasm32-fasl-publication* t)',
                 '(let ((*wasm32-fasl-publication* t)\n           (*wasm32-template-memory* t)')
    body=replace(body,"(apply #'compile-file source :target :wasm32 options)",
                 "(apply #'compile-file source :target :wasm32 :save-source-locations save-source-locations options)")
    bodies[backend]=body
    spec=importlib.util.spec_from_file_location('loader_architecture',HERE/'architecture/generate.py')
    generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)
    generated,_=generator.generate(c.read(generator.LAYOUT),c.read(generator.TCR))
    assert generated==bodies[arch],'architecture generator differs'
    return bodies


def runtime_sources():
    installed=integration()
    if installed:
        identity={r['file']:r['reviewed'] for r in installed['files'] if r['file'].startswith('runtime/')}
        c.verify_files(ROOT,identity)
        return {name:(ROOT/name).read_text() for name in identity}
    result={str(p.relative_to(HERE)):p.read_text() for p in (HERE/'runtime').glob('*.mjs')}
    return {'runtime/wasm32/'+Path(name).name:body for name,body in result.items()}


def prepare_runtime(out):
    import shutil
    out.mkdir(parents=True,exist_ok=True)
    for p in (ROOT/'runtime/wasm32').iterdir():
        if p.is_file() and p.suffix=='.mjs':shutil.copyfile(p,out/p.name)
    if integration():
        runtime_sources() # Verify the product copies; no proposal overlay.
    else:
        for name,body in runtime_sources().items():(out/Path(name).name).write_text(body)
