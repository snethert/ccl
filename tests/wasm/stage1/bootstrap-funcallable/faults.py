"""Changed-site controls; each omission must fail the focused positive runner."""
from pathlib import Path
import json,os,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent

def run(out):
    root=out/'faults'
    if root.exists():shutil.rmtree(root)
    root.mkdir();rows=[]
    env={**os.environ,'CCL_LIBRARY_CASE':'CORE-GF-IDENTITY'}
    for name in ['positive','collector-seventh-field','manifest-immediates-identity','pinned-function-shape','snapshot-vector-shape']:
        d=root/name;d.mkdir(exist_ok=True)
        for p in out.iterdir():
            if p.suffix in ('.mjs','.json','.wasm'):shutil.copy(p,d/p.name)
        shutil.copytree(out/'runtime',d/'runtime',dirs_exist_ok=True)
        (d/'compiled').symlink_to(out/'compiled',target_is_directory=True)
        if name=='collector-seventh-field':
            source=(out/'runtime/collector.c').read_text();old='scan=o->scan;p=o->moved;';assert source.count(old)==1
            source=source.replace(old,'scan=o->scan;p=o->moved;if(LOAD(p)==1834)scan=6;')
            (d/'collector.c').write_text(source)
            subprocess.run(['/usr/local/opt/llvm/bin/clang','--target=wasm32','-O2','-nostdlib','-fno-builtin','-matomics','-mbulk-memory','-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,--shared-memory','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer',d/'collector.c','-o',d/'collector.wasm'],check=True)
        if name=='manifest-immediates-identity':
            p=d/'runtime/installer.mjs';s=p.read_text();old="need(get(raw+28)===f.immediates,'IMMEDIATES_IDENTITY');";assert s.count(old)==1;p.write_text(s.replace(old,''))
        if name=='pinned-function-shape':
            p=d/'runtime/collector-owner.mjs';s=p.read_text();old="need(n===6||n===7,'image function shape');";assert s.count(old)==1;p.write_text(s.replace(old,''))
        if name=='snapshot-vector-shape':
            p=d/'snapshot.mjs';s=p.read_text();old="check(bytes.readUInt32LE(offset)===2042,'function immediates shape');";assert s.count(old)==1;p.write_text(s.replace(old,''))
        if name=='pinned-function-shape':cmd=['/usr/local/bin/node',d/'owner-check.mjs',d/'collector.wasm',d/'result.json'];needle='image function shape'
        elif name=='snapshot-vector-shape':cmd=['/usr/local/bin/node',d/'snapshot-check.mjs',d/'result.json'];needle='Missing expected exception'
        else:cmd=['/usr/local/bin/node',d/'check.mjs',d,d/'result.json'];needle='core_gf_ref' if name=='collector-seventh-field' else 'IMMEDIATES_IDENTITY'
        result=subprocess.run(cmd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
        (d/'execution.log').write_text(result.stdout)
        if name=='positive':assert result.returncode==0,result.stdout
        else:assert result.returncode!=0 and needle in result.stdout,(name,result.stdout[-2000:])
        rows.append(dict(name=name,status='PASS' if name=='positive' else 'REJECTED',diagnostic=None if name=='positive' else needle))
    (out/'faults.json').write_text(json.dumps(dict(status='PASS',rows=rows),indent=2)+'\n')
if __name__=='__main__':run(Path(sys.argv[1]).resolve())
