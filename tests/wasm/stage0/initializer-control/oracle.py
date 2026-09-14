"""Literal bootstrap expectations, independent of the loader and WAT generator."""
STATES={
 'complete':'CCCCCCCCC','early':'FNNNNNNNN','middle':'CCCCFNNNN','late':'CCCCCCCCF',
 'diagnostic-early':'FBBCCCCCC','diagnostic-middle':'CCCCFBCCC','diagnostic-late':'CCCCCCCCF',
 'diagnostic-two-failures':'FBBCFBCCC','missing-module':'NNNNNNNNN'}
NAMES=['core','types','startup']
FULL={'C':'COMPLETED','F':'FAILED','N':'NOT_RUN','B':'BLOCKED'}
def require(ok,why):
    if not ok:raise ValueError(why)
def check(o,case,manifest):
    require('unexpected' not in o,'EXECUTION_ERROR')
    require(o['config']==case,'CASE_IDENTITY')
    states=STATES[case['name']];success=case['name']=='complete';r=o['report']
    require(r['status']==('PASS' if success else 'FAIL'),'AGGREGATE')
    require(r['published']==success and o['ready_artifact']==success and len(o['publications'])==int(success),'NO_PARTIAL_PUBLICATION')
    require(r['diagnostic']==case['diagnostic'],'DIAGNOSTIC_MODE')
    executed=[i for i,s in enumerate(states) if s in 'CF']
    want_memory=dict(started=[int(s in 'CF') for s in states],completed=[int(s=='C') for s in states],
       effects=[(i+1)*10 if s in 'CF' else 0 for i,s in enumerate(states)],calls=executed)
    require(o['memory']==want_memory,'PHYSICAL_EFFECTS')
    wanted_steps=[dict(index=i,id=f'{NAMES[i//3]}/init-{i}',module=NAMES[i//3],state=FULL[s],
      result=100+i if s=='C' else None,blocked_by=[i-1] if s=='B' else []) for i,s in enumerate(states)]
    require(r['steps']==wanted_steps,'STEP_RESULTS')
    errors=[dict(phase='initializer',code='INITIALIZER_EXCEPTION',module=NAMES[i//3],index=i,
                 step=f'{NAMES[i//3]}/init-{i}',payload=i) for i,s in enumerate(states) if s=='F']
    if case['omit']:errors=[dict(phase='module',code='REQUIRED_MODULE_MISSING',module='types',index=None,step=None)]
    require(r['first_failure']==(errors[0] if errors else None),'FIRST_FAILURE')
    require(r['errors']==errors,'ALL_FAILURES')
    fetched=NAMES[:2] if case['omit'] else NAMES
    loaded=NAMES[:1] if case['omit'] else NAMES
    require(o['fetches']==fetched and r['modules']==[dict(id=m['id'],sha256=m['sha256']) for m in manifest['modules'] if m['id'] in loaded],'MODULE_PREFLIGHT')
    if success:require(o['publications']==[dict(receipt=dict(scope='STAGE0_HAND_BUILT_BOOTSTRAP',completed=[x['id'] for x in wanted_steps]),snapshot=want_memory)],'READY_SNAPSHOT')
    return dict(name=case['name'],status='PASS' if success else 'REJECTED',executed=executed,completed=states.count('C'),
                failed=states.count('F'),blocked=states.count('B'),first_failure=r['first_failure'])
