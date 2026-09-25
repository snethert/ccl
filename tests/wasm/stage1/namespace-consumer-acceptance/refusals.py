"""Qualify O-73 without changing any reviewed product byte."""
from pathlib import Path
import argparse, sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage

CLAUSES={
 'range alignment':'(lo&7)', 'range order':'hi<lo',
 'range stride':'((hi-lo)&31)', 'range backing':'!span(lo,(W)hi-lo)',
 'package overlap':'overlap(lo,(W)hi-lo,base,(W)end-base)',
 'descriptor overlap':'overlap(lo,(W)hi-lo,c,80)',
 'scratch overlap':'overlap(lo,(W)hi-lo,sc,sz)',
 'result overlap':'overlap(lo,(W)hi-lo,result,16)',
 'zero linked base':'!lo', 'symbol below range':'p<lo',
 'symbol above range':'(W)p+32>hi', 'symbol stride':'((p-lo)&31)',
}
FLAGS=['--target=wasm32','-O2','-nostdlib','-fno-builtin','-Wl,--no-entry',
 '-Wl,--export-all','-Wl,--import-memory','-Wl,--max-memory=2147549184',
 '-Wl,--shared-memory','-matomics','-mbulk-memory','-Wl,--global-base=1048576',
 '-Wl,-z,stack-size=65536']

def run(out,source):
 out.mkdir(parents=True,exist_ok=True)
 original=source.read_text()
 def build(name,body):
  path=out/(name+'.c');path.write_text(body);binary=path.with_suffix('.wasm')
  c.command(['/usr/local/opt/llvm/bin/clang',*FLAGS,path,'-o',binary],out/(name+'.build.log'))
  return binary
 binary=build('symbols',original)
 c.command([c.NODE,HERE/'controls.mjs',binary,out/'controls.json'],out/'controls.log')
 mutants=[]
 for i,(name,clause) in enumerate(CLAUSES.items()):
  assert original.count(clause)==1,(name,clause)
  mutant=build('omit-'+str(i),original.replace(clause,'0'))
  record=out/('omit-'+str(i)+'.json')
  # The exact malformed input passes the complete public operation only
  # after this single check is removed. A trap or another refusal fails.
  c.command([c.NODE,HERE/'controls.mjs',mutant,record,name,'admit'],out/('omit-'+str(i)+'.log'))
  mutants.append(dict(clause=clause,control=name,without_check=c.read(record),
                      source=c.sha(mutant.with_suffix('.c')),wasm=c.sha(mutant)))
 # The thirteenth clause is redundant under admitted config, and also
 # duplicated by symbase's final span check. Retain the single-deletion
 # survivor deliberately, with its logical proof in README.
 clause='!span(p,32)';assert original.count(clause)==1
 redundant=build('redundant-span',original.replace(clause,'0'))
 c.command([c.NODE,HERE/'controls.mjs',redundant,out/'redundant-span.json'],out/'redundant-span.log')
 assert c.read(out/'controls.json')==c.read(out/'redundant-span.json')
 record=dict(status='PASS',source=c.sha(source),wasm=c.sha(binary),
  controls=c.read(out/'controls.json'),isolated_mutants=mutants,
  equivalent_clause=clause,equivalence='lo <= p and p+32 <= hi <= memory size; final symbase span also remains',
  product_changed=False,slot_credit=False)
 c.save(out/'refusals.json',record)
 return record

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('out',type=Path);parser.add_argument('source',type=Path)
 args=parser.parse_args()
 with storage.lease([args.out]):
  result=run(args.out,args.source)
  print('PASS: 12 isolated refusals and single-check mutants; 1 equivalent clause')
