"""Conservative static closure; this is not an execution or image-install claim."""
import collections,json,re,sys
from pathlib import Path
p=Path(sys.argv[1]);x=json.loads((p/'throughput.json').read_text())
# Preserve full error text, normalizing only printed object addresses.
for row in x['functions']:
 if row['message']:
  row['message']=re.sub(r'#x[0-9A-Fa-f]{10,16}(?=>)', '#xOBJECT',row['message'])
(p/'throughput.json').write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
by=collections.defaultdict(list)
for r in x['functions']:by[(r['package'],r['name'])].append(r)
closed={k for k,v in by.items() if len(v)==1 and v[0]['proposal']=='admitted' and not v[0]['dynamic_call'] and not v[0]['file_macro_calls']}
while True:
 next_set={k for k in closed if all(tuple(c) in closed for c in by[k][0]['callees'])}
 if next_set==closed:break
 closed=next_set
r=dict(status='PASS',admitted=sum(r['proposal']=='admitted' for r in x['functions']),
 static_dependency_closed=len(closed),functions=sorted(closed),
 scope='Emitted named dependencies only; no assumed external primitives, duplicate definitions and dynamic calls excluded. Macros defined only by loading source files remain owed. This is neither assembly nor execution nor production install qualification.',
 file_macro_dependencies=sum(bool(r['file_macro_calls']) for r in x['functions']),
 host_error_messages=sum(r['message'] is not None for r in x['functions']))
(p/'frontier.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
print({k:v for k,v in r.items() if k not in ('functions','scope')})
