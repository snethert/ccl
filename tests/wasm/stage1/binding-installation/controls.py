"""Execute owner faults against the exact generated native-oracle corpus."""
import json,shutil,subprocess
from pathlib import Path
MUTANTS=[
 ('missing-alias-admitted',"need(names.length===expected.length&&new Set(names).size===names.length&&same([...names].sort(),[...expected].sort()),'COMPLETE_BINDINGS');","void names;",'missing-alias must refuse'),
 ('partial-entry-range',"need(same(r.ranges,entryRanges(b)),'ENTRY_RANGES');","void r.ranges;",'wrong-range-start must refuse'),
 ('wrong-arity-admitted',"need(same(ownerArity(raw),c.arity),'ARITY_IDENTITY');","void c.arity;",'wrong-arity must refuse'),
 ('stale-manifest-admitted',"m.previous===this.#head&&","true&&",'stale-runtime-manifest must refuse'),
 ('lost-alias-publication','for(const b of bindings)write(b.where,b.value);','for(const b of bindings.slice(0,1))write(b.where,b.value);','published package binding ["BINDING-B","F"]'),
 ('missing-rollback','for(let i=journal.length-1;i>=0;i--)put(...journal[i]);','for(let i=journal.length-1;i<0;i--)put(...journal[i]);','missing-global-import atomic refusal'),
 ('old-code-overwritten','// Keep prior module instances and code rows alive for saved function objects.','''// Fault: overwrite an earlier same-arity entry at redefinition.
  if(this.#generation===3){const old=[...this.#modules.values()].find(c=>c.arity[0]===0&&c.arity[1]===0);const fresh=[...staged.values()][0];o.table.set(old.slot,o.table.get(fresh.slot));o.tail_table.set(old.slot,o.tail_table.get(fresh.slot));}''','old code survives'),
]
def run(x,out):
 out.mkdir();rows=[]
 for name,old,new,oracle in MUTANTS:
  d=out/name;d.mkdir()
  for n in ['installer.mjs','ranges.mjs','execute.mjs','loader.mjs','binary.mjs','stub.wasm']:shutil.copy(x/n,d/n)
  p=d/'installer.mjs';s=p.read_text();assert s.count(old)==1,name;p.write_text(s.replace(old,new))
  argv=['/usr/local/bin/node',str(d/'execute.mjs'),str(x/'compiled'),str(d/'execution.json')];(d/'command.json').write_text(json.dumps(argv,indent=2)+'\n')
  with (d/'execution.log').open('w') as f:r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  log=(d/'execution.log').read_text();assert r.returncode and 'AssertionError' in log and oracle in log,(name,log[-2000:]);rows.append(dict(name=name,status='REJECTED',oracle=oracle))
 (out/'controls.json').write_text(json.dumps(rows,indent=2,sort_keys=True)+'\n');return rows
