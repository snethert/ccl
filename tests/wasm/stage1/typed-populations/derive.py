from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def replace(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def sources(parent):
 # Existing D1 tag; the exact two-field strong shape is not a native weak object.
 arch=(ROOT/'compiler/WASM32/wasm32-arch.lisp').read_text();assert '(:population . 90)' in arch
 builder=(ROOT/'runtime/wasm32/bootstrap-populations.mjs').read_text()
 builder=replace(builder,'2*256+250','2*256+90').replace('strong-population-v1','strong-population-v2')
 builder=builder.replace('// Image-builder representation: ordinary vector + conses, never a weak header.','// Exact D1 population-tagged two-field strong representation; no GC link or weak flags.')
 service=replace((parent/'execution/services/population.c').read_text(),'L(base)!=762','L(base)!=602')
 collector=(ROOT/'runtime/wasm32/collector.c').read_text()
 collector=replace(collector,'   if(tag==74){','''   if(tag==90){
    /* Stage 1 strong population v2: type and data, no weak GC-link slot. */
    if(n!=2||(W)p+16>s->used)return reject(s,BAD_OBJECT);
    if((LOAD(p+4)!=0&&LOAD(p+4)!=4)||LOAD(p+12)!=0)return reject(s,BAD_OBJECT);
    scan=2;size=16;
   }
   else if(tag==74){''')
 owner=(ROOT/'runtime/wasm32/collector-owner.mjs').read_text()
 owner=replace(owner,'     if([10,26,42,58,106,114,250].includes(tag)', '''     if(tag===90){
      need(n===2&&p+16<=region.end,'strong population shape');
      need([0,4].includes(this.#get(p+4))&&this.#get(p+12)===0,'strong population fields');
      count=2;bytes=16;
     }
     else if([10,26,42,58,106,114,250].includes(tag)''')
 return {'builder.mjs':builder,'population.c':service,'collector.c':collector,'owner.mjs':owner}
