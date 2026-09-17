#!/usr/bin/env python3
"""Damage materialized target objects, retaining valid module identities."""
import json,shutil,struct,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent

def run(positive,out):
 out.mkdir(parents=True,exist_ok=False)
 original=json.loads((positive/'materialized.json').read_text());mods=json.loads((positive/'modules.json').read_text());base=original['base']
 def mutate(name):
  row=json.loads(json.dumps(original));data=bytearray.fromhex(row['image'])
  def word(at):return struct.unpack_from('<I',data,at-base)[0]
  def put(at,value):struct.pack_into('<I',data,at-base,value)
  def literal(case):
   root=row['roots'][next(i for i,m in enumerate(mods) if m['name']==case)]
   return word(root-2)
  if name=='bignum-limb':p=literal('integer');put(p-2,word(p-2)^1)
  elif name=='float-bits':p=literal('float');put(p-2,word(p-2)^1)
  elif name=='tagged-string-elements':p=literal('string');put(p-2,word(p-2)*4)
  elif name=='vector-element-width':p=literal('vector');put(p-2,65535)
  elif name=='merge-equal-objects':p=literal('sharing');put(p+10,word(p+6))
  elif name=='split-shared-cycle':
   p=literal('sharing');old=word(p-2);new=base+len(data)+1
   row['objects'].append({'id':'mutant-copy','offset':len(data),'tag':1});data.extend(struct.pack('<II',new,word(old+3)));put(p+2,new)
  elif name=='omit-cold-pool':row['roots'][next(i for i,m in enumerate(mods) if m['name']=='cold')]=77825
  else:raise ValueError(name)
  row['image']=data.hex();return row
 rows=[]
 for name,oracle in [('bignum-limb','integer'),('float-bits','float'),('tagged-string-elements','tail_pool'),('vector-element-width','vector'),('merge-equal-objects','sharing'),('split-shared-cycle','sharing'),('omit-cold-pool','cold pool retained')]:
  dest=out/name;dest.mkdir()
  for p in positive.iterdir():
   if p.suffix=='.wasm' or p.name in ('modules.json','expected.json'):shutil.copy(p,dest/p.name)
  (dest/'materialized.json').write_text(json.dumps(mutate(name)))
  command=['/usr/local/bin/node',str(HERE/'execute_compiled.mjs'),str(dest)]
  (dest/'command.json').write_text(json.dumps(command))
  r=subprocess.run(command,capture_output=True,text=True,timeout=120);log=r.stdout+r.stderr;(dest/'failure.log').write_text(log)
  if r.returncode==0 or oracle not in log:raise ValueError('image control '+name+' did not fail at '+oracle)
  rows.append({'name':name,'status':'REJECTED','oracle':oracle,'module_bytes_unchanged':True})
 (out/'controls.json').write_text(json.dumps(rows,indent=2)+'\n');return rows
if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
