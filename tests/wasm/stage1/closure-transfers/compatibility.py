"""Require unchanged bytes for every inherited function without TAGBODY IR."""
import hashlib,json,tarfile
from pathlib import Path
def check(e,compiled):
 roots=json.loads((compiled/'root-ir.json').read_text());stable={r['name'] for r in roots if all(op!='LOCAL-TAGBODY' for op,n in r['storage_ops'])}
 rows=[]
 with tarfile.open(e/'2026-09-19-stage1-temporaries-r1/execution.tar.gz') as t:
  for m in t.getmembers():
   n=Path(m.name)
   if len(n.parts)==3 and n.parts[:2]==('generated','compiled') and n.suffix in ('.wat','.wasm') and n.stem in stable:
    old=t.extractfile(m).read();new=(compiled/n.name).read_bytes();assert old==new,n.name
    rows.append(dict(path=n.name,sha256=hashlib.sha256(new).hexdigest()))
 assert len(rows)==2*len(stable) and len(stable)>10
 return dict(status='PASS',functions=len(stable),files=len(rows),records=rows)
