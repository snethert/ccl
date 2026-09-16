"""Derive storage obligations from a pre-emitter IR witness, not module metadata.

The compiler uses iterative propagation. This reader uses the lexical creation
forest, propagating each cell directly to every intervening ancestor.
"""
def derive(rows):
 by_name={r['name']:r for r in rows}
 assert len(by_name)==len(rows)
 owner={};function_cells={};needs={r['name']:{(r['unit'],v) for v in r['inherited']} for r in rows}
 for r in rows:
  for v in set(r['required']+r['base']):
   key=(r['unit'],v);assert key not in owner or owner[key]==r['name'];owner[key]=r['name']
  for item in r['function_bindings']:
   assert item['function'] not in function_cells
   function_cells[item['function']]=(r['unit'],item['variable'])
 for r in rows:
  for callee in r['calls']:
   key=function_cells[callee]
   if owner[key]!=r['name']:needs[r['name']].add(key)
 for name,initial in list(needs.items()):
  for key in list(initial):
   at=name;seen=set()
   while at!=owner[key]:
    assert at is not None and at not in seen,(name,key,'not lexical')
    seen.add(at);needs[at].add(key);at=by_name[at]['parent']
 captured=set().union(*needs.values())
 result={}
 for r in rows:
  private=set(r['base']) | (set(r['required']) & set(r['assigned']))
  private |= {v for v in r['required'] if (r['unit'],v) in captured}
  result[r['name']]={'bound_words':len(private),'captures':len(needs[r['name']]),
                   'basis':'pre-emitter CCL IR, lexical owners and independent ancestor propagation'}
 return result
