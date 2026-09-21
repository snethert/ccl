from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def generate():
 s=(ROOT/'runtime/wasm32/hash.c').read_text()
 s=replace(s,'static U key_slot', (HERE/'keys.c').read_text()+'\nstatic U key_slot')
 s=replace(s,'U at=hash(key,n),free=NONE;', 'U at=content_hash(key,n),free=NONE;')
 s=replace(s,'if(k==key){','if(k!=EMPTY&&k!=DELETED&&same(k,key)){')
 s=replace(s,'U at=hash(k,n);used++;','U at=content_hash(k,n);used++;')
 s=replace(s,'if(present==k)return BAD_TABLE;','if(present!=EMPTY&&same(present,k))return BAD_TABLE;')
 s=replace(s,'if(op!=3&&!key_ok(key))return BAD_KEY;', '''if(op!=3&&(!key_ok(key)||!keys_valid(key,b,bytes(n),scratch,scratch_end,result)))return BAD_KEY;
 for(U j=0;j<n;j++){U k=L(key_slot(b,j));if(k!=EMPTY&&k!=DELETED&&!keys_valid(k,b,bytes(n),scratch,scratch_end,result))return BAD_KEY;}
 if(L(b+44)!=EMPTY&&!keys_valid(L(b+44),b,bytes(n),scratch,scratch_end,result))return BAD_KEY;''')
 s=replace(s,'if(L(key_slot(b,i))==key)found=1;', 'if(same(L(key_slot(b,i)),key))found=1;')
 s=replace(s,'if(L(b+44)==key){','if(L(b+44)!=EMPTY&&same(L(b+44),key)){')
 return s

def owner():
 s=(ROOT/'runtime/wasm32/bootstrap-tables.mjs').read_text()
 s=replace(s,'createStrongEQ','createStrongEquality')
 s=replace(s,"if(plan.test!=='eq')throw Error('equality service not installed: '+plan.test);", "if(!['eql','equal'].includes(plan.test)||service.ht_kind()!==(plan.test==='eql'?1:2))throw Error('equality service identity');")
 s=replace(s,"end!==base+bytes||end>memory.buffer.byteLength)","end!==base+bytes||end>memory.buffer.byteLength||(base<1114112&&end>1048576))")
 return s
