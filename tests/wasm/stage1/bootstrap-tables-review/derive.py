from pathlib import Path
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent/'bootstrap-tables';ROOT=HERE.parents[3]
def policy():
 s=(PARENT/'policy.mjs').read_text();a='export function createStrongEQ({site,policy,memory,service,base,end,capacity}){';assert s.count(a)==1
 s=s.replace(a,'''export function plannedCapacity(site,liveCount){
 if(!Number.isSafeInteger(liveCount)||liveCount<0)throw Error('measured population required');
 const need=Math.max(4,site.size,liveCount+Math.max(16,Math.ceil(liveCount/4)));
 if(need>16384)throw Error('bootstrap table capacity exceeds 16384');
 return 2**Math.ceil(Math.log2(need));
}
export function createStrongEQ({site,policy,memory,service,base,end,capacity,liveCount}){''')
 a="if(plan.test!=='eq')throw Error('equality service not installed: '+plan.test);";s=s.replace(a,a+"\n const required=plannedCapacity(site,liveCount);")
 a="!Number.isInteger(capacity)||capacity<4||capacity>16384||\n    (capacity&(capacity-1))||capacity<plan.size"
 assert s.count(a)==1;s=s.replace(a,"capacity!==required")
 return s

def check():
 s=(PARENT/'check.mjs').read_text().replace('createStrongEQ,strongPlan,STRONG_POLICY','createStrongEQ,strongPlan,plannedCapacity,STRONG_POLICY')
 s=s.replace("const hash=", "const measured=JSON.parse(fs.readFileSync(dir+'/measured.json'));\nconst countBySite=new Map(measured.map(x=>[x.site,x.count]));\nconst hash=",1)
 s=s.replace('(base+32768)', '(base+65536)').replace('size=32768','size=65536')
 s=s.replace('const capacity=2**Math.ceil(Math.log2(Math.max(4,site.size))),bytes=64+8*capacity;', 'const liveCount=countBySite.get(site.id)??1;\n  const capacity=plannedCapacity(site,liveCount),bytes=64+8*capacity;')
 s=s.replace('end:base+bytes,capacity};','end:base+bytes,capacity,liveCount};')
 a='const key=cons(ordinal+1),value=cons(ordinal+101);cons(999); // unrooted garbage\n  assert.equal(service.ht_run(table,table-6+bytes,1,key,value,scratch,scratch+131072,result),0);'
 b='''for(let i=0;i<liveCount;i++){
   const key=cons(i+1),value=cons(i+101);
   assert.equal(service.ht_run(table,table-6+bytes,1,key,value,scratch,scratch+131072,result),0,'measured population insertion');
  }
  cons(999); // unrooted garbage'''
 assert a in s;s=s.replace(a,b).replace("get(cfg+84),3,'three live objects'","get(cfg+84),1+2*liveCount,'measured live objects'").replace("bytes+16,'table alone retains key and value'","bytes+16*liveCount,'table alone retains key and value'")
 a="assert.equal(found.length,1);const [k,v]=found[0];assert.equal(get(k+3),(ordinal+1)*4);assert.equal(get(v+3),(ordinal+101)*4);"
 b="assert.equal(found.length,liveCount);const indices=new Set();for(const [k,v] of found){const index=get(k+3)/4;assert(index>=1&&index<=liveCount);indices.add(index);assert.equal(get(v+3),(index+100)*4);}\n   assert.equal(indices.size,liveCount,'all measured entries retained');const [k,v]=found[0];"
 assert a in s;s=s.replace(a,b).replace('base,capacity,collections:3','base,capacity,liveCount,measurement:countBySite.has(site.id),collections:3')
 return s
