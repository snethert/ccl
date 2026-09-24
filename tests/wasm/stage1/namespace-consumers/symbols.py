"""Compose the qualified symbol leaf with the linker's existing symbol cells."""
from pathlib import Path
HERE=Path(__file__).resolve().parent

def source():
    text=(HERE.parents[3]/'runtime/wasm32/symbols.c').read_text()
    text=text.replace('*n<=1024&&inside(c,node-6', '*n<=16384&&inside(c,node-6')
    text=text.replace('*n>256||', '*n>8192||')
    old='if(sym!=NIL&&sym!=TRUE&&!inside(c,p,32))return 0;'
    new='''if(sym!=NIL&&sym!=TRUE&&!inside(c,p,32)){
  U lo=L(c+72),hi=L(c+76);
  if(!lo||p<lo||(W)p+32>hi||((p-lo)&31)||!span(p,32))return 0;
 }'''
    assert text.count(old)==1
    text=text.replace(old,new)
    old=' return 1;\n}\nstatic U vector'
    new=''' U lo=L(c+72),hi=L(c+76);
 if(lo||hi){if((lo&7)||hi<lo||((hi-lo)&31)||!span(lo,(W)hi-lo)||
  overlap(lo,(W)hi-lo,base,(W)end-base)||overlap(lo,(W)hi-lo,c,80)||
  overlap(lo,(W)hi-lo,sc,sz)||overlap(lo,(W)hi-lo,result,16))return 0;}
 return 1;
}
static U vector'''
    assert text.count(old)==1
    return text.replace(old,new)
