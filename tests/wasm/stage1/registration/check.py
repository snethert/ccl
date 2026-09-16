"""Independent checks over retained native results and bounded decoded FASLs."""
import copy,hashlib,json,sys,tarfile
from pathlib import Path
from unit import ROOT,save
from fasl import compare_compiler,compare_systems,require,CompilerFasl

def read(p):return json.loads(p.read_text())
def assess(data):
    require(data['loaded-before-rebuild'],'LOADED_BEFORE_REBUILD')
    r=data['run'];require(r['status']=='PASS' and r['source_restored'] and r['restored_fasls']==164,'RUN_OR_RESTORATION')
    a,b,c=(data[k] for k in ('baseline-fasls','registered-fasls','restored-fasls'))
    require(len(a)==164 and a.keys()==b.keys() and a==c,'FASL_CORPUS')
    require({n for n in a if a[n]!=b[n]}=={'bin/systems.dx64fsl','bin/compile-ccl.dx64fsl'},'FASL_CHANGED_SET')
    before,after=(data[k] for k in ('baseline-snapshot','registered-snapshot'))
    for key in ('native','architectures','targets'):require(before[key]==after[key],'EXISTING_TARGET_'+key)
    require(len(before['architectures'])==5 and len(before['targets'])==17,'TARGET_POPULATION')
    ops=before['native']['operators'];require(len(ops)==279 and sum(x['name'] is None for x in ops)==12,'OPERATOR_POPULATION')
    added={'CCL::WASM32-ARCH','CCL::WASM32-BACKEND','CCL::XWASM32FASLOAD'}
    require([m for m in after['modules'] if m['name'] not in added]==before['modules'],'EXISTING_SYSTEMS')
    require(len(after['modules'])==len(before['modules'])+3 and {m['name'] for m in after['modules']}-{m['name'] for m in before['modules']}==added,'ADDED_SYSTEMS')
    for phase in ('baseline','registered'):
        t=data[phase+'-tests'];require(t==r[phase+'_tests'],'TEST_RECORD_JOIN')
        require(t['passed']==21843 and t['upstream_disabled']==75 and t['success'] and not any(t[k] for k in ('failed','missing','unexpected')),'NATIVE_TESTS')
    require(data['execution']['status']=='PASS' and len(data['execution']['cases'])==24,'GENERATED_EXECUTION')
    require(data['target-checks']=={'refusals':10,'target_state_restored':True,'module_registration':True},'TARGET_CHECKS')
    return {'native_tests_per_build':21843,'unchanged_fasls':162,'restored_fasls':164,'operator_slots':279,'reserved_slots':12,'architecture_module_lists':5,'target_module_profiles':17,'generated_calls':24,'unsupported_refusals':10}

def load(root):
    d={n:read(root/(n+'.json')) for n in ('run','baseline-fasls','registered-fasls','restored-fasls','baseline-snapshot','registered-snapshot','execution','target-checks')}
    for phase in ('baseline','registered'):d[phase+'-tests']=read(root/phase.join(('', '-tests/test-summary.json')))
    d['loaded-before-rebuild']='WASM32-LOADED-BEFORE-REBUILD' in (root/'registered-build.log').read_text()
    return d

def verify(root,inputs):
    data=load(root);summary=assess(data)
    with tarfile.open(root/'baseline-fasls.tar.gz') as t:
        require({m.name for m in t.getmembers()}==set(data['baseline-fasls']),'FASL_ARCHIVE_MEMBERS')
        baseline={m.name:t.extractfile(m).read() for m in t.getmembers()}
    for n,b in baseline.items():require(hashlib.sha256(b).hexdigest()==data['baseline-fasls'][n],'FASL_ARCHIVE_BYTES')
    with tarfile.open(inputs/'source.tar') as t:
        sources={n:t.extractfile('lib/'+n+'.lisp').read().decode() for n in ('compile-ccl','systems')}
    comparisons={}
    for name,fn in [('compile-ccl',compare_compiler),('systems',compare_systems)]:
        after=(root/('registered-'+name+'.dx64fsl')).read_bytes()
        require(hashlib.sha256(after).hexdigest()==data['registered-fasls']['bin/'+name+'.dx64fsl'],'REGISTERED_FASL_BYTES')
        result=fn(baseline['bin/'+name+'.dx64fsl'],after,sources[name],(root/('proposal/files/lib/'+name+'.lisp')).read_text())
        require(result==read(root/(name+'-comparison.json')),'COMPONENT_REPLAY')
        comparisons[name]=result
    controls=[]
    def reject(name,thunk):
        try:thunk()
        except (ValueError,KeyError,IndexError) as e:controls.append({'name':name,'status':'REJECTED','reason':str(e)})
        else:raise ValueError('CONTROL_ESCAPED '+name)
    mutations={
      'backend-not-loaded':lambda d:d.__setitem__('loaded-before-rebuild',False),
      'missing-fasl':lambda d:d['registered-fasls'].pop(next(iter(d['registered-fasls']))),
      'unexplained-fasl':lambda d:d['registered-fasls'].__setitem__('bin/nx.dx64fsl','0'*64),
      'failed-restoration':lambda d:d['run'].__setitem__('source_restored',False),
      'reserved-slot':lambda d:next(o for o in d['registered-snapshot']['native']['operators'] if o['name'] is None).__setitem__('name','INVENTED'),
      'operator-flag':lambda d:d['registered-snapshot']['native']['operators'][0].__setitem__('flags',-1),
      'target-list':lambda d:d['registered-snapshot']['architectures'][0]['compiler'].append('INVENTED'),
      'target-env':lambda d:d['registered-snapshot']['targets'][0]['env'].pop(),
      'native-failure':lambda d:d['registered-tests'].__setitem__('failed',1),
      'missing-generated-case':lambda d:d['execution']['cases'].pop(),
      'missing-refusal':lambda d:d['target-checks'].__setitem__('refusals',4)}
    for name,mutate in mutations.items():
        d=copy.deepcopy(data);mutate(d);reject(name,lambda d=d:assess(d))
    for name in ('systems','compile-ccl'):
        raw=(root/('registered-'+name+'.dx64fsl')).read_bytes();decoder=CompilerFasl(raw);decoder.decode()
        # Corrupt the first compiled package thunk, outside both permitted functions.
        op=next(o for o in decoder.ops if o['opcode']==3);cursor=CompilerFasl(raw);cursor.pos=op['offset']+1;cursor.count();cursor.count()
        changed=bytearray(raw);changed[cursor.pos+10]^=1
        fn=compare_systems if name=='systems' else compare_compiler
        reject(name+'-code-byte',lambda fn=fn,changed=changed,name=name:fn(baseline['bin/'+name+'.dx64fsl'],bytes(changed),sources[name],(root/('proposal/files/lib/'+name+'.lisp')).read_text()))
        for label,blob in [('truncated',raw[:-1]),('extra-byte',raw+b'\0')]:reject(name+'-'+label,lambda blob=blob:CompilerFasl(blob).decode())
    return {'summary':summary,'controls':controls}
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--write',action='store_true');a=p.parse_args()
    result=verify(a.output,a.inputs)
    if a.write:save(a.output/'verification.json',result)
    else:require(result==read(a.output/'verification.json'),'VERIFIER_RECORD')
    print('S1-REGISTRATION-VERIFIED',json.dumps(result['summary']),len(result['controls']),'controls')
