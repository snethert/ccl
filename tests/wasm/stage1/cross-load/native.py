"""R6/R6a with explicit accounting for the new host publication dispatches."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tarfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import proposal


def local(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def run(out,comparison_only=False):
    out.mkdir(parents=True,exist_ok=comparison_only)
    qualification=local('cross_load_qualification',HERE/'qualify.py')
    bodies=qualification.sources()
    prior=local('cross_load_native_prerequisite',HERE.parent/'bootstrap-generic-dispatch/native.py')
    old=prior.driver
    previous=c.read(c.STORE/'2026-09-24-namespace-consumers-r1/native/results/run.json')
    assert previous['status']=='PASS'
    inherited=previous['r6']['intentional_artifacts']
    pairs=[]
    for fasl in inherited:
        if fasl in ('bin/systems.dx64fsl','bin/compile-ccl.dx64fsl'):continue
        name=fasl.replace('l1-fasls/','level-1/').replace('bin/','lib/').replace('.dx64fsl','.lisp')
        assert name in bodies
        pairs.append((name,fasl))
    # These two shared host files intentionally gain executable dispatch.
    # Every other decoded component must still compare exactly, apart from
    # the existing, bounded source-location allowance.
    import native_compare
    class HostCompilerFasl(native_compare.CompilerFasl):
        def expr(self,depth=0):
            # XFASLOAD embeds a compressed source-note byte vector larger than
            # the small registration decoder's 4 KiB bound. Bound this byte
            # payload by the actual file; retain every byte without decoding it.
            if self.pos<len(self.data) and self.data[self.pos]&127==14:
                assert depth<64
                start,raw=self.pos,self.byte();size=0
                for shift in range(0,35,7):
                    byte=self.byte();size|=(byte&127)<<shift
                    if byte&128:break
                else:raise ValueError('FASL_COUNT_BOUND')
                assert size<=len(self.data)-self.pos
                self.ops.append(dict(offset=start,opcode=14,epush=bool(raw&128)))
                value={'u8vector':self.take(size).hex()}
                if raw&128:
                    self.refs.append(value);assert len(self.refs)<=self.capacity
                self.spans[id(value)]=(start,self.pos)
                return value
            return super().expr(depth)
    comparer=type(sys)('cross_load_intentional_comparer')
    comparer.__dict__.update(native_compare.__dict__)
    text=Path(native_compare.__file__).read_text()
    text=text.replace("    assert na==nb,'native executable, non-debug constant, or ABI difference'",
                      '    intentional(na,nb)')
    exec(compile(text,str(HERE/'native.py')+':comparer','exec'),comparer.__dict__)
    comparer.CompilerFasl=HostCompilerFasl
    def compare_intentional(before,after,src_before,src_after,allowed,added=None):
        changes=[]
        def intentional(a,b):
            if added:
                new=[r for r in b if isinstance(r,dict) and r.get('defvar-init',[None])[0]=={'symbol':added}]
                assert len(new)==1 and new[0]['defvar-init'][1:]==[0,None]
                b=[r for r in b if r is not new[0]]
                changes.append(dict(added=new[0]))
            assert len(a)==len(b)
            found=set()
            for x,y in zip(a,b):
                if x==y:continue
                assert set(x)==set(y)=={'defun'},'unattributed shared component'
                f,g=x['defun'][0]['function'],y['defun'][0]['function']
                name=f['constants'][-2]
                assert name==g['constants'][-2] and name.get('symbol') in allowed,name
                assert x['defun'][1]==y['defun'][1]
                found.add(name['symbol'])
                changes.append(dict(name=name['symbol'],before=x,after=y))
            assert found==set(allowed),(found,allowed)
        comparer.intentional=intentional
        result=comparer.compare(before,after,src_before,src_after)
        result['scope']='Intentional shared dispatch changes retained in full; all other executable bytes and non-location data equal.'
        result['intentional_components']=changes
        return result
    def shared(before,after,src_before,src_after):
        return compare_intentional(before,after,src_before,src_after,
            ['CCL::FASL-DUMP-FUNCTION'])
    def cross(before,after,src_before,src_after):
        return compare_intentional(before,after,src_before,src_after,
            ['CCL::XFASLOAD','CCL::XLOAD-LFUN-NAME'])
    if comparison_only:
        with tarfile.open(c.STORE/'macos-u1-inputs/source.tar') as archive:
            result=cross((out/'results/xfasload-before.dx64fsl').read_bytes(),
                (out/'results/xfasload-after.dx64fsl').read_bytes(),
                archive.extractfile('xdump/xfasload.lisp').read().decode(),bodies['xdump/xfasload.lisp'])
        c.save(out/'xfasload-comparison.json',result)
        print('NATIVE-DISPATCH-COMPARISON-PASS');return
    # Keep the standard native build, snapshot, test and restoration contract.
    # The generated driver is retained so its changes are reviewable.
    reg=HERE.parent/'registration'
    driver=type(sys)('cross_load_native_driver')
    driver.__dict__.update(old.__dict__)
    text=(reg/'run.py').read_text()
    before="if set(changed)!={'bin/systems.dx64fsl','bin/compile-ccl.dx64fsl'}:raise ValueError('unexpected FASL changes '+repr(changed))"
    after="""if set(changed)!=set(EXPECTED):raise ValueError('unexpected FASL changes '+repr(changed))
            with tarfile.open(out/'baseline-fasls.tar.gz') as baseline_archive, tarfile.open(inputs/'source.tar') as sources:
                for srcname,faslname in SOURCE_PAIRS:
                    checked=compare_source(baseline_archive.extractfile(faslname).read(),(source/faslname).read_bytes(),sources.extractfile(srcname).read().decode(),(source/srcname).read_text())
                    save(out/(Path(srcname).stem+'-comparison.json'),checked)
                checked=compare_shared(baseline_archive.extractfile('bin/nfcomp.dx64fsl').read(),(source/'bin/nfcomp.dx64fsl').read_bytes(),sources.extractfile('lib/nfcomp.lisp').read().decode(),(source/'lib/nfcomp.lisp').read_text())
                save(out/'nfcomp-comparison.json',checked)
                checked=compare_cross(baseline_archive.extractfile('xdump/xfasload.dx64fsl').read(),(source/'xdump/xfasload.dx64fsl').read_bytes(),sources.extractfile('xdump/xfasload.lisp').read().decode(),(source/'xdump/xfasload.lisp').read_text())
                save(out/'xfasload-build-comparison.json',checked)
"""
    assert text.count(before)==1;text=text.replace(before,after).replace("'identical':162","'identical':164-len(changed)")
    before="        with Unit(source,out/'proposal'):"
    after="""        lisp('cross-loader-before','(progn (ccl::in-development-mode (compile-file "ccl:xdump;xfasload.lisp" :output-file '+json.dumps(str(out/'xfasload-before.dx64fsl'))+')) (ccl:quit))')
        with Unit(source,out/'proposal'):
            lisp('cross-loader-after','(progn (ccl::in-development-mode (compile-file "ccl:xdump;xfasload.lisp" :output-file '+json.dumps(str(out/'xfasload-after.dx64fsl'))+')) (ccl:quit))')
            with tarfile.open(inputs/'source.tar') as archive:
                comparison=compare_cross((out/'xfasload-before.dx64fsl').read_bytes(),(out/'xfasload-after.dx64fsl').read_bytes(),archive.extractfile('xdump/xfasload.lisp').read().decode(),(source/'xdump/xfasload.lisp').read_text())
            save(out/'xfasload-comparison.json',comparison)"""
    assert text.count(before)==1;text=text.replace(before,after)
    # The old registration smoke expects the writer refusal. This proposal
    # supersedes it with the real FASL/heap witness, run by run.py.
    first=text.index("            lisp('target',")
    last=text.index("        for n in ('wasm32-arch'",first)
    text=text[:first]+text[last:]
    (out/'driver.py').write_text(text)
    exec(compile(text,str(reg/'run.py'),'exec'),driver.__dict__)
    def prepare(source,destination):
        destination.mkdir(parents=True)
        manifest=dict(source_revision='c994217adc56b3f8a564526cee4695893ac84d86',added=[],modified=[])
        for name,body in bodies.items():
            p=destination/'files'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body)
            if (source/name).exists():manifest['modified'].append(dict(path=name,before=c.sha(source/name),after=c.sha(p)))
            else:manifest['added'].append(dict(path=name,sha256=c.sha(p)))
        c.save(destination/'unit.json',manifest);return manifest
    driver.proposal=prepare;driver.SOURCE_PAIRS=pairs
    driver.EXPECTED=inherited+['bin/nfcomp.dx64fsl','xdump/xfasload.dx64fsl']
    driver.compare_source=native_compare.compare
    driver.compare_shared=shared;driver.compare_cross=cross
    sys.setrecursionlimit(20000)
    status=driver.run(c.STORE/'macos-u1-inputs',c.KERNEL,out/'work',out/'results',
                      c.STORE/'2026-09-16-stage1-1a-r2/native')
    assert status==0,'native qualification failed'
    c.save(out/'qualification.json',dict(status='PASS',source_identity={name:hashlib.sha256(body.encode()).hexdigest() for name,body in bodies.items()},
        run=c.sha(out/'results/run.json'),intentional_shared_artifacts=['bin/nfcomp.dx64fsl','xfasload-after.dx64fsl']))
