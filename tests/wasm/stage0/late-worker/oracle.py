"""Literal memory and instance-state oracle, independent of Wasm/loader effects."""
import gzip
import hashlib
import json
import struct

STEPS=['instance-0','process-0','setup-0','instance-1','setup-1','shared-1','touch-0','touch-1',
       'install-0','publish','sync-0','sync-1','shared-2','instance-2','setup-2','retry-process-2','touch-2',
       'shared-3','instance-3','setup-3','observe-0','observe-1','observe-2','observe-3']
REFUSALS={
 'active-data':('instance-2','ACTIVE_DATA'), 'start-bss':('instance-2','START_FUNCTION'),
 'overlap':('instance-2','REGION_OVERLAP'),'misaligned':('instance-2','REGION_ALIGNMENT'),
 'undersized':('instance-2','PRIVATE_SIZE'),'duplicate-owner':('instance-2','OWNER_ALREADY_ASSIGNED'),
 'wrong-digest':('instance-2','BINARY_DIGEST'),'wrong-private-base':('setup-2','PRIVATE_RANGE'),
 'lazy-data':('install-0','LAZY_DATA'),'lazy-start':('install-0','LAZY_START'),
 'lazy-reserved':('install-0','RESERVED_SLOT')}
def require(v,r):
 if not v:raise ValueError(r)
def metadata():
 g=dict(process_word=32,generation_word=48,data_base=64,data_size=16,bss_base=128,bss_size=64,code_record=224,
        worker_base=4096,worker_stride=512,worker_count=4,tls_offset=0,tls_size=16,tcr_offset=32,tcr_size=64,
        cstack_offset=128,cstack_size=128,vstack_offset=288,vstack_size=128,heap_base=8192,heap_size=1024,staging_base=12288,staging_size=512)
 ranges=[('process',32,36),('generation',48,52),('data',64,80),('bss',128,192),('code',224,256)]
 ranges += [('worker-'+str(i),4096+512*i,4608+512*i) for i in range(4)]+[('heap',8192,9216),('staging',12288,12800)]
 return dict(globals=g,regions=[dict(name=n,start=s,end=e) for n,s,e in ranges],
             owned=[dict(name=n,start=s,end=e) for n,s,e in [('tls',0,16),('tcr',32,96),('cstack',128,256),('vstack',288,416)]],reserved=[0,1])
def check(out,bundle,case):
 observed=json.loads((out/'observed.json').read_text())
 require(observed['version']==1 and observed['case']==case,'PROFILE')
 mem=bytearray((i*17+31)%256 for i in range(65536))
 def word(p,n):struct.pack_into('<I',mem,p,n)
 def fill(p,n,b):mem[p:p+n]=bytes([b])*n
 word(32,0);word(48,0)
 workers={};heap=mem[8192];expected_failure=REFUSALS.get(case)
 expected_steps=STEPS if expected_failure is None else STEPS[:STEPS.index(expected_failure[0])+1]
 require([r['name'] for r in observed['rows']]==expected_steps,'STEP_SEQUENCE')
 require(observed['failure']==(expected_failure[1] if expected_failure else None),'FAILURE_STATUS')
 snapshots=gzip.decompress((out/'memory.bin.gz').read_bytes())
 require(len(snapshots)==65536*len(expected_steps),'SNAPSHOT_BOUND')
 for index,row in enumerate(observed['rows']):
  require(row['snapshot']==index,'SNAPSHOT_INDEX')
  name=row['name'];action,*suffix=name.split('-');id=int(suffix[-1]) if suffix else None
  error=expected_failure and name==expected_failure[0];value=None;state=None
  if error:
   if action=='instance':state=dict(ready=False,instantiated=False)
   else:state=workers[id]
   expected=dict(status='ERROR',error=expected_failure[1],state=state)
  else:
   if action=='instance':
    workers[id]=dict(ready=False,instantiated=True,owner=-1,tls=0,tcr=0,csp=0,vsp=0,generation=0,slots=[None,24,None,None,None,None,None,None])
   elif action=='process':
    mem[64:80]=bytes.fromhex('0123456789abcdef1032547698badcfe');fill(128,64,0);word(32,2);value=1
   elif action=='setup':
    base=4096+id*512;fill(base,16,0);fill(base+32,64,0);fill(base+128,128,160+id);fill(base+288,128,176+id)
    word(base,1000+id)
    for off,val in [(32,id+1),(36,base),(40,base+256),(44,base+416)]:word(base+off,val)
    workers[id].update(ready=True,owner=id,tls=base,tcr=base+32,csp=base+256,vsp=base+416)
    if id>=2:workers[id]['generation']=1;workers[id]['slots'][2]=(heap*0x01010101+7)%2**32
    value=0
   elif action=='shared':
    fill(64,16,208+id);fill(128,64,177+id);fill(8192,1024,226+id);fill(12288,512,243+id);heap=226+id
    id=0
   elif action=='touch':
    base=4096+512*id
    for offset in (12,92,252,412):word(base+offset,0x11220000+id)
   elif action=='install':workers[id]['slots'][2]=(heap*0x01010101+7)%2**32
   elif action=='publish':
    mem[224:256]=hashlib.sha256((bundle/'lazy.wasm').read_bytes()).digest();word(48,1);value=1
   elif action=='sync':workers[id]['generation']=1;workers[id]['slots'][2]=(heap*0x01010101+7)%2**32
   elif action=='retry':id=2;value=0
   elif action!='observe':raise ValueError('UNKNOWN_STEP')
   # Installed functions read live heap bytes; table identity is witnessed by
   # the distinct reserved and lazy return values, not host-supplied slot labels.
   for w in workers.values():
    if w['slots'][2] is not None:w['slots'][2]=(heap*0x01010101+7)%2**32
   state=None if name=='publish' else workers[id]
   expected=dict(status='OK',value=value,state=state)
   if action=='instance':expected['metadata']=metadata()
  require(snapshots[index*65536:(index+1)*65536]==mem,'MEMORY '+name)
  require(row['result']==expected,'STATE '+name)
 return dict(case=case,status='REFUSED_AS_REQUIRED' if expected_failure else 'PASS',steps=len(expected_steps),
             refusal=expected_failure[1] if expected_failure else None,memory_bytes_checked_per_step=65536)
