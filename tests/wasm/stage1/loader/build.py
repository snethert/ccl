"""Build the wasm32 compiler and cross-loader from pinned U1 plus this branch's files, then produce the P2-0 artifacts."""
from pathlib import Path
import os, shutil, sys, tarfile, tempfile
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import proposal
SOURCES=['compiler/WASM32/wasm32-backend.lisp','compiler/WASM32/wasm32-arch.lisp',
         'lib/systems.lisp','lib/compile-ccl.lisp','lib/nfcomp.lisp',
         'xdump/faslenv.lisp','xdump/xfasload.lisp','xdump/xwasm32-fasload.lisp']
def integrated():
    names=list(c.read(c.ROOT/'doc/WASM/stage1/integration-stream-constructors.json')['qualification']['source_identity'])
    names+=[f['file'] for f in c.read(c.ROOT/'doc/WASM/stage1/integration-namespace-consumers.json')['files']]
    return sorted(set(n for n in names if n.endswith('.lisp')))
def run(out,stops=False):
    out.mkdir(parents=True,exist_ok=True)
    kernel=out/'dx86cl64';shutil.copyfile(c.KERNEL,kernel);kernel.chmod(0o755)
    with tempfile.TemporaryDirectory(prefix='u1-',dir=out) as temp:
        source=Path(temp);inputs=c.STORE/'macos-u1-inputs'
        for name in ('source.tar','bootstrap.tar.gz'):
            assert c.sha(inputs/name)==c.read(inputs/'pins.json')['inputs'][name]
            with tarfile.open(inputs/name) as archive:archive.extractall(source,filter='data')
        # The accepted wasm32 tree: every integrated product source (the R13
        # identity plus the namespace consumers) over pristine U1, then this
        # branch's files. This is what the level-0 enumeration reads.
        bodies=proposal.sources()
        for name,body in bodies.items():
            path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
        fixture=source/'tests/wasm/stage1/loader';fixture.mkdir(parents=True)
        for name in ('p2-0.lisp','p2-0-second.lisp'):shutil.copyfile(HERE/name,fixture/name)
        env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(source)+'/',LOADER_OUTPUT=str(out)+'/',LOADER_SOURCE=str(HERE)+'/')
        prefix=[kernel,'-I',c.IMAGE,'--no-init','--batch','--eval',
              '(ccl::in-development-mode (load "ccl:lib;systems.lisp") (load "ccl:lib;compile-ccl.lisp") (load "ccl:xdump;faslenv.lisp") (load (compile-file "ccl:lib;nfcomp.lisp" :output-file "'+str(out)+'/nfcomp.dx64fsl")))',
              '--load',HERE.parent/'registration/load.lisp']
        seconds=c.command(prefix+['--load',HERE/'produce.lisp'],out/'build.log',env,cwd=source,timeout=300)
        log=(out/'build.log').read_text()
        assert 'FASL-PUBLICATION-PASS' in log,log[-3000:]
        original=(out/'p2-0.w32fsl').read_bytes()
        assert original[12:14]==bytes.fromhex('ff80'),'Wasm FASL version'
        changed=bytearray(original);changed[13]=0x67
        (out/'native-version.w32fsl').write_bytes(changed)
        for name in ('p2-0.lisp','p2-0-second.lisp'):(fixture/name).unlink()
        c.command(prefix+['--load',HERE/'load.lisp'],out/'load.log',env,cwd=source,timeout=300)
        log=(out/'load.log').read_text()
        assert 'CROSS-LOAD-PASS' in log and 'HOST-STATE-RESTORED-PASS' in log,log[-3000:]
        controls=[]
        for label,name in [('native','nfcomp.dx64fsl'),('rewritten','native-version.w32fsl')]:
            assert 'FASL-VERSION-REFUSAL-PASS '+label in log,label
            assert not (out/('refused-'+label)).exists(),'refusal published artifacts'
            controls.append(dict(name=label,status='REFUSED',reason='Wrong FASL version',
                sha256=c.sha(out/name),host_state_restored=True,published=False))
        c.save(out/'fasl-controls.json',dict(status='PASS',original=c.sha(out/'p2-0.w32fsl'),
            rewritten_byte=dict(offset=13,before=128,after=103),rows=controls))
        stop_seconds=None
        if stops:
            stop_seconds=c.command(prefix+['--load',HERE/'stops.lisp'],out/'stops.log',env,cwd=source,timeout=1800)
            assert 'STOPS-PASS' in (out/'stops.log').read_text(),(out/'stops.log').read_text()[-3000:]
    import hashlib
    c.save(out/'build-completion.json',dict(status='PASS',seconds=seconds,stops_seconds=stop_seconds,sources={n:hashlib.sha256(b.encode()).hexdigest() for n,b in bodies.items()}))
if __name__=='__main__':run(Path(sys.argv[1]).resolve(),'--stops' in sys.argv)
