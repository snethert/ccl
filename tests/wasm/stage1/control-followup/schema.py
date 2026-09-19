"""Name LL19's persistent fields without changing the frozen v1 layout."""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
RENAMES={'scratch0':'stack_reserve_flags','scratch1':'debugger_depth'}
def build():
 p=ROOT/'doc/WASM/contracts/tcr.v1.json';old=json.loads(p.read_text())
 def rewrite(x):
  if isinstance(x,str):return RENAMES.get(x,x)
  if isinstance(x,list):return [rewrite(v) for v in x]
  if isinstance(x,dict):return {k:rewrite(v) for k,v in x.items()}
  return x
 new=rewrite(old);new['version']=2
 new['compatibility']={'layout':'Identical size, offsets, widths, alignment, classification and ownership to v1. Names replace the historical scratch labels. Existing generated architecture aliases remain valid at the same offsets.','v1_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'aliases':RENAMES}
 for f in new['fields']:
  if f['name']=='stack_reserve_flags':
   f['description']='Persistent recovery state: bit 0 suppresses soft-limit checks on all three stacks while a condition handler uses reserve capacity; other bits are preserved.';f['update']='Owning thread sets before soft-overflow signalling and restores on transfer. Hard limits remain checked.'
  if f['name']=='debugger_depth':
   f['description']='Persistent debugger-hook nesting depth, never a Lisp root.';f['update']='Owning thread saves/increments on hook entry and restores on normal or exceptional return.'
 new['rules']+=['stack_reserve_flags and debugger_depth must not be reused as scratch storage', 'reserve-in-use is shared across VSP/TSP/CSP, unlike native per-stack guards; hard limits remain active on each stack']
 check(old,new);return new

def check(old,new):
 assert new['size_bytes']==old['size_bytes'] and new['alignment']==old['alignment']
 assert new['version']==2 and new['compatibility']['aliases']==RENAMES
 assert len(new['fields'])==len(old['fields'])==48
 for a,b in zip(old['fields'],new['fields']):
  assert b['name']==RENAMES.get(a['name'],a['name'])
  for k in ('offset','width','alignment','classification','owner','group'):assert a[k]==b[k],k
 assert new['counts']==old['counts']
 return True
if __name__=='__main__':print(json.dumps(build(),indent=2,ensure_ascii=False))
