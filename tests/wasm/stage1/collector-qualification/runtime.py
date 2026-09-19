"""Complete the pointer-free LL10 layouts in both moving and pinned scanners."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def collector():
 s=(ROOT/'runtime/wasm32/collector.c').read_text()
 a=s.index('static U raw_bytes');b=s.index('static U find',a)
 s=s[:a]+'''/* Header counts are 24 bits; even 16-byte elements fit U arithmetic. */
static U raw_bytes(U tag,U n) {
 switch(tag) {
 case 7:return n?n*4:0xffffffffu;
 case 15:return n==1?4:0xffffffffu;
 case 23:return n==3?12:0xffffffffu;
 case 159:case 167:case 175:case 183:case 191:return n*4;
 case 199:case 207:return n;
 case 215:case 223:return n*2;
 case 231:case 239:return 4+n*8;
 case 247:return 4+n*16;
 case 255:return (n+7)/8;
 default:return 0xffffffffu;
 }
}
'''+s[b:]
 return replace(s,'if(!bytes && !((tag==191||tag==215||tag==223)&&n==0))','if(bytes==0xffffffffu)')
def owner():
 s=(ROOT/'runtime/wasm32/collector-owner.mjs').read_text()
 old='if([7,15,191].includes(tag))raw=n*4;else if([215,223].includes(tag))raw=n*2;else if(tag===231)raw=4+8*n;else if(tag===23&&n===3)raw=12;'
 new='if(tag===7&&n>0)raw=n*4;else if(tag===15&&n===1)raw=4;else if(tag===23&&n===3)raw=12;else if([159,167,175,183,191].includes(tag))raw=n*4;else if([199,207].includes(tag))raw=n;else if([215,223].includes(tag))raw=n*2;else if([231,239].includes(tag))raw=4+8*n;else if(tag===247)raw=4+16*n;else if(tag===255)raw=Math.ceil(n/8);'
 return replace(s,old,new)
