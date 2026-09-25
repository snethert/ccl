"""Replay from a differently located Git-free checkout; bind artifact equality."""
from pathlib import Path
import hashlib,os,shutil,subprocess,sys,tarfile
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage

def run(out,first):
    out.mkdir(parents=True,exist_ok=True)
    checkout=out/'archive/ccl';checkout.mkdir(parents=True)
    # A clean tracked checkout, plus this uncommitted review unit. No .git or
    # GIT_DIR escape hatch. The pinned evidence remains a read-only input.
    archive=out/'checkout.tar'
    with archive.open('wb') as stream:subprocess.run(['git','archive','HEAD'],cwd=c.ROOT,stdout=stream,check=True)
    with tarfile.open(archive) as source:source.extractall(checkout,filter='data')
    archive.unlink()
    target=checkout/'tests/wasm/stage1/loader'
    shutil.copytree(HERE,target,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copyfile(HERE.parent/'ready/compiler.py',checkout/'tests/wasm/stage1/ready/compiler.py')
    (checkout.parent/'ccl-evidence').symlink_to(c.STORE,target_is_directory=True)
    env=dict(os.environ);env.pop('GIT_DIR',None);env.pop('GIT_WORK_TREE',None)
    env['GIT_CEILING_DIRECTORIES']=str(out)
    c.command([sys.executable,'-c',"import runpy,sys;from pathlib import Path;sys.path.insert(0,str(Path(sys.argv[1]).parent));runpy.run_path(sys.argv[1])['run'](Path(sys.argv[2]))",target/'run.py',out/'execution'],out/'replay.log',env,checkout,timeout=1800)
    # Exercise added/modified classification and Unit installation in this
    # Git-free tree without repeating the already-bound compiler corpus.
    probe=out/'prepare.py'
    probe.write_text('''from pathlib import Path
import sys
sys.path.insert(0,sys.argv[1]);import corpus,proposal
spec=corpus.importlib.util.spec_from_file_location('loader_compiler',corpus.HERE.parent/'ready/compiler.py')
compiler=corpus.importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
bodies=proposal.sources();key='compiler/WASM32/wasm32-backend.lisp'
compiler.generate=lambda:bodies[key];compiler.sources=lambda:{n:b for n,b in bodies.items() if n!=key}
compiler.install();stage=Path(sys.argv[2]);stage.mkdir()
corpus.builder.prepare(corpus.c.PARENT,stage)
unit=corpus.c.read(stage/'compiled/proposal/unit.json')
assert {x['path'] for x in unit['modified']} >= {'lib/nfcomp.lisp','xdump/faslenv.lisp','xdump/xfasload.lisp'}
assert {x['path'] for x in unit['added']} >= {'compiler/WASM32/wasm32-arch.lisp','compiler/WASM32/wasm32-backend.lisp','xdump/xwasm32-fasload.lisp'}
print('GITLESS-PROPOSAL-CLASSIFICATION-PASS')
''')
    c.command([sys.executable,probe,target,out/'prepare'],out/'prepare.log',env,checkout,timeout=300)
    paths=['p2-0.w32fsl','p2-0-second.w32fsl','heap.bin','static.bin','image.json','code-set.json']
    paths += ['artifacts/'+p.name for p in sorted((first/'p2-0/artifacts').iterdir())]
    identities={}
    for name in paths:
        a=first/'p2-0'/name;b=out/'execution/p2-0'/name
        assert a.read_bytes()==b.read_bytes(),name
        identities[name]=c.sha(a)
    a=c.read(first/'summary.json');b=c.read(out/'execution/summary.json')
    for field in ('artifacts','target','controls','level0','boots','execution_inputs'):
        assert a[field]==b[field],field
    result=dict(status='PASS',gitless=True,artifacts=identities,source_identity=c.read(first/'p2-0/build-completion.json')['sources'],
                first_inputs=a['execution_inputs'],second_inputs=b['execution_inputs'],compiler_classification='PASS',
                observations_equal=True,stops_equal=True)
    c.save(out/'summary.json',result);print('LOADER-REPLAY-PASS',len(paths))

if __name__=='__main__':
    with storage.lease([Path(sys.argv[1])]):run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
