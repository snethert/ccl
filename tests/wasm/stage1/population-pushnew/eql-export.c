/* Additional entry on the shared EQL table service; calls its existing
 * key validator and comparator. No second comparison implementation.
 * Canonical owner objects only; no allocation, poll, or JavaScript call. */
EXPORT U ht_eql(U a,U ignored_end,U ignored_op,U b,U ignored_value,U scratch,U scratch_end,U result){
 (void)ignored_end;(void)ignored_op;(void)ignored_value;(void)scratch;(void)scratch_end;
 if((result&3)||!span(result,16)||overlap(result,16,1048576,65536))return BAD_OWNER;
 if(!keys_valid(a,0,0,0,0,result)||!keys_valid(b,0,0,0,0,result))return BAD_KEY;
 U answer=same(a,b)?TRUE:NIL;
 S(result,answer);S(result+4,NIL);S(result+8,1);S(result+12,0);return 0;
}
