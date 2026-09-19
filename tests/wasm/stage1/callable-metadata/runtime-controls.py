"""Re-execute real installation/restore faults against the unchanged compiler output."""
import json,shutil,subprocess
from pathlib import Path
NODE='/usr/local/bin/node'
def run(x,out):
 out.mkdir();rows=[]
 for name,file,old,new,oracle in [
 ('lost-function-relocation','snapshot.mjs',"if (tag === tags.function || tag === tags['simple-vector']) for", "if (tag === tags['simple-vector']) for",'restored pool identity'),
 ('installation-repair','loader.mjs','const raw={entry:instance.exports.entry,tail_entry:instance.exports.tail_entry};', 'new DataView(o.memory.buffer).setUint32(new DataView(o.memory.buffer).getUint32(row.imports.env.tcr+56,true),0,true);\n      const raw={entry:instance.exports.entry,tail_entry:instance.exports.tail_entry};','installation preserves metadata and environment bytes')]:
  d=out/name;d.mkdir()
  for n in ['execute.mjs','snapshot.mjs','transport.mjs','loader.mjs','binary.mjs','stub.wasm']:shutil.copy(x/n,d/n)
  p=d/file;s=p.read_text();assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
  argv=[NODE,str(d/'execute.mjs'),str(x/'compiled'),str(d/'result.json')];(d/'command.json').write_text(json.dumps(argv,indent=2)+'\n')
  with (d/'execution.log').open('w') as f:r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  text=(d/'execution.log').read_text();assert r.returncode!=0 and 'AssertionError' in text and oracle in text,(name,text[-2000:])
  rows.append(dict(name=name,status='REJECTED',oracle=oracle))
 (out/'controls.json').write_text(json.dumps(rows,indent=2,sort_keys=True)+'\n');return rows
