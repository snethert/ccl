"""Single-site runtime faults executed against the unchanged positive oracles."""
import json,os,shutil,subprocess,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent

def run(base,command,clang,flags):
 out=base/'controls';out.mkdir();rows=[]
 c=(base/'collector.c').read_text();owner=(base/'collector-owner.mjs').read_text()
 tests=[
 ('active-results','c','n=LOAD(s->tcr+116);','n=0;','roots','active values moved'),
 ('bit-rounding','c','case 255:return (n+7)/8;','case 255:return n/8;','literals','bits_33: moved active values'),
 ('byte-width','c','case 199:case 207:return n;','case 199:case 207:return n*4;','literals','collection refused 3'),
 ('raw-payload-as-roots','c','return t==10||','return t==167||t==10||','literals','raw_tag_words: native literals'),
 ('omit-module-constants','owner','for(const group of this.#layout.groups)slots.push(...group.slots);',"for(const group of this.#layout.groups)if(group.kind!=='module-constants')slots.push(...group.slots);",'roots','superseded callback datum'),
 ('omit-callbacks-generated','owner','for(const group of this.#layout.groups)slots.push(...group.slots);',"for(const group of this.#layout.groups)if(group.kind!=='callbacks')slots.push(...group.slots);",'roots','superseded callback datum'),
 ('omit-registry','owner','for(const group of this.#layout.groups)slots.push(...group.slots);',"for(const group of this.#layout.groups)if(group.kind!=='registry')slots.push(...group.slots);",'roots','superseded callback datum'),
 ('omit-host','owner','for(const group of this.#layout.groups)slots.push(...group.slots);',"for(const group of this.#layout.groups)if(group.kind!=='host')slots.push(...group.slots);",'roots','superseded callback datum'),
 ('omit-pinned-bits','owner','else if(tag===255)raw=Math.ceil(n/8);','','pinned','collector-owner: image kind'),
 ]
 # Reuse all eight reviewed owner controls against the extended owner.
 spec=importlib.util.spec_from_file_location('owner_controls',HERE.parent/'collector-owner/controls.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 tests += [(name,'owner',old,new,'owner',diagnostic) for name,old,new,diagnostic in m.MUTANTS]
 for name,kind,old,new,oracle,diagnostic in tests:
  d=out/name;d.mkdir();source=c if kind=='c' else owner
  assert source.count(old)==1,(name,source.count(old))
  for n in ['collector-owner.mjs','owner.mjs','loader.mjs','binary.mjs','stub.wasm','setup.mjs','allocation-service.mjs','roots.mjs','literals.mjs','owner-check.mjs']:shutil.copy(base/n,d/n)
  wasm=base/'collector.wasm'
  if kind=='c':
   (d/'collector.c').write_text(source.replace(old,new));wasm=d/'collector.wasm';command([clang,*flags,d/'collector.c','-o',wasm],d/'compile.log')
  else:
   for n in ['owner.mjs','collector-owner.mjs']:(d/n).write_text(source.replace(old,new))
  script='literals' if oracle=='pinned' else oracle
  argv=['/usr/local/bin/node',str(d/(('owner-check' if script=='owner' else script)+'.mjs'))]
  if script!='owner':argv.append(str(base/('constants' if script=='literals' else 'generated')))
  argv += [str(wasm),str(d/'unexpected.json')]
  env=dict(os.environ,LITERAL_LAYOUT='pinned' if oracle=='pinned' else 'low')
  (d/'command.json').write_text(json.dumps(argv,indent=2)+'\n')
  p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=90,env=env);(d/'output.log').write_text(p.stdout)
  assert p.returncode!=0 and diagnostic in p.stdout,(name,p.returncode,p.stdout[-2000:])
  rows.append(dict(name=name,status='REJECTED',diagnostic=diagnostic,returncode=p.returncode))
 result=dict(status='PASS',mutants=rows);(out/'controls.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');return result
