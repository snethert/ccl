import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'bootstrap-tables'))
from selection import selection

def parse(log):
 tables={};pops={};absent=[];totals=None
 for line in log.splitlines():
  p=line.split('|');kind=p[0]
  if kind=='TOTAL':assert totals is None;totals=list(map(int,p[1:]));assert len(totals)==4
  elif kind=='TABLE':
   _,key,test,weak,count=p;assert key not in tables;tables[key]=dict(test=test.lower(),weak=weak.lower(),count=int(count),owners=[])
  elif kind=='TABLE-OWNER':
   _,key,site,path=p;tables[key]['owners'].append(dict(site=site,path=path))
  elif kind=='POP':
   _,key,tag,count,pending=p;assert key not in pops;pops[key]=dict(type=int(tag),count=int(count),pending=int(pending),owners=[])
  elif kind=='POP-OWNER':
   _,key,site,path=p;pops[key]['owners'].append(dict(site=site,path=path))
  elif kind=='NO-TABLE':_,site,path=p;absent.append(dict(site=site,path=path,status='NO_MATCHED_INSTANCE_IN_CAPTURE'))
 assert totals==[len(tables),sum(r['count'] for r in tables.values()),len(pops),sum(r['count'] for r in pops.values())], 'heap census totals'
 sites={r['id']:r for r in selection()}
 for r in tables.values():
  assert r['owners'],'unattributed table'
  sources={o['site'] for o in r['owners']};assert len(sources)==1,'ambiguous constructor'
  r['site']=sources.pop();assert r['site'] in sites
  assert (r['test'],r['weak'])==(sites[r['site']]['test'],sites[r['site']]['weak']), 'constructor identity'
  assert r['count']>=0
  r['owners'].sort(key=lambda x:x['path'])
  r['capacity']=2**(max(4,sites[r['site']]['size'],r['count']+max(16,(r['count']+3)//4))-1).bit_length()
  assert r['capacity']<=16384,'owner capacity ceiling'
  r['disposition']='EQ_MOVEMENT_EXECUTED' if r['test']=='eq' else 'BLOCKS_BOOTSTRAP_EQUALITY_SERVICE'
 for r in pops.values():
  assert r['owners'],'unattributed population';r['owners'].sort(key=lambda x:x['path'])
  assert r['type'] in [0,1,65536,65537] and r['count']>=0 and r['pending']>=0
  r['disposition']='BLOCKS_BOOTSTRAP_TERMINATION_SERVICE' if r['type']&65536 else 'STRONG_STORAGE_ACCESSOR_JOIN_REQUIRED'
 for a in absent:assert a['site'] in sites
 assert set(sites)=={r['site'] for r in tables.values()}|{a['site'] for a in absent},'constructor inventory coverage'
 tables=sorted(tables.values(),key=lambda x:(x['site'],x['owners'][0]['path']))
 pops=sorted(pops.values(),key=lambda x:x['owners'][0]['path'])
 for i,r in enumerate(tables):r['id']='table-'+str(i)
 for i,r in enumerate(pops):r['id']='population-'+str(i)
 return dict(totals=dict(tables=totals[0],entries=totals[1],populations=totals[2],members=totals[3]),tables=tables,populations=pops,absent=sorted(absent,key=lambda x:x['site']),closure='NOT_ESTABLISHED')

def validate(census,log):
 assert census==parse(log),'census differs from native capture'
 return dict(status='PASS',**census['totals'])

def table_check(source):
 source=source.replace("const liveCount=countBySite.get(site.id)??1;", "assert(countBySite.has(site.id),'missing instance measurement');const liveCount=countBySite.get(site.id);")
 a="const [k,v]=found[0];\n   assert.equal(service.ht_run(table,table-6+bytes,0,k,NIL,scratch,scratch+131072,result),0);assert.deepEqual([get(result),get(result+4),get(result+8)],[v,77838,2],'lookup after movement');"
 b="for(const [k,v] of found){assert.equal(service.ht_run(table,table-6+bytes,0,k,NIL,scratch,scratch+131072,result),0);assert.deepEqual([get(result),get(result+4),get(result+8)],[v,77838,2],'lookup after movement');}"
 assert source.count(a)==1;return source.replace(a,b)
