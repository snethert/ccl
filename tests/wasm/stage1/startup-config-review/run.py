#!/usr/bin/env python3
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE));from derive import derive,tcr_check
PARENT='2026-09-20-stage1-startup-config-r1';RESETS='2026-09-20-stage1-startup-resets-r1'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
def check_parent(e):
 for key in [PARENT,RESETS]:
  p=e/key
  for n,h in read(p/'source-pins.json').items():assert sha(ROOT/n)==h,n
  for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 return read(e/PARENT/'source-pins.json')
def reset_run(e,out):
 p=e/RESETS/'execution';out.mkdir()
 for f in p.iterdir():
  if f.is_file() and (f.suffix in ['.mjs','.wasm'] or f.name in ['selection.json','expected.json','tcr.json']):shutil.copy(f,out/f.name)
 shutil.copytree(p/'compiled',out/'compiled')
 s=(ROOT/'tests/wasm/stage1/startup-resets/check.mjs').read_text();(out/'check.mjs').write_text(tcr_check(s))
 command(['/usr/local/bin/node',out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 assert (out/'execution.json').read_bytes()==(p/'execution.json').read_bytes()
 save(out/'verification.json',dict(status='PASS',retained_execution=RESETS+'/execution/execution.json',sha256=sha(out/'execution.json'),stronger_tcr_check=True))
def run(e,out):
 out.mkdir(parents=True,exist_ok=False);check_parent(e);overlay=derive(out/'overlay')
 runner=load('config_r2_run',overlay/'run.py');runner.ROOT=ROOT
 runner.run(e,out/'config')
 reset_run(e,out/'resets')
 import regression
 regression.run(e,out,command,read,save)
 summary=read(out/'config/summary.json');summary.update(slot_credit=False,reset_replay_identical=True,regression_controls=read(out/'regressions.json'),native_cpu_probe=read(out/'config/compiled/native-cpu-probe.json'))
 save(out/'summary.json',summary);check_parent(e);print(json.dumps(summary,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
