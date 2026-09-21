#!/usr/bin/env python3
import argparse,importlib.util,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('review128',HERE.parent/'startup-winners-review/run.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
read,save,sha,command,replace=old.read,old.save,old.sha,old.command,old.replace
PARENT='2026-09-20-stage1-startup-winners-review-r1';WIN=old.WIN
SOURCES=('run.py','packet.py','README.md','scope.json')
def pins(e):
 p=read(e/PARENT/'source-pins.json')
 for n,h in p.items():assert sha(ROOT/n)==h,n
 for n in SOURCES:p[str((HERE/n).relative_to(ROOT))]=sha(HERE/n)
 return dict(sorted(p.items()))
def check(e):
 p=e/PARENT
 for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 for n,h in read(p/'inputs.json').items():assert sha(e/n)==h,n
 for n,h in read(p/'tools.json').items():assert sha(Path(n))==h,n
 for r in read(e/WIN/'packet.json')['files']:assert sha(e/WIN/r['path'])==r['sha256'],r['path']
 return pins(e)
def run(e,out):
 source=check(e);out.mkdir(parents=True,exist_ok=False)
 p=e/PARENT/'execution/winners';src=e/WIN/'execution'
 previous=(p/'check.mjs').read_text()
 poison=""" setup(4);primitive(1,T,28);
 // Every result word starts with the complement of its required value.
 // An omitted store, stale-content rewrite or partial store cannot pass.
 const required=[ht,NIL,1,0],poison=required.map(x=>(~x)>>>0);
 poison.forEach((x,i)=>put(RESULT+4*i,x));
 assert(poison.every((x,i)=>x!==required[i]),'distinct publication poison');
"""
 fixed=replace(previous,' setup(4);primitive(1,T,28);\n',poison)
 target=out/'positive';old.copy_inputs(src,target);(target/'check.mjs').write_text(fixed);shutil.copy(src/'hash.wasm',target/'hash.wasm')
 command([old.NODE,target/'check.mjs',target,target/'execution.json'],target/'execution.log')
 assert (target/'execution.json').read_bytes()==(src/'execution.json').read_bytes()
 code=(src/'hash.c').read_text();tail='S(result,v);S(result+4,found);S(result+8,op==0?2:1);S(result+12,rehashed);return 0;'
 assert code.count(tail)==1
 faults=[
  ('omit-primary','S(result,v);','if(op!=5)S(result,v);',False),
  ('omit-secondary','S(result+4,found);','if(op!=5)S(result+4,found);',True),
  ('omit-count','S(result+8,op==0?2:1);','if(op!=5)S(result+8,op==0?2:1);',True),
  ('omit-rehashed','S(result+12,rehashed);','if(op!=5)S(result+12,rehashed);',True),
  ('omit-tail',tail,'if(op==5){S(result,v);return 0;}'+tail,True),
  ('rewrite-stale-tail',tail,'if(op==5){volatile U *p=(volatile U *)(unsigned long)result;U a=p[1],b=p[2],c=p[3];p[0]=v;p[1]=a;p[2]=b;p[3]=c;return 0;}'+tail,True),
 ]
 controls=[]
 for name,a,b,escaped in faults:
  m=out/'faults'/name;old.copy_inputs(src,m);(m/'hash.c').write_text(replace(code,a,b));(m/'previous.mjs').write_text(previous);(m/'fixed.mjs').write_text(fixed)
  command([old.CLANG,*old.FLAGS,*['-Wl,--export='+n for n in ['ht_size','ht_init','ht_run']],m/'hash.c','-o',m/'hash.wasm'],m/'build.log')
  command([old.NODE,m/'previous.mjs',m,m/'previous.json'],m/'previous.log',None if escaped else 'raw clear publication')
  if escaped:assert (m/'previous.json').read_bytes()==(src/'execution.json').read_bytes(),name
  command([old.NODE,m/'fixed.mjs',m,m/'execution.json'],m/'rejected.log','raw clear publication')
  controls.append(dict(name=name,previous='ESCAPED' if escaped else 'REJECTED',corrected='REJECTED',diagnostic='raw clear publication',binary=sha(m/'hash.wasm')))
 inherited=[]
 earlier=read(p/'controls.json')
 for row in earlier['publication']+earlier['inherited']:
  name=row['name'];m=out/'inherited'/name;old.copy_inputs(src,m);(m/'check.mjs').write_text(fixed)
  origin=p/'faults'/name if row in earlier['publication'] else src/'faults'/name
  shutil.copy(origin/'hash.wasm',m/'hash.wasm')
  command([old.NODE,m/'check.mjs',m,m/'execution.json'],m/'rejected.log',row['diagnostic'])
  inherited.append(dict(name=name,status='REJECTED',diagnostic=row['diagnostic']))
 save(out/'controls.json',dict(new=controls,inherited=inherited))
 assert pins(e)==source
 save(out/'summary.json',dict(status='PASS',new_faults=len(controls),previous_escapes=sum(c['previous']=='ESCAPED' for c in controls),inherited_faults=len(inherited),positive_execution_sha256=sha(target/'execution.json'),positive_identical=True,source_pins=len(source),compiler_service_adapter_unchanged=True,ordering='Audit 129 closed ordering; registry-order evidence reused unchanged by hash',slot_credit=False))
 print(read(out/'summary.json'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
