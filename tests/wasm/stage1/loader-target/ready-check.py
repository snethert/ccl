"""Require real startup loads, stream output, independent instances and refusals."""
import hashlib
import json
from pathlib import Path
import sys


def read(path): return json.loads(path.read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def run(a_path, b_path, omitted_path, empty_path, parent_path):
    a,b,omitted,empty=map(read,(a_path,b_path,omitted_path,empty_path))
    parent=read(parent_path)
    for boot,instance,value,result in ((a,'a',111,112),(b,'b',222,223)):
        assert boot['ready'] and boot['status']=='READY' and boot['boot0']
        assert boot['instrumentation']['modules'] >= 1
        if instance == 'a':
            assert boot['instrumentation']['instances'] >= boot['modules']
        else:
            assert boot['instrumentation']['instances'] == 3
        assert not boot['level1CrossLoaded']
        assert boot['errorServiceMode']==1
        assert boot['collectionInhibition']==0 and not boot['collectionPending']
        assert boot['startupLoads']==['/ccl/bin/loader-postimage.w32fsl',f'/ccl/bin/loader-instance-{instance}.w32fsl']
        closed={r['path'] for r in boot['loadEvents'] if r['event']=='close'}
        assert set(boot['startupLoads'])<=closed
        for name in boot['startupLoads']:
            assert any(r['event']=='return' and r['path']==name and r['count']>0 and r['value']=={'symbol':'T'}
                       for r in boot['loadEvents']),('post-image LOAD must return',name)
        stdout=''.join(r['text'] for r in boot['outputEvents'] if r['channel']==1)
        stderr=''.join(r['text'] for r in boot['outputEvents'] if r['channel']==2)
        assert 'LOADER-POSTIMAGE-PASS' in stdout and 'stdout λ😀\n' in stdout
        assert 'LOADER-GENERATION-REFUSAL-PASS' not in stdout
        assert not boot['abandonedSessions'] and not boot['openFiles']
        assert len(boot['archiveStorage'])==1
        assert boot['archiveStorage'][0]['generations']==1
        assert boot['archiveStorage'][0]['openSessions']==0
        assert 'stderr λ😀\n' in stderr
        assert f'LOADER-INSTANCE-{instance.upper()}-PASS (:COLD {value}) {result}' in stdout
        other='B' if instance=='a' else 'A'
        assert f'LOADER-INSTANCE-{other}-PASS' not in stdout
    for key in ('heapDigest','codeDigest','modules','bundleInputs'):
        assert a[key]==b[key],('fresh instances must start from the same image and namespace',key)
    names={r['callable']['function'].get('symbol') for r in a['execution']
           if isinstance(r.get('callable',{}).get('function'),dict)}
    services={'GET-UNIVERSAL-TIME','GET-TIMEZONE','%INTERNAL-RUN-TIME',
              '%OPEN-DIR','%READ-DIR','CLOSE-DIR','%MKDIR','%RMDIR','UNIX-RENAME',
              'BOGUS-THING-P','%ADDRESS-OF'}
    assert services<=names,('required Lisp service adapters were not observed',services-names)
    for refusal in (omitted,empty):
        assert not refusal['ready'] and refusal['status']=='STOPPED'
        assert refusal['heapDigest']==a['heapDigest'] and refusal['codeDigest']==a['codeDigest']
        assert not refusal['level1CrossLoaded']
        assert not any('LOADER-POSTIMAGE-PASS' in r['text'] for r in refusal['outputEvents'])
    assert omitted['omittedBundles']==['/ccl/l1-fasls/l1-utils.w32fsl']
    assert omitted['startupLoads']==empty['startupLoads']==a['startupLoads']
    assert omitted['bundleInputs']==[r for r in a['bundleInputs']
                                      if r['path'] not in omitted['omittedBundles']]
    assert not any(r['event']=='open' and r['path'] in omitted['omittedBundles'] for r in omitted['loadEvents'])
    assert empty['bundleInputs']==[] and empty['completedLoads']==[]
    # The separately compiled witnesses bind the exact pre-existing image.
    manifest=Path(parent['image'])/'boot/artifacts/manifest.json'
    assert digest(manifest)==parent['manifest']
    image=read(manifest)
    assert image['heap']['digest']==a['heapDigest'] and image['codeDigest']==a['codeDigest']
    return dict(status='PASS',inputs={str(p):digest(p) for p in
        (a_path,b_path,omitted_path,empty_path,parent_path)},
        heap=a['heapDigest'],code=a['codeDigest'],level0_modules=a['modules'],
        completed_loads=[a['targetLoadedFiles'],b['targetLoadedFiles']],
        instances=[dict(state=['COLD',111],later_function=112),dict(state=['COLD',222],later_function=223)],
        observed_lisp_services=sorted(services),
        assertions=['real %TOPLEVEL-FUNCTION% handoff', 'target-only level-1 loading',
          'class-mode error service', 'post-image LOAD returns in both fresh Workers',
          'independent mutable state and later installed functions',
          'Unicode stdout/stderr and flushing', 'ordinary READY preserves the reload generation',
          'required bundle omission refuses',
          'no-load path cannot pass'],
        scope='One Lisp Worker per fresh instance. This does not claim multi-Worker scheduling or native image saving.')


if __name__=='__main__':
    result=run(*(Path(p) for p in sys.argv[1:6]))
    Path(sys.argv[6]).write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],result['completed_loads'])
