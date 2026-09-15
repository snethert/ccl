"""Exercise real accessor instances, then reject altered dependency witnesses."""
from copy import deepcopy
from pathlib import Path
import json
import os
import subprocess
from accessors import classify
from payloads import literal_regions,require,read,save

HERE=Path(__file__).resolve().parent
EXPECTED={
    'reader-left-a':11,'reader-right-a':29,'reader-left-b':43,
    'writer-left-a':73,'written-left-a':73,'other-slot-preserved':29,
    'other-instance-preserved':43,'writer-right-b':89,'written-right-b':89,
    'generic-left':73,'generic-right':89,'alternate-slot-parameter':29,
    'substituted-callee':-900}


def no_duplicate_keys(pairs):
    result={}
    for k,v in pairs:
        require(k not in result,'DUPLICATE_NATIVE_JSON_KEY');result[k]=v
    return result


def check(path,compiled_templates):
    rows=[json.loads(s,object_pairs_hook=no_duplicate_keys) for s in path.read_text().splitlines()]
    require([r['sequence'] for r in rows]==list(range(1,len(rows)+1))
            and rows[-1]['kind']=='accessor-complete' and rows[-1]['completed'] is True,'NATIVE_COMPLETION')
    cases=[r for r in rows if r['kind']=='accessor-case']
    require(len(cases)==len(EXPECTED) and {r['case']:r['actual'] for r in cases}==EXPECTED
            and all(r['expected']==EXPECTED[r['case']] for r in cases),'NATIVE_ACCESSOR_VALUES')
    fs={r['id']:r for r in rows if r['kind']=='function'};ts={}
    for r in rows:
        if r['kind']!='accessor-template':continue
        kind=r['accessor_kind'];fn=fs[r['function']];code=fn['payload_hex'][:16*fn['code_words']]
        t=compiled_templates[kind]
        require(code==t['code'] and fn['code_words']==t['code_words'],'NATIVE_BUILD_TEMPLATE_BYTES')
        literals,_=literal_regions(fn)
        require(literals[1]['name']==t['callee']['name'],'NATIVE_TEMPLATE_CALLEE')
        ts[kind]=dict(t,function=fn['id'],callee=literals[1])
    require(set(ts)=={'reader','writer'},'NATIVE_TEMPLATE_COVERAGE')
    instances=[r for r in rows if r['kind']=='accessor-instance']
    require(len(instances)==4,'NATIVE_INSTANCE_COVERAGE')
    for r in instances:
        match=classify(fs[r['function']],r['method'],ts)
        require(match is not None and match['kind']==r['accessor_kind'],'NATIVE_INSTANCE_JOIN')
        require(match['generic_dispatch_bound'] is False and match['runtime_cell_values']=='UNRESOLVED',
                'ACCESSOR_SCOPE')
    first=instances[0];original=fs[first['function']];refused=[]
    def reject(name,change):
        f=deepcopy(original);change(f)
        require(classify(f,first['method'],ts) is None,'ACCESSOR_CONTROL_ESCAPED '+name);refused.append(name)
    reject('instruction-byte',lambda f:f.update(payload_hex=f['payload_hex'][:20]+'ff'+f['payload_hex'][22:]))
    reject('required-arity',lambda f:f.update(bits=f['bits']+(1<<8)))
    reject('missing-method-bit',lambda f:f.update(bits=f['bits']^(1<<28)))
    reject('extra-executable-literal',lambda f:f.update(words=f['words']+1))
    reject('closure-instead-of-prototype',lambda f:f.update(prototype=f['id']+100))
    reject('wrong-slot-type',lambda f:f['literals'][0].update(type={'symbol':'CONS','package':'COMMON-LISP'}))
    reject('slot-without-identity',lambda f:f['literals'][0].pop('object'))
    reject('same-name-different-callee',lambda f:f['literals'][1].update(symbol=f['literals'][1]['symbol']+1000))
    reject('wrong-method-owner',lambda f:f['literals'][2].update(object=first['method']+1000))
    reject('wrong-method-class',lambda f:f['literals'][2].update(type={'symbol':'STANDARD-WRITER-METHOD','package':'CCL'}))
    mutations={r['case']:r for r in rows if r['kind']=='accessor-mutation'}
    swap=mutations['alternate-slot'];match=classify(fs[swap['function']],swap['method'],ts)
    require(match is not None and match['slot_id']!=literal_regions(original)[0][0]['object'],
            'ALTERNATE_SLOT_PARAMETER')
    wrong=mutations['substituted-callee']
    require(classify(fs[wrong['function']],wrong['method'],ts) is None,'REAL_CALLEE_SUBSTITUTION')
    return dict(status='PASS',native_cases=len(cases),native_instances=len(instances),
        controls_rejected=refused,real_callee_substitution_rejected=True,alternate_slot_parameter_preserved=True)


def run(source,output,build):
    output.mkdir(parents=True,exist_ok=False)
    argv=[str(source/'dx86cl64'),'--no-init','--batch']
    for path in ('observer.lisp','dependencies.lisp','rich-observation/observer.lisp',
                 'resident-bodies/export.lisp','dispatch-registry/inspect.lisp',
                 'registry-callees/build-observer.lisp','registry-callees/accessor-probes.lisp'):
        argv+=['--load',str(HERE.parent/path)]
    dest=output/'native.jsonl'
    argv+=['--eval','(progn (ccl-accessor-census-probes::run '+json.dumps(str(dest))+') (ccl:quit))']
    save(output/'command.json',dict(argv=argv,cwd=str(source)))
    with (output/'native.log').open('wb') as log:
        p=subprocess.run(argv,cwd=source,env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(source)),
                         stdout=log,stderr=subprocess.STDOUT,timeout=90)
    require(p.returncode==0 and 'ACCESSOR-NATIVE-PASS' in (output/'native.log').read_text(),'NATIVE_ACCESSOR_EXECUTION')
    result=check(dest,read(build/'accessor-template-joins.json.gz')['templates'])
    save(output/'controls.json',result);print(result)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','output','build'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.source.resolve(),a.output.resolve(),a.build.resolve())
