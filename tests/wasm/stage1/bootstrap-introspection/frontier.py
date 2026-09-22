"""Separate missing recipes from missing dependencies in the requested work."""
from pathlib import Path
import collections,json,sys

def report(environment,numeric):
    rows=json.loads((environment/'results.json').read_text())
    native=json.loads((numeric/'compiled/native.json').read_text())
    executed={r['definition'] for r in native}
    whole=json.loads((numeric/'compiled/whole-file.json').read_text())
    selected={r['name']:r['file'] for r in whole if r['name'] and (numeric/'compiled'/(r['module']+'.wasm')).exists()}
    def filekey(path):return path.removesuffix('.newest')
    def ran(name,path):return name in executed and filekey(selected.get(name,''))==filekey(path)
    closed={r['name']:r for r in json.loads((numeric/'compiled/closed.json').read_text())}
    all_records={r['name']:r for f in rows for r in f['records'] if r['definition'] is not None}
    def blockers(name,seen=None):
        seen=set() if seen is None else seen
        if name in closed or name in seen:return set()
        seen.add(name)
        r=all_records.get(name)
        if not r or r['outcome']!='ADMITTED':return {name}
        return set().union(*(blockers(c,seen) for c in r['dependencies']))
    groups={}
    for group,stems in [('numeric',{'l0-numbers','l0-float','l0-bignum32','l1-numbers'}),('clos',{'l1-clos-boot'})]:
        result=[]
        for f in rows:
            if f['file'].replace('.newest','').split(';')[-1].removesuffix('.lisp') not in stems:continue
            for d in f['definitions']:
                n=d['name'];admitted=d['outcome']=='ADMITTED'
                result.append(dict(name=n,file=f['file'],admitted=admitted,executed=ran(n,f['file']),
                    callee_closed=n in closed,missing=sorted(blockers(n)) if admitted and n not in closed else [],
                    disposition=('executed' if ran(n,f['file']) else 'needs recipe' if n in closed else 'needs dependencies' if admitted else d['outcome'])))
        groups[group]=dict(rows=result,counts=dict(collections.Counter(r['disposition'] for r in result)),
            missing=dict(collections.Counter(n for r in result for n in r['missing']).most_common()))
    refusals=[dict(file=f['file'],name=r['name'],kind=r['outcome'],message=r['message']) for f in rows for r in f['records'] if r['definition'] is not None and r['outcome']!='ADMITTED']
    result=dict(groups=groups,refusals=refusals,scope='Names resolve conservatively across whole-file records; actual execution is taken only from native comparison rows. Callee closure is the executor result, not this diagnostic traversal. Cycles are not proof of termination.')
    (numeric/'requested-frontier.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result
if __name__=='__main__':report(*(Path(x).resolve() for x in sys.argv[1:]))
