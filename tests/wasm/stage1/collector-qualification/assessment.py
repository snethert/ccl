"""Qualify named populations independently of the publication summary."""
import copy,json,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent

def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def need(ok,why):
 if not ok:raise ValueError(why)
OWNER_NAMES='all-root-families second-collection manifest-is-copied allocation-retry-after-reclaim live-growth-and-view-refresh actual-memory-maximum unsigned-high-heap outside-boundary nested-boundary async-boundary zero-allocation unaligned-allocation past-memory-maximum recover-after-refusal EGC-request multiple-workers missing-group duplicate-group unknown-group duplicate-slot scratch-slot unaligned-slot canonical-stack-overlap missing-canonical-image scratch-stack-overlap heaps-overlap C-stack-mismatch truncated-image oversized-TCR small-root-list wrong-digest allocation-limit stack-base result-into-C-stack binding-into-C-stack T-header unknown-image-kind interior-heap-root heap-growth-exhaustion-preserves-live engine-growth-refusal'.split()
MUTANTS='active-results bit-rounding byte-width raw-payload-as-roots omit-module-constants omit-callbacks-generated omit-registry omit-host omit-pinned-bits omit-callbacks omit-next-method omit-image-pool raw-metadata-root unowned-canonical stale-host-view grow-without-reclaim unpublished-boundary'.split()

def assess(d):
 g=d['generated'];need(g['status']=='PASS' and d['lazy']==g,'cold execution equality')
 cases={r['id'] for r in d['cases']};need(len(cases)==len(d['cases']) and len(cases)==43,'generated case membership')
 configs={(8,False,False),(16,False,False),(32,False,False),(128,False,False),(512,False,False),(512,True,False),(32768,False,True)}
 rows=g['rows'];normal=[r for r in rows if 'capacity' in r]
 need(len(normal)==len(cases)*len(configs) and {(r['id'],r['capacity'],r['empty'],r['high']) for r in normal}=={(c,*v) for c in cases for v in configs},'generated heap configurations')
 need(g['native_comparisons']==len(normal) and g['collections']==sum(r['moves'] for r in rows) and g['growths']==sum(r.get('grown',0) for r in rows) and g['collections']>0 and g['growths']>0,'actual moving retry')
 need([r for r in rows if 'capacity' not in r]==[dict(id='failure_live',refusal=6,moves=2)],'failure after movement')
 p=d['polls'];expect={r['id']:r['expected'] for r in d['pollcases']};seen=collections.Counter()
 for r in p['conditions']:
  need(r['id'] in expect and {k:r[k] for k in ('status','values','nodes','specials')}==expect[r['id']],'poll native semantics');seen[r['id']]+=1
 need(set(seen)==set(expect) and set(seen.values())=={4} and len(expect)==30 and len(p['moved_vectors'])==62,'poll populations')
 need(d['core']['status']=='PASS' and len(d['core']['tests'])==95 and {'interior','tag-mismatch','root-cycle','unknown-header','capacity','workspace','inline-descriptor-262144','arena-descriptor-262144','stack-callable-262144'}.issubset({r['name'] for r in d['core']['tests']}),'core refusal oracle')
 owner=d['owner'];need(owner['status']=='PASS' and owner['checks']==len(OWNER_NAMES) and collections.Counter(r['name'] for r in owner['rows'])==collections.Counter(OWNER_NAMES) and all(r['status'] in ('PASS','REJECTED') for r in owner['rows']),'owner admission and memory population')
 roots=d['roots'];need(roots['status']=='PASS' and [r['high'] for r in roots['rows']]==[False,True],'low and high generated roots')
 for r in roots['rows']:
  need(r['families']==['module-constants','callbacks','registry','host','next_method_context','multiple-values'] and r['callbackInvoked'] and r['rawUnchanged'] and r['interiorRefused'],'precise generated root families')
  need(r['first']['reclaimed']==16 and r['repeated']['reclaimed']==24 and r['resultMove']['objects']==11,'independent live and dead accounting')
 lit=d['literals'];need(lit['status']=='PASS' and [r['label'] for r in lit['rows']]==['low','high','pinned'],'moving and pinned literal placements')
 for r in lit['rows']:need(r['status']=='PASS' and r['coldBeforeInstall'] and r['comparisons']==151 and r['collections']==79 and r['literalObjects']==155,'literal native population')
 need({r['name'] for r in d['controls']['mutants']}==set(MUTANTS) and len(d['controls']['mutants'])==len(MUTANTS) and all(r['status']=='REJECTED' and r['returncode']!=0 for r in d['controls']['mutants']),'executed runtime mutants')
 return dict(status='PASS',native_retry_comparisons=len(normal),explicit_poll_comparisons=len(p['conditions']),literal_comparisons=sum(r['comparisons'] for r in lit['rows']),runtime_mutants=len(MUTANTS),owner_checks=len(OWNER_NAMES),core_checks=95,cold_observations=len(rows),root_placements=2)

def run(execution,out):
 paths={'generated':'generated.json','lazy':'lazy.json','cases':'generated/cases.json','polls':'polls/execution.json','pollcases':'polls/compiled/cases.json','core':'core.json','owner':'owner.json','roots':'roots.json','literals':'literals.json','controls':'controls/controls.json'}
 d={k:read(execution/v) for k,v in paths.items()};result=assess(d);controls=[]
 mutations=[('missing-generated-case',lambda x:x['cases'].pop()),('cold-result',lambda x:x['lazy'].update(status='FAIL')),('missing-heap',lambda x:x['generated']['rows'].pop(0)),('poll-value',lambda x:x['polls']['conditions'][0]['values'].append(42)),('omit-owner-case',lambda x:x['owner']['rows'].pop()),('missing-callback',lambda x:x['roots']['rows'][0]['families'].remove('callbacks')),('raw-word-root',lambda x:x['roots']['rows'][0].update(rawUnchanged=False)),('invented-reclaim',lambda x:x['roots']['rows'][0]['first'].update(reclaimed=0)),('omit-pinned',lambda x:x['literals']['rows'].pop()),('omit-cold-pool',lambda x:x['literals']['rows'][0].update(coldBeforeInstall=False)),('missing-mutant',lambda x:x['controls']['mutants'].pop())]
 for name,edit in mutations:
  bad=copy.deepcopy(d);edit(bad)
  try:assess(bad)
  except ValueError as e:controls.append(dict(name=name,status='REJECTED',diagnostic=str(e)))
  else:raise ValueError(name+' escaped')
 out.mkdir();save(out/'assessment.json',result);save(out/'controls.json',controls);return result
