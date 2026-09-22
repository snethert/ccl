"""Derive the second callable shape without changing integrated runtime files."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]

def derive():
    c=(ROOT/'runtime/wasm32/collector.c').read_text()
    old='else if(node_subtag(tag)||(tag==130&&n>=1)){scan=n;size=4+(W)n*4;}'
    assert c.count(old)==1
    c=c.replace(old,'else if(node_subtag(tag)||(tag==130&&n>=1)){if(tag==42&&n!=6&&n!=7)return reject(s,BAD_OBJECT);scan=n;size=4+(W)n*4;}')
    marker=' /* Root chain uses the actual current descriptor shapes'
    assert c.count(marker)==1
    c=c.replace(marker,''' /* Validate the extra callable field after inventory, before any copy. */
 for(index=0;index<s->count;index++){
  p=objects(s)[index].old;
  if(LOAD(p)==1834){
   U value=LOAD(p+28),q=value-6,i;
   if((value&7)!=6||!extent(q,32)||LOAD(q)!=2042||inside(q,s->to,s->end))return reject(s,BAD_OBJECT);
   if(inside(q,s->from,s->limit)){
    i=find(s,q);if(i==0xffffffffu||objects(s)[i].size!=32)return reject(s,BAD_OBJECT);
   }
   if(inside(q,s->stacklo,s->stackhi))return reject(s,BAD_OBJECT);
  }
 }
'''+marker)
    owner=(ROOT/'runtime/wasm32/collector-owner.mjs').read_text()
    marker="    need(p+bytes<=region.end,'image object extent');"
    assert owner.count(marker)==1
    owner=owner.replace(marker,marker+'''
    if(tag===42){
     need(n===6||n===7,'image function shape');
     if(n===7){const q=this.#get(p+28);need(q%8===6&&q-6+32<=this.#view.byteLength,'image immediates extent');need(this.#get(q-6)===2042,'image immediates shape');}
    }''')
    installer=(ROOT/'runtime/wasm32/installer.mjs').read_text()
    old='const raw=object(f.object,1578,32);'
    assert installer.count(old)==1
    installer=installer.replace('validate,sha,PROFILE}', 'validate,sha,PROFILE,FLOAT_PROFILE}')
    installer=installer.replace("need(r.profile===PROFILE,'PROFILE');","need([PROFILE,FLOAT_PROFILE].includes(r.profile),'PROFILE');")
    installer=installer.replace(old,"const raw=object(f.object,f.immediates===undefined?1578:1834,32);if(f.immediates!==undefined){need(get(raw+28)===f.immediates,'IMMEDIATES_IDENTITY');vector(f.immediates,7);}")
    installer=installer.replace('entryRanges(b)', 'entryRanges(b,{ownerRetry:r.profile===FLOAT_PROFILE})')
    ranges=(ROOT/'runtime/wasm32/ranges.mjs').read_text().replace('entryRanges(bytes){', 'entryRanges(bytes,options={}){').replace('const m=inspect(bytes);','const m=inspect(bytes,options);')
    return {'ranges.mjs':ranges,'collector.c':c,'collector-owner.mjs':owner,'installer.mjs':installer}
