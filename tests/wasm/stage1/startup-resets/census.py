#!/usr/bin/env python3
"""Query candidates in their own namespace; do not conflate snapshot IDs."""
import argparse,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'tests/wasm/native-census/query'))
from capture import query
from native import save

def run(e,out,cache):
 out.mkdir(parents=True,exist_ok=False)
 selection=json.loads((HERE/'selection.json').read_text());capture=e/'2026-09-15-correlated-query-base-r1/packet.json'
 assert hashlib.sha256(capture.read_bytes()).hexdigest()=='c1a38143e34a23c1a517b8845e430cb6721bd5f57dfa92bb2981e8eb2b733a7b'
 rows=[]
 for row in selection['callbacks']:
  if row['disposition']!='SELECTED_LITERAL_RESET':continue
  q=dict(kind='find-function',name=row['name']);answer=query(capture,cache,q)
  assert answer['status']=='OBSERVED' and answer['exhaustive'] is False
  candidates=[]
  for record in answer['records']:
   f=record['function'];assert f['name']==row['name'];assert record['source'].endswith('/'+row['source'])
   assert f['calls']==[] and f['inner_functions']==[],'literal reset contains a call'
   candidates.append(dict(function=f['function_id'],event=record['event'],source_position=record['source_position']))
  assert candidates
  save(out/(row['module']+'.json'),answer)
  rows.append(dict(name=row['name'],snapshot_function=row['function'],snapshot_namespace='NATIVE-STARTUP-SEEDS-R2',compiler_candidates=candidates,compiler_namespace=answer['namespace'],relation='name/source candidates, not identity equality',reported_call_count=0))
 save(out/'summary.json',dict(status='PASS',rows=rows,exhaustive=False,scope='No computed call in the recorded reset bodies. Callback dispatch and future registration are not bounded by these observations.'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve(),a.cache.resolve())
