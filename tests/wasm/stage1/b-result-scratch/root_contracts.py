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
                   'small_scratch':small_scratch(r), 'basis':'pre-emitter CCL IR, lexical owners, independent storage bound and ancestor propagation'}
 return result


# The witness above reports pre-emitter operations, not the compiler's decision.
# Unknown operations conservatively keep the existing dynamic-storage path.
SMALL_OPS = set("NIL T FIXNUM LAMBDA-LIST IMMEDIATE LEXICAL-REFERENCE SPECIAL-REF BOUND-SPECIAL-REF SETQ-LEXICAL SETQ-SPECIAL %FUNCTION CLOSED-FUNCTION SIMPLE-FUNCTION CONS LIST EQ TYPED-FORM %DECLS-BODY CAR CDR %CAR %CDR RPLACA RPLACD %RPLACA %RPLACD VALUES PROGN IF LET LET* MULTIPLE-VALUE-PROG1 PROG1".split())
def small_scratch(row):
 ops=row['storage_ops']
 assert ops and sum(op=='LAMBDA-LIST' for op,n in ops)==1
 assert all(isinstance(op,str) and isinstance(n,int) and n>=0 for op,n in ops)
 return not ({op for op,n in ops}-SMALL_OPS) and max([n for op,n in ops if op=='VALUES']+[0])<=4
