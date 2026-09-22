"""Extend the accepted fixture snapshot reader for the second function shape."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def derive():
    s=(HERE.parent/'constants/snapshot.mjs').read_text()
    s=s.replace("new URL('../../../../doc/WASM/contracts/wasm32-layout.v1.json', import.meta.url)","new URL('./layout.json', import.meta.url)")
    s=s.replace('export const digest', "tags.function = schema.subtags.find(x => x.name === 'subtag-function').value;\nexport const digest")
    s=s.replace("if (tag === tags['simple-vector']) payload = 4*count;", "if (tag === tags.function) {check(count === 6 || count === 7, 'function count'); payload = 4*count;}\n      else if (tag === tags['simple-vector']) payload = 4*count;")
    s=s.replace("if (tag === tags['simple-vector']) for", "if (tag === tags.function || tag === tags['simple-vector']) for")
    marker="  check(cursor === size, 'unaccounted object bytes');"
    s=s.replace(marker,marker+'''
  for(const object of record.objects){
    if(object.tag===6&&bytes.readUInt32LE(object.offset)===1834){
      const value=bytes.readUInt32LE(object.offset+28),offset=value-record.base-6;
      check(value%8===6&&pointers.has(value)&&offset>=0&&offset+32<=size,'function immediates extent');
      check(bytes.readUInt32LE(offset)===2042,'function immediates shape');
    }
  }''')
    return s
if __name__=='__main__':
    import sys
    Path(sys.argv[1]).write_text(derive())
