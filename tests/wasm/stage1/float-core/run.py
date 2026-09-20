import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
sys.set_int_max_str_digits(0)
from corpus import cases
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
CLANG=Path('/usr/local/opt/llvm/bin/clang');NODE=Path('/usr/local/bin/node')
DETECTOR='cde56ae04099bcfa37f2a29815f8e2d718c6d525d4893ceaec2c8e8691bfa302'
FLAGS=['--target=wasm32','-O2','-nostdlib','-fno-builtin','-fno-jump-tables','-ffp-contract=off','-Wall','-Wextra','-Werror','-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=65536','-Wl,-z,stack-size=65536','-Wl,--export=float_calculate']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log,env=None):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,cwd=log.parent,env=env,check=True,timeout=600)
def build(out):
 src=HERE.parents[1]/'stage0/float-detection/checked.wat';assert sha(src)==DETECTOR
 s=src.read_text();assert s.count('(memory 1 1)')==1;s=s.replace('(memory 1 1)','(memory 1 32769)');(out/'detector.wat').write_text(s)
 command(['/usr/local/bin/wat2wasm',out/'detector.wat','-o',out/'detector.wasm'],out/'detector-build.log')
 shutil.copy(HERE/'float.c',out/'float.c');command([CLANG,*FLAGS,out/'float.c','-o',out/'float.wasm'],out/'build.log')
def run(e,out):
 out.mkdir(parents=True,exist_ok=False);save(out/'toolchain.json',dict(flags=FLAGS,tools=[dict(path=str(Path(t).resolve()),sha256=sha(Path(t).resolve())) for t in [CLANG,NODE,'/usr/local/bin/wasm-ld','/usr/local/bin/wat2wasm','/usr/local/bin/wasm2wat','/usr/bin/clang']]));build(out);import structure;structure.run(out,sys.modules[__name__]);rows=cases();save(out/'cases.json',rows);shutil.copy(HERE/'execute.mjs',out/'execute.mjs')
 command([NODE,out/'execute.mjs',out/'float.wasm',out/'detector.wasm',out/'cases.json',out/'execution.json'],out/'execution.log')
 import native;native.run(e,out,rows,sys.modules[__name__])
 import hardware;hardware.run(out,rows,sys.modules[__name__])
 import controls;controls.run(out,sys.modules[__name__]);controls.oracle_regression(out,sys.modules[__name__])
 save(out/'summary.json',dict(status='PASS',cases=len(rows),target_comparisons=len(rows)*3,mutants=len(controls.faults()),oracle_controls=1,hardware_comparisons=json.loads((out/'hardware.json').read_text())['cases'],native=json.loads((out/'native.json').read_text())|{'differences':len(json.loads((out/'native.json').read_text())['differences'])},owner_refusals=63,exact_fits=6,gate_credit=False));print((out/'summary.json').read_text())
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
