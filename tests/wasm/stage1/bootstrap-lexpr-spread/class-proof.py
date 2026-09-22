"""Join proposal masks and slot indices to the independently read native CPL."""
import json,sys
from pathlib import Path
import backend
BITS={'CONDITION':1,'SERIOUS-CONDITION':2,'ERROR':4,'SIMPLE-CONDITION':8,
      'TYPE-ERROR':32,'CONTROL-ERROR':64}
BITS.update({name.split('::')[-1].upper():1<<bit for name,bit,mask,slots in backend.CLASSES})
def check(out):
 rows=json.loads((out/'compiled/native-condition-classes.json').read_text());result=[]
 for name,bit,mask,slots in backend.CLASSES:
  row=next(r for r in rows if r['name']==name.split('::')[-1].upper())
  assert row['cpl'][0]==row['name']
  assert all(c in BITS or c in ('STANDARD-OBJECT','T') for c in row['cpl']),row
  native_mask=sum(BITS.get(c,0) for c in row['cpl'])
  assert native_mask==mask,(name,native_mask,mask)
  assert [s['name'].lower() for s in row['slots']]==slots,row
  assert mask*4<=2147483644
  result.append(dict(name=row['name'],mask=mask,slots=slots,cpl=row['cpl']))
 (out/'condition-class-proof.json').write_text(json.dumps(dict(status='PASS',rows=result),indent=2,sort_keys=True)+'\n')
if __name__=='__main__':check(Path(sys.argv[1]).resolve())
