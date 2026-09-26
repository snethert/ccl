"""Native LFUN-BITS treats optional NIL as a read, not an invalid store."""
import product
from pathlib import Path

c = product.c


def overlay(base):
    path = base / 'metadata-check.mjs'
    source = path.read_text()
    anchor = "['bits writer type',[gf,NIL]]"
    assert source.count(anchor) == 1
    source = source.replace(anchor, "['bits writer type',[gf,T]]")
    anchor = "    ['bits writer ordinary function',[ordinary,0]],"
    assert source.count(anchor) == 1
    before = "  for(const [label,args] of [\n" + anchor
    assert source.count(before) == 1
    positive = '''  assert.deepEqual(gen.invoke('core_generic_set_function_bits',[ordinary,NIL]),bits);
  records.push('ordinary optional NIL reads unchanged bits');
  const sideBits=get(gf+22)+22,savedBits=get(sideBits);
  try {
    put(sideBits,12);
    assert.deepEqual(gen.invoke('core_generic_set_function_bits',[gf,NIL]),[12]);
    assert.equal(get(sideBits),12,'optional NIL leaves funcallable bits unchanged');
    records.push('funcallable optional NIL reads unchanged bits');
  } finally {put(sideBits,savedBits);}
'''
    path.write_text(source.replace(before, positive + before))
    env = c.read(base / 'execution-environment.json')
    env['files']['metadata-check.mjs'] = c.sha(path)
    env['tooling']['loader-def/metadata.py'] = c.sha(Path(__file__))
    c.save(base / 'execution-environment.json', env)
