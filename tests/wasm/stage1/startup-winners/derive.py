from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
def derive():
 s=(ROOT/'runtime/wasm32/hash.c').read_text()
 old='if(op>3)return BAD_OPERATION;';assert s.count(old)==1
 s=s.replace(old,'if(op>3&&op!=5)return BAD_OPERATION;')
 old='if(op!=3&&!key_ok(key))return BAD_KEY;';assert s.count(old)==1
 s=s.replace(old,'if(op!=3&&op!=5&&!key_ok(key))return BAD_KEY;')
 old=' /* Full-table insertion refuses before rehash, preserving the vector. */';assert s.count(old)==1
 s=s.replace(old,''' /* CLR: shape and owner ranges are already validated. Clearing does not
  * need to follow/re-hash stale keys. Preserve object identity and capacity,
  * retire every bucket/cache reference, clear tombstones and key-moved. */
 if(op==5){ht_init(b,end,n);v=table;found=NIL;goto publish;}
'''+old)
 return s
