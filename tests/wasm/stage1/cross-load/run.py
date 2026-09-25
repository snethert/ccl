"""Build the first real Wasm FASL and cross-load it from pristine U1."""
from pathlib import Path
import argparse
import os
import shutil
import sys
import tarfile
import tempfile
import time
import subprocess
import re
import importlib.util

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'bootstrap-validation'))
import common as c
import storage
import proposal


def run(out):
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    inputs = c.STORE / 'macos-u1-inputs'
    pins = c.read(inputs / 'pins.json')['inputs']
    spec=importlib.util.spec_from_file_location('cross_load_qualification',HERE/'qualify.py')
    qualification=importlib.util.module_from_spec(spec);spec.loader.exec_module(qualification)
    bodies = qualification.sources()
    for name, body in bodies.items():
        path = out / 'proposal' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    with tempfile.TemporaryDirectory(prefix='u1-', dir=out.parent) as temporary:
        source = Path(temporary)
        for name in ('source.tar', 'bootstrap.tar.gz'):
            assert c.sha(inputs / name) == pins[name]
            with tarfile.open(inputs / name) as archive:
                archive.extractall(source, filter='data')
        for name, body in bodies.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
        fixture=source/'tests/wasm/stage1/cross-load/fixture.lisp'
        fixture.parent.mkdir(parents=True)
        shutil.copyfile(HERE/'fixture.lisp',fixture)
        shutil.copyfile(c.KERNEL, source / 'dx86cl64')
        (source / 'dx86cl64').chmod(0o755)
        env = dict(os.environ, CCL_DEFAULT_DIRECTORY=str(source)+'/',
                   CROSS_LOAD_SOURCE=str(HERE)+'/', CROSS_LOAD_OUTPUT=str(out)+'/')
        c.command([source / 'dx86cl64', '-I', c.IMAGE, '--no-init', '--batch',
                   '--load', HERE / 'build.lisp'], out / 'build.log', env, source, timeout=180)
        assert 'FASL-PUBLICATION-PASS' in (out/'build.log').read_text()
        fixture.unlink()
        c.command([source/'dx86cl64','-I',c.IMAGE,'--no-init','--batch',
                   '--load',HERE/'load.lisp'],out/'cross-load.log',env,source,timeout=180)
        refusals(source,out,env)
        frontier(source,out,env)
    assert 'CROSS-LOAD-PASS' in (out / 'cross-load.log').read_text()
    for wat in (out / 'producer').glob('*.wat'):
        c.command([c.WABT, '--enable-all', wat, '-o', wat.with_suffix('.wasm')],
                  wat.with_suffix('.log'))
    c.save(out / 'build.json', dict(status='PASS', seconds=time.monotonic()-start,
           source_identity={name:c.sha(out / 'proposal' / name) for name in bodies},
           toolchain={str(p):c.sha(p) for p in (c.KERNEL, c.IMAGE, c.WABT, c.NODE)},
           inputs=pins))
    image(out)
    print('CROSS-LOAD-BUILD-PASS', flush=True)


def frontier(source,out,env):
    destination=out/'frontier';destination.mkdir()
    root=sorted((source/'level-0').glob('*.lisp'))
    subdir=sorted((source/'level-0/WASM32').glob('*.lisp'))
    rows=[]
    for path in root+subdir:
        name=str(path.relative_to(source))
        stem=name.replace('/','-').removesuffix('.lisp')
        extra=dict(env,CROSS_LOAD_FILE='ccl:'+name.replace('/',';'),
                   CROSS_LOAD_RESULT=str(destination/stem))
        c.command([source/'dx86cl64','-I',c.IMAGE,'--no-init','--batch',
                   '--load',HERE/'frontier.lisp'],destination/(stem+'.log'),extra,source,timeout=180)
        row=c.read(destination/(stem+'.json'))
        rows.append(dict(path=name,sha256=c.sha(path),status=row[0],phase=row[1],
                         name=row[2],position=row[3],condition=row[4],log=stem+'.log'))
    c.save(destination/'results.json',dict(compile_order=rows,
        load_order=[str(p.relative_to(source)) for p in subdir+root],
        scope='Independent fresh-host first-stop probes using the real compiler and dumper; later files do not inherit failed predecessors. No ordered build or boot claimed.'))


def refusals(source,out,env):
    destination=out/'fasl-controls';destination.mkdir()
    data=(out/'fixture.w32fsl').read_bytes()
    name=c.read(out/'producer/cross-load.json')['modules'][0]['name'].encode('ascii')
    offset=data.index(name)
    assert len(name)<128 and data[offset-2:offset]==bytes([129,len(name)|128])
    rows=[]
    for key,index,value,reason in [('version',offset-2,130,'FASL-FUNCTION-VERSION'),
                                  ('length',offset-1,128,'FASL-MODULE-TEXT-LENGTH'),
                                  ('ascii',offset,255,'FASL-MODULE-TEXT-BYTE'),
                                  ('duplicate',None,None,'FASL-DUPLICATE-MODULE'),
                                  ('length-upper',None,None,'FASL-MODULE-TEXT-LENGTH'),
                                  ('pool-kind',None,None,'FASL-FUNCTION-POOL'),
                                  ('pool-subtype',None,None,'FASL-FUNCTION-POOL'),
                                  ('pool-size',None,None,'FASL-FUNCTION-POOL')]:
        path=destination/(key+'.w32fsl');changed=bytearray(data)
        if index is not None:changed[index]=value
        if key=='length-upper':
            changed[offset-1:offset]=bytes([1,0,0,136])
            changed[8:12]=(int.from_bytes(data[8:12],'big')+3).to_bytes(4,'big')
        if key.startswith('pool-'):changed=bytearray((out/(key+'.w32fsl')).read_bytes())
        path.write_bytes(changed)
        output=destination/key
        extra=dict(env,CROSS_LOAD_BAD_FILE=str(path),CROSS_LOAD_BAD_OUTPUT=str(output)+'/',
                   CROSS_LOAD_BAD_REASON=reason,CROSS_LOAD_DUPLICATE='yes' if key=='duplicate' else '')
        c.command([source/'dx86cl64','-I',c.IMAGE,'--no-init','--batch',
                   '--load',HERE/'refusals.lisp'],destination/(key+'.log'),extra,source,timeout=180)
        assert 'FASL-REFUSAL-PASS' in (destination/(key+'.log')).read_text()
        assert not output.exists(),'refusal published producer output'
        rows.append(dict(name=key,reason=reason,fasl_sha256=c.sha(path),published=False))
    c.save(destination/'results.json',rows)


def image(out):
    runtime=out/'runtime'
    runtime.mkdir(exist_ok=True)
    for name in ('heap-image.mjs','sha256.mjs','binary.mjs','ranges.mjs','materializer.mjs','bytes.mjs','bundle.mjs'):
        shutil.copyfile(c.ROOT/'runtime/wasm32'/name,runtime/name)
    for name,body in proposal.runtime_sources().items():
        (runtime/Path(name).name).write_text(body)
    shutil.copyfile(HERE/'image.mjs',out/'image.mjs')
    shutil.copyfile(HERE/'check.mjs',out/'check.mjs')
    policy=c.read(c.STORE/'2026-09-20-stage1-materialization-r1/execution/policy.json')
    assert policy['materializer']['sha256']==c.sha(runtime/'materializer.mjs')
    c.save(out/'policy.json',policy)
    c.save(out/'versions.json',dict(abi=dict(name='B',version=1),
        layout=dict(version=1,sha256=c.sha(c.ROOT/'doc/WASM/contracts/wasm32-layout.v1.json'))))
    rows={}
    for p in sorted((out/'producer').glob('*.wasm')):
        x=subprocess.check_output(['/usr/local/bin/wasm-objdump','-x',p],text=True)
        d=subprocess.check_output(['/usr/local/bin/wasm-objdump','-d',p],text=True)
        p.with_suffix('.sections.txt').write_text(x);p.with_suffix('.instructions.txt').write_text(d)
        ops=sorted({line.split('|',1)[1].strip().split()[0] for line in d.splitlines()
                    if '|' in line and line.split('|',1)[1].strip()})
        features=set()
        if re.search(r'-> \([^)]*,',x):features.add('multivalue')
        if any(op.startswith('return_call') for op in ops):features.add('tailcall')
        if any('.atomic.' in op for op in ops):features.add('atomics')
        if set(ops)&{'try_table','throw','throw_ref'}:features.add('exceptions')
        if 'exnref' in d or 'throw_ref' in ops:features.add('exnref')
        if set(ops)&{'memory.copy','memory.fill','memory.init','data.drop'}:features.add('bulk')
        rows[p.stem.split('-')[1]]=dict(binary_sha256=c.sha(p),features=sorted(features),
            wait=any(op.startswith('memory.atomic.wait') or op=='memory.atomic.notify' for op in ops),
            legacy=bool(set(ops)&{'try','catch','catch_all','delegate','rethrow'}),
            instruction_mnemonics=ops,sections_sha256=c.sha(p.with_suffix('.sections.txt')),
            instructions_sha256=c.sha(p.with_suffix('.instructions.txt')))
    c.save(out/'classifications.json',rows)
    faults=out/'service-controls';faults.mkdir(exist_ok=True)
    wat=(out/'producer/module-2.wat').read_text()
    original='(import "integer" "calculate" (func $integer_slow (param i32 i32) (result i32)))'
    assert wat.count(original)==1
    variants={'name':original.replace('"calculate"','"unqualified"'),
              'signature':original.replace('(param i32 i32)','(param i64 i32)'),
              'duplicate':original+original.replace('$integer_slow','$duplicate')}
    for name,replacement in variants.items():
        changed=wat.replace(original,replacement)
        if name=='signature':
            call='(call $integer_slow (local.get $op)'
            assert changed.count(call)==1
            changed=changed.replace(call,'(call $integer_slow (i64.extend_i32_s (local.get $op))')
        path=faults/(name+'.wat');path.write_text(changed)
        c.command([c.WABT,'--enable-all',path,'-o',path.with_suffix('.wasm')],path.with_suffix('.log'))
    c.command([c.NODE,out/'image.mjs',out],out/'image.log')
    c.command([c.NODE,out/'check.mjs',out],out/'checks.log')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--image-only',action='store_true')
    parser.add_argument('--corpus',action='store_true')
    parser.add_argument('--native',action='store_true')
    parser.add_argument('--native-compare',action='store_true')
    args = parser.parse_args()
    with storage.lease([args.output]):
        if args.native or args.native_compare:
            spec=importlib.util.spec_from_file_location('cross_load_native',HERE/'native.py')
            native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
            native.run(args.output.resolve(),comparison_only=args.native_compare)
        elif args.corpus:
            spec=importlib.util.spec_from_file_location('cross_load_qualification',HERE/'qualify.py')
            qualification=importlib.util.module_from_spec(spec);spec.loader.exec_module(qualification)
            qualification.corpus(args.output.resolve())
        elif args.image_only:image(args.output.resolve())
        else:run(args.output.resolve())
