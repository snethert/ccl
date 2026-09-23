"""Compile the reviewed float service plus pinned musl algorithms, without libc."""
from pathlib import Path
import subprocess
HERE=Path(__file__).resolve().parent

def sources(out):
    for name in ('float.c','transcend.c','float-service.mjs'):
        data=(HERE/name).read_bytes()
        (out/name).write_bytes(data)

def build(out,runtime):
    sources(runtime)
    cmd=['/usr/local/opt/llvm/bin/clang','--target=wasm32','-O2','-nostdlib','-ffreestanding','-fno-builtin','-ffp-contract=off','-fno-jump-tables',
         '-Dhidden=__attribute__((visibility("hidden")))','-Wno-macro-redefined','-Wno-shift-op-parentheses','-I',str(HERE/'libm'),
         '-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,-z,stack-size=65536','-Wl,--global-base=1024',
         '-Wl,--export=float_calculate_lisp','-Wl,--export=float_calculate','-Wl,--export=__stack_pointer',str(runtime/'float.c'),
         *map(str,sorted((HERE/'libm').glob('*.c'))),'-o',str(out/'float.wasm')]
    subprocess.run(cmd,check=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);build(a.output,a.output)
