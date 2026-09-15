"""Exercise field-value flow against native CCL, including mutation and errors."""
from pathlib import Path
import argparse,os,subprocess,traceback
from field_inputs import HERE,read,save,require,convert,Resolver,Unbounded
from scan import STORES


def check(raw):
    require(raw['restored'] is True,'FIELD_NATIVE_RESTORED')
    operators={r['id']:r['name'] for r in raw['snapshot']['operators']}
    expected={'fixed':{'symbol'},'parameter':{'input'},'keyword':{'input'},'copy':{'field'},
              'returned':{'return'},'mixed':{'symbol','input'},'assigned':None,'error-result':{'symbol','return'}}
    results=[];seen=set()
    # These probes do not use CONSTANTLY; no constructor rule is enabled.
    constructor=dict(constructor={'id':-1},providers={})
    for c in raw['captures']:
        require(c['case'] in expected and c['case'] not in seen,'FIELD_PROBE_POPULATION');seen.add(c['case'])
        resolver=Resolver(convert(c,operators),constructor,c['ir']);g=resolver.graph;stores=[]
        for owner in resolver.family:
            for n in g.body(owner):
                if n['operator'] in STORES:
                    args=g.items(n['operands']);require(len(args)==3,'FIELD_PROBE_STORE')
                    stores.append((owner,n,args[-1]))
        require(len(stores)==1,'FIELD_PROBE_ONE_STORE');owner,n,value=stores[0]
        try:targets,trace=resolver.resolve(value,owner,n['id'])
        except Unbounded as e:
            require(expected[c['case']] is None and str(e)=='assigned-variable','FIELD_PROBE_REFUSAL')
            results.append(dict(case=c['case'],status='REFUSED',reason=str(e)));continue
        kinds={t[0] for t in targets};require(kinds==expected[c['case']],'FIELD_PROBE_DEPENDENCIES '+c['case'])
        if c['case']=='keyword':
            spec=resolver.inputs[next(t[1] for t in targets if t[0]=='input')]
            require(spec['kind']=='keyword' and spec['keyword']['package']=='KEYWORD' and
                    spec['keyword']['name']=='FN','FIELD_PROBE_KEYWORD')
        results.append(dict(case=c['case'],status='PASS',kinds=sorted(kinds)))
    require(seen==expected.keys(),'FIELD_PROBE_COVERAGE')
    require([r['case'] for r in raw['checks']]==list(expected),'FIELD_PROBE_EXECUTIONS')
    return results


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    argv=[str(a.source/'dx86cl64'),'--image-name',str(a.image),'--no-init','--batch']
    for n in ('observer.lisp','dependencies.lisp','rich-observation/observer.lisp','resident-bodies/export.lisp',
              'finite-callees/probes.lisp','registry-callees/field-probes.lisp'):
        argv+=['--load',str(HERE.parent/n)]
    argv+=['--eval','(progn (census-finite-probes::field-run) (ccl:quit))']
    save(a.output/'command.json',dict(argv=argv,cwd=str(a.source)))
    with (a.output/'native.log').open('wb') as log:
        p=subprocess.run(argv,cwd=a.source,env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(a.source),
            FINITE_OUTPUT=str(a.output/'native.json')),stdout=log,stderr=subprocess.STDOUT,timeout=90)
    require(p.returncode==0,'FIELD_NATIVE_EXIT');results=check(read(a.output/'native.json'))
    save(a.output/'checks.json',results);print(dict(status='PASS',native_cases=len(results),assigned_refused=True),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('source','image','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():
            (a.output/'failure.txt').write_text(traceback.format_exc())
            for n in ('field_native.py','field_inputs.py','field-probes.lisp'):
                (a.output/n).write_bytes((HERE/n).read_bytes())
        raise
