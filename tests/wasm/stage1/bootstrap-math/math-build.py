"""Compile the reviewed float service plus pinned musl algorithms, without libc."""
from pathlib import Path
import subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]

def sources(out):
    source=(ROOT/'runtime/wasm32/float.c').read_text()
    at='static U calculate('
    assert source.count(at)==1
    source=source.replace(at,(HERE/'transcend.c').read_text()+'\n'+at)
    source=source.replace(' if(op>11)return 5;', ' if(op>=12&&op<=37&&native)return transcend(op,av,bv,in,end,out,limit,result,mask,safe);\n if(op>11)return 5;')
    (out/'float.c').write_text(source)
    owner=(ROOT/'runtime/wasm32/float-service.mjs').read_text().replace('op>11','op>37').replace('b=op>=10?0:stage(get(root+12))','b=op>=10&&![12,13,30,31].includes(op)?0:stage(get(root+12))')
    owner=owner.replace(' let busy=false;', " if(!(wasm.__stack_pointer instanceof WebAssembly.Global)||wasm.__stack_pointer.value>input)throw Error('FLOAT_STACK');\n let busy=false;")
    (out/'float-service.mjs').write_text(owner)

def build(out,runtime):
    sources(runtime)
    cmd=['/usr/local/opt/llvm/bin/clang','--target=wasm32','-O2','-nostdlib','-ffreestanding','-fno-builtin','-ffp-contract=off','-fno-jump-tables',
         '-Dhidden=__attribute__((visibility("hidden")))','-Wno-macro-redefined','-Wno-shift-op-parentheses','-I',str(HERE/'libm'),
         '-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,-z,stack-size=65536','-Wl,--global-base=1024',
         '-Wl,--export=float_calculate_lisp','-Wl,--export=float_calculate','-Wl,--export=__stack_pointer',str(runtime/'float.c'),
         *map(str,sorted((HERE/'libm').glob('*.c'))),'-o',str(out/'float.wasm')]
    subprocess.run(cmd,check=True)
