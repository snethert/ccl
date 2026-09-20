"""Derive an isolated hash-vector scanner from the integrated copying collector."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
def replace(s,a,b):
    assert s.count(a)==1,(a[:100],s.count(a))
    return s.replace(a,b)
def generate():
    s=(ROOT/'runtime/wasm32/collector.c').read_text()
    s=replace(s,'if(node_subtag(tag)||(tag==130&&n==6)){scan=n;size=4+(W)n*4;}', '''if(tag==74){
    /* Only strong owner-created EQ vectors; never infer weak semantics. */
    U capacity=n>=14?(n-14)/2:0;
    if(n<22||((n-14)&1)||capacity>16384||(capacity&(capacity-1))||(W)p+4+4*(W)n>s->used)return reject(s,BAD_OBJECT);
    if((LOAD(p+8)&~((1u<<30)|(1u<<29)))||!(LOAD(p+8)&(1u<<30))||LOAD(p+52)!=capacity*4||LOAD(p+56)!=0)return reject(s,BAD_OBJECT);
    if(LOAD(p+4)!=NIL||LOAD(p+12)!=0||LOAD(p+16)!=NIL||LOAD(p+20)!=NIL||LOAD(p+24)!=0||LOAD(p+28)!=NIL)return reject(s,BAD_OBJECT);
    if(((LOAD(p+32)|LOAD(p+36))&3)||LOAD(p+32)/4>capacity||LOAD(p+36)/4>capacity||LOAD(p+32)/4+LOAD(p+36)/4>capacity)return reject(s,BAD_OBJECT);
    if(LOAD(p+40)!=0xfffffffcu&&((LOAD(p+40)&3)||LOAD(p+40)/4>=capacity))return reject(s,BAD_OBJECT);
    scan=n;size=4+(W)n*4;
   }
   else if(node_subtag(tag)||(tag==130&&n==6)){scan=n;size=4+(W)n*4;}''')
    s=replace(s,'U v=forward(s,LOAD(p+4*index));STORE(p+4*index,v);', '''U old=LOAD(p+4*index),v=forward(s,old);STORE(p+4*index,v);
   /* Payload index 14 is object word 15: first key. Cached keys are roots,
    * but only bucket-key movement requests a rehash. Destination-only write
    * preserves the collector's source/root atomicity on refusal. */
   if((LOAD(o->moved)&255)==74&&index>=14&&!(index&1)&&old!=v)
    STORE(o->moved+8,LOAD(o->moved+8)|(1u<<29));''')
    return s
