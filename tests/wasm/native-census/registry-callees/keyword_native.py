"""Check keyword selection against native calls, not an expected IR encoding."""
import argparse,os,subprocess,traceback
from pathlib import Path
from keyword_inputs import bind,arguments,read,save,require,convert,ROOT
from finite import Graph
HERE=Path(__file__).resolve().parent


def check(raw):
    require(raw['restored'] is True,'KEYWORD_NATIVE_RESTORED')
    ops={r['id']:r['name'] for r in raw['snapshot']['operators']};results=[];seen=set()
    expected={'default':'1+','supplied':'1-','first-minus':'1-','first-plus':'1+',
              'other-key':'1-','stack-key':'1-','dynamic-key':None,'spread':None}
    for c in raw['captures']:
        name=c['case'];require(name in expected and name not in seen,'KEYWORD_PROBE_POPULATION');seen.add(name)
        cap=convert(c,ops);g=Graph(cap['flow']);calls=[]
        for n in g.body(cap['function']['function_id']):
            if n['operator']=='CCL::CALL':calls.append(n)
        require(len(calls)==1,'KEYWORD_PROBE_CALL');_,args,spread=arguments(g,calls[0]['id'])
        if name=='spread':
            require(spread is not None,'KEYWORD_SPREAD_VISIBLE');results.append(dict(case=name,status='SPREAD_OPEN'));continue
        require(spread is None,'KEYWORD_PROBE_UNEXPECTED_SPREAD')
        keys=[n for n in c['ir']['objects'] if n['kind']=='symbol' and n['package']=='KEYWORD' and n['name']=='FN']
        if name=='default':require(not keys,'KEYWORD_DEFAULT_ABSENT');key=-1
        else:require(len(keys)==1 or name=='dynamic-key','KEYWORD_PROBE_FN');key=keys[0]['id'] if keys else -1
        try:bound=bind(g,args,1,{key})
        except ValueError as e:
            require(name=='dynamic-key' and str(e)=='KEYWORD_DYNAMIC_KEY','KEYWORD_PROBE_REFUSAL')
            results.append(dict(case=name,status='DYNAMIC_KEY_OPEN'));continue
        if key in bound:
            val=g.node(bound[key]);require(val['operator']=='CCL::IMMEDIATE','KEYWORD_LITERAL_VALUE')
            literal=g.items(val['operands']);require(literal==[next(x for x in literal if x.get('symbol')=='COMMON-LISP::'+expected[name])],
                                                   'KEYWORD_SELECTED_VALUE')
        else:require(name=='default','KEYWORD_MISSING_SUPPLIED_VALUE')
        results.append(dict(case=name,status='PASS',selected=expected[name]))
    require(seen==expected.keys(),'KEYWORD_PROBE_COVERAGE')
    require([x['case'] for x in raw['checks']]==list(expected),'KEYWORD_NATIVE_CASES')
    return results


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    argv=[str(a.source/'dx86cl64'),'--image-name',str(a.image),'--no-init','--batch']
    for n in ('observer.lisp','dependencies.lisp','rich-observation/observer.lisp','resident-bodies/export.lisp',
              'finite-callees/probes.lisp','registry-callees/keyword-probes.lisp'):
        argv+=['--load',str(HERE.parent/n)]
    argv+=['--eval','(progn (census-finite-probes::keyword-run) (ccl:quit))']
    save(a.output/'command.json',dict(argv=argv,cwd=str(a.source)))
    with (a.output/'native.log').open('wb') as log:
        p=subprocess.run(argv,cwd=a.source,env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(a.source),
            FINITE_OUTPUT=str(a.output/'native.json')),stdout=log,stderr=subprocess.STDOUT,timeout=90)
    require(p.returncode==0,'KEYWORD_NATIVE_EXIT');checks=check(read(a.output/'native.json'));save(a.output/'checks.json',checks)
    print(dict(status='PASS',native_cases=len(checks),dynamic_keys_and_spread_preserved=True),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('source','image','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():
            (a.output/'failure.txt').write_text(traceback.format_exc())
            for n in ('keyword_native.py','keyword_inputs.py','keyword-probes.lisp'):(a.output/n).write_bytes((HERE/n).read_bytes())
        raise
