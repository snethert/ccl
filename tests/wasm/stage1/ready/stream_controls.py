"""The stream scanner's exact field count is independent of extent admission."""
from pathlib import Path
import shutil
import subprocess
import common as c
HERE=Path(__file__).resolve().parent

def check(out):
    work=out/'stream-count-control';work.mkdir()
    source=(out/'compiled/runtime/collector.c').read_text()
    old='else if(tag==50){if(n!=4)return reject(s,BAD_OBJECT);'
    assert source.count(old)==1
    (work/'collector.c').write_text(source.replace(old,'else if(tag==50){'))
    c.command(['/usr/local/opt/llvm/bin/clang','--target=wasm32','-O2','-nostdlib','-fno-builtin','-matomics','-mbulk-memory',
        '-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,--shared-memory',
        '-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer',
        work/'collector.c','-o',work/'collector.wasm'],work/'compile.log')
    try:c.command([c.NODE,HERE/'stream-shapes.mjs',work,work/'unexpected.json'],work/'check.log',timeout=60)
    except subprocess.CalledProcessError:
        assert 'stream count' in (work/'check.log').read_text()
    else:raise AssertionError('stream count omission survived')
    c.save(out/'stream-controls.json',dict(status='PASS',omission='stream field count',rejected_by='stream count',
        source=c.sha(work/'collector.c')))
    target=out/'development/stream-count';target.mkdir(parents=True)
    for name in ('collector.c','compile.log','check.log'):shutil.copyfile(work/name,target/name)
    shutil.rmtree(work)
