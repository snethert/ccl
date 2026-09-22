"""Changed-site controls: wrong libm dispatch, pole flags, and owner admission."""
from pathlib import Path
import importlib.util,json,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent
out=Path(sys.argv[1]).resolve()
spec=importlib.util.spec_from_file_location('hyperbolic_build_controls',HERE/'math-build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
rows=[]
for name,old,new,expected in (
 ('dispatch','UNARY(13,asinh)','UNARY(13,sin)','asinh/'),
 ('pole-flags','(i==15&&(x==1||x==-1))||','','4 !== 2'),
):
    dest=out/'faults'/name;runtime=dest/'runtime';runtime.mkdir(parents=True)
    build.build(dest,runtime)
    text=(runtime/'float.c').read_text();assert text.count(old)==1
    (runtime/'float.c').write_text(text.replace(old,new))
    spec=importlib.util.spec_from_file_location('fault_build',build.ROOT/'runtime/wasm32/build-float.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.HERE=runtime;module.sources=lambda p:None;module.build(dest,runtime)
    shutil.copy(out/'detector.wasm',dest/'detector.wasm')
    result=subprocess.run(['/usr/local/bin/node',HERE/'math-check.mjs',dest,dest/'result.json'],capture_output=True,text=True)
    (dest/'failure.log').write_text(result.stdout+result.stderr)
    assert result.returncode and expected in result.stderr,(name,result.stderr)
    rows.append(dict(name=name,rejected=True,oracle=expected))
# Removing the six new owner operations must fail through the generated path.
dest=out/'faults/owner-range';dest.mkdir(parents=True)
for name in ('compiled','collector.wasm','integer.wasm','float.wasm','detector.wasm','eql.wasm','check.mjs','install.mjs'):
    p=out/name
    if p.suffix=='.mjs':shutil.copy(p,dest/p.name)
    else:(dest/p.name).symlink_to(p,target_is_directory=p.is_dir())
shutil.copytree(out/'runtime',dest/'runtime')
p=dest/'runtime/float-service.mjs';text=p.read_text();assert text.count('op>43')==1;p.write_text(text.replace('op>43','op>37'))
result=subprocess.run(['/usr/local/bin/node',dest/'check.mjs',dest,dest/'rejected.json'],capture_output=True,text=True,timeout=120)
(dest/'failure.log').write_text(result.stdout+result.stderr)
assert result.returncode and 'CORE-HYPER-' in result.stdout+result.stderr
rows.append(dict(name='owner-range',rejected=True,oracle='first generated hyperbolic call'))
(out/'faults.json').write_text(json.dumps(dict(status='PASS',faults=rows),indent=2,sort_keys=True)+'\n')
