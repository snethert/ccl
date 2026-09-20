"""Check actual observations against the independent case inventory."""
import collections,json
from pathlib import Path

def read(p):return json.loads(p.read_text())
def check(cases,oracle,native,eager,cold):
 assert eager.get('status')=='PASS' and cold.get('status')=='PASS','execution status'
 assert eager==cold,'cold result equality'
 assert len(oracle)==4553 and len(cases)==18050,'required corpus membership'
 assert len(native)==len(cases),'native population'
 assert [r['id'] for r in cases]==list(range(len(cases))),'case identities'
 assert {r['family'] for r in cases if 'family' in r}=={'add','sub','mul','ash','length','truncate'}
 expected={(pi,r['name']):(['102'] if r['expected']=='division-by-zero' else r['expected']) for pi in range(3) for r in oracle}
 observed={}
 for c,n in zip(cases,native):
  assert c['id']==n['id'] and c['function']==n['function'],'native identities'
  if 'family' in c:
   key=(int(c['function'][1]),c['origin']);assert key not in observed
   observed[key]=n['expected'];assert n['expected']==c['oracle'],'independent numeric value'
 assert observed==expected,'independent oracle coverage'
 want={(high,collect,n['id']):n for high in [False,True] for collect in [False,True] for n in native}
 actual={}
 for r in eager['rows']:
  if 'id' in r:
   key=(r['high'],r['collect'],r['id']);assert key not in actual,'duplicate execution'
   assert key in want and r['function']==want[key]['function'] and r['values']==want[key]['expected'],'generated value'
   actual[key]=r
 assert actual.keys()==want.keys(),'execution matrix omissions'
 summary=[r for r in eager['rows'] if 'cases' in r]
 assert len(summary)==4 and all(r['cases']==len(cases) for r in summary),'actual counts'
 assert all(r['moves']>0 for r in summary if r['collect']),'moving modes'
 return dict(native_cases=len(native),independent_integer_cases=len(expected),generated_comparisons=len(actual),collections=sum(r['moves'] for r in summary),modules=len(eager['admission']),native_policies=[[0,3],[3,0],[3,3]],cold_identical=True)

def qualify(out):
 d=out/'generated'
 return check(read(d/'cases.json'),read(out/'integer-oracle.json'),read(d/'native.json'),read(d/'eager.json'),read(d/'cold.json'))
