from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
def derive():
 s=(ROOT/'runtime/wasm32/collector-owner.mjs').read_text()
 for a,b in [
  ("import {sha256} from './sha256.mjs';", "import {sha256} from './sha256.mjs';\nimport {CollectionStatistics} from './statistics.mjs';"),
  (' #roles=new Map();',' #statistics;\n #roles=new Map();'),
  ('static create(memory,bytes,digest,layout){','static create(memory,bytes,digest,layout,{clock}={}){'),
  ('const owner=new CollectorOwner();owner.#memory=memory;', 'const owner=new CollectorOwner();owner.#statistics=new CollectionStatistics(clock);owner.#memory=memory;'),
  (' get tcr(){', ' get statistics(){return this.#statistics.snapshot();}\n gctime(units=1000){return this.#statistics.gctime(units);}\n get tcr(){'),
  ('const status=this.#collector.collect(scratch.start);', 'const started=this.#statistics.sample();\n   const status=this.#collector.collect(scratch.start);'),
  ("need(status===0,'collection refused '+status);", "need(status===0,'collection refused '+status);\n   this.#statistics.committed(started,this.#get(scratch.start+92));"),
 ]:
  assert s.count(a)==1,a
  s=s.replace(a,b)
 return s
