"""Keep unavailable native entries and their remaining emitted callers explicit."""
from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parent

def report(environment,numeric):
    exclusions=json.loads((HERE/'exclusions.json').read_text())
    rows=json.loads((environment/'results.json').read_text())
    records=[(f['file'],r) for f in rows for r in f['records'] if r['definition'] is not None]
    result=[]
    for file,names in exclusions.items():
        for name in names:
            assert not any(f.removeprefix('ccl:').replace(';','/').removesuffix('.newest')==file and r['name']==name.upper() for f,r in records)
            callers=[dict(file=f,name=r['name'],outcome=r['outcome']) for f,r in records if name.upper() in r['dependencies']]
            result.append(dict(file=file,name=name,disposition='native-pointer implementation excluded',
              remaining_emitted_callers=callers,
              obligation='Every retained caller needs a target implementation or an explicit profile exclusion. No replacement or closure credit is inferred.'))
    out=dict(definitions=result,excluded=16,scope='Direct dependencies emitted by the current whole-file compiler only; refused bodies and dynamic calls may contain additional callers. File IO, synchronization, scheduler, bignum scratch storage and host exit remain required target work, not excluded APIs.')
    (numeric/'ffi-exclusions.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':report(*(Path(x).resolve() for x in sys.argv[1:]))
