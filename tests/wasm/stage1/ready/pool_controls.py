"""Pool scanner count, clearing and unchanged collector-owner regression."""
from pathlib import Path
import shutil
import subprocess
import common as c
HERE=Path(__file__).resolve().parent

def check(out):
    compiled=out/'compiled';source=(compiled/'runtime/collector.c').read_text()
    c.command([c.NODE,HERE/'pool-shapes.mjs',compiled,out/'pool-shapes.json'],out/'pool-shapes.log',timeout=60)
    controls=[]
    for name,old,new,reason in [
      ('count','if(n!=1)return reject(s,BAD_OBJECT);scan=0;size=8;','scan=0;size=8;','pool count'),
      ('clear','if(LOAD(p)==338)STORE(p+4,NIL);','','pool cleared')]:
        work=out/'development'/('pool-'+name);work.mkdir(parents=True,exist_ok=True)
        assert source.count(old)==1
        (work/'collector.c').write_text(source.replace(old,new))
        c.command(['/usr/local/opt/llvm/bin/clang','--target=wasm32','-O2','-nostdlib','-fno-builtin','-matomics','-mbulk-memory',
          '-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,--shared-memory',
          '-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer',
          work/'collector.c','-o',work/'collector.wasm'],work/'compile.log')
        try:c.command([c.NODE,HERE/'pool-shapes.mjs',work,work/'unexpected.json'],work/'check.log',timeout=60)
        except subprocess.CalledProcessError:assert reason in (work/'check.log').read_text()
        else:raise AssertionError(name+' omission survived')
        controls.append(dict(omission=name,rejected_by=reason,source=c.sha(work/'collector.c')))
    work=out/'collector-owner';work.mkdir(exist_ok=True)
    for p in (compiled/'runtime').glob('*.mjs'):shutil.copyfile(p,work/p.name)
    shutil.copyfile(work/'collector-owner.mjs',work/'owner.mjs')
    check=HERE.parent/'collector-owner/check.mjs';shutil.copyfile(check,work/'check.mjs')
    c.command([c.NODE,work/'check.mjs',compiled/'collector.wasm',work/'results.json'],work/'run.log',timeout=60)
    owner=c.read(work/'results.json');assert owner['checks']==40 and owner['status']=='PASS'
    c.save(out/'pool-controls.json',dict(status='PASS',shape_checks=8,omissions=controls,owner_checks=40,
                                      owner_source=c.sha(check),collector=c.sha(compiled/'collector.wasm')))
    shutil.rmtree(work)
    return c.read(out/'pool-controls.json')
