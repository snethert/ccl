"""Reuse the integrated build and extend its pinned musl source set."""
from pathlib import Path
import importlib.util,shutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def sources(out):
    old=(ROOT/'runtime/wasm32/transcend.c').read_text()
    new=old.replace('DECLARE(log) ', 'DECLARE(asinh) DECLARE(acosh) DECLARE(atanh)\nDECLARE(log) ')
    new=new.replace(' UNARY(10,exp) UNARY(11,sinh) UNARY(12,tanh)',
                    ' UNARY(10,exp) UNARY(11,sinh) UNARY(12,tanh)\n UNARY(13,asinh) UNARY(14,acosh) UNARY(15,atanh)')
    new=new.replace('(i==6&&x==0)||', '(i==6&&x==0)||(i==15&&(x==1||x==-1))||')
    text=(ROOT/'runtime/wasm32/float.c').read_text();assert text.count(old)==1
    text=text.replace(old,new).replace('op<=37','op<=43')
    (out/'float.c').write_text(text);(out/'transcend.c').write_text(new)
    text=(ROOT/'runtime/wasm32/float-service.mjs').read_text();assert text.count('op>37')==1
    (out/'float-service.mjs').write_text(text.replace('op>37','op>43'))

def build(out,runtime):
    sources(runtime)
    shutil.copytree(ROOT/'runtime/wasm32/libm',runtime/'libm',dirs_exist_ok=True)
    for p in (HERE/'libm').glob('*.c'):shutil.copy(p,runtime/'libm'/p.name)
    spec=importlib.util.spec_from_file_location('hyperbolic_float_build',ROOT/'runtime/wasm32/build-float.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.HERE=runtime;module.sources=lambda destination:None
    module.build(out,runtime)
