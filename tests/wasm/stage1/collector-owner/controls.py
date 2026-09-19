"""Single-site owner omissions, exercised by the unchanged executable oracle."""
import json,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
MUTANTS=[
 ('omit-callbacks','for(const group of this.#layout.groups)slots.push(...group.slots);',"for(const group of this.#layout.groups)if(group.kind!=='callbacks')slots.push(...group.slots);",'root family moved 1'),
 ('omit-next-method','slots.push(this.#layout.tcr+188);','/* omitted next-method root */','root family moved 4'),
 ('omit-image-pool','return result;','return result.filter(p=>p!==786456);','root family moved 6'),
 ('raw-metadata-root','slots.push(this.#layout.tcr+188);','slots.push(this.#layout.tcr+188,262272);','precise live count'),
 ('unowned-canonical',"need(images.some(r=>contains(r,NIL-1,8))&&images.some(r=>contains(r,T-6,32)),'canonical object ownership');",'/* ownership omitted */','missing-canonical-image'),
 ('stale-host-view','if(!this.#view||this.#view.buffer!==buffer)','if(!this.#view)','growth view'),
 ('grow-without-reclaim','const collection=this.collect();','const collection={};','retry reclaims before growth'),
 ('unpublished-boundary',"need(this.#boundary&&!this.#busy,'legal owner boundary');",'/* boundary omitted */','outside-boundary'),
]
def run(out,wasm,compiled):
 out.mkdir();source=(HERE/'owner.mjs').read_text();rows=[]
 for name,old,new,diagnostic in MUTANTS:
  assert source.count(old)==1,(name,source.count(old))
  d=out/name;d.mkdir();(d/'owner.mjs').write_text(source.replace(old,new));shutil.copy(HERE/'check.mjs',d/'check.mjs')
  argv=['/usr/local/bin/node',str(d/'check.mjs'),str(wasm),str(d/'unexpected.json'),str(compiled)]
  p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=90);(d/'output.log').write_text(p.stdout)
  assert p.returncode!=0 and diagnostic in p.stdout,(name,p.returncode,p.stdout[-1500:])
  rows.append(dict(name=name,status='REJECTED',diagnostic=diagnostic,returncode=p.returncode))
 result=dict(status='PASS',mutants=rows);(out/'controls.json').write_text(json.dumps(result,indent=2)+'\n');return result
