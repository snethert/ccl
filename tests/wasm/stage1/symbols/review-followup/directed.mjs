// Called before and after the inherited trace's real relocation.
import assert from 'node:assert/strict';
export function directed({code,raw,service,CONFIG,RESULT,NIL,owner,packages,statuses,expected,phase}) {
 const {get,put,query,decode}=owner,checks=[];
 const keywordCall=(op,name)=>code?code.invokeForm('symbol_values',op,query(name),packages.KEYWORD):raw(op,query(name),packages.KEYWORD);
 const start=get(CONFIG+12),found=keywordCall(0,'ALLOW-OTHER-KEYS');
 assert.equal(found[1],statuses[1],'pre-existing keyword must be external before INTERN');
 const again=keywordCall(1,'ALLOW-OTHER-KEYS'),s=found[0];
 const kw=[s!==NIL,found[1]===statuses[1],s===again[0],again[1]===statuses[1],get(s+2)===s,get(s+10)===packages.KEYWORD].map(Number);
 assert.deepEqual(kw,expected.keyword,'native pre-existing keyword');assert.equal(get(CONFIG+12),start,'pre-existing keyword allocates nothing');
 if(code)assert.deepEqual(code.call('symbol_read',[s]),[s],'generated keyword self-value');
 const forms=['symbol_call','symbol_values','symbol_preserve','symbol_apply','symbol_dynamic','symbol_indirect'];
 const made=[];
 if(code)for(let i=0;i<forms.length;i++){
  const before=code.operationCounts(2),values=code.invokeForm(forms[i],2,query('FRESH')),other=code.invokeForm(forms[i],2,query('FRESH'));
  const symbol=values[0],row=[i,values.length,Number(raw(4,symbol)[0]===NIL),Number(decode(raw(3,symbol)[0])==='FRESH'),Number(symbol!==other[0]),Number(values.length===1||values[1]===NIL)];
  assert.deepEqual(row,expected.make[i],'MAKE-SYMBOL '+forms[i]);
  assert(!made.includes(symbol),'MAKE-SYMBOL identities across forms');made.push(symbol);
  const after=code.operationCounts(2),delta=Object.fromEntries(Object.keys(before).map(k=>[k,after[k]-before[k]]));
  const mode=i<4?'fixed_calls':i===4?'direct_calls':'dynamic_calls';
  assert.equal(delta[mode],2,'MAKE-SYMBOL per-form delivery '+forms[i]);
  if(i===5)assert.equal(delta.direct_calls,0,'MAKE-SYMBOL indirect descriptor');
  checks.push({form:forms[i],native:row,delivery:delta});
 }
 const chars=[];
 for(const [point,native] of expected.characters){
  // Write an explicit UTF-32 word: JS must not normalise or encode it for us.
  const q=query('X');put(q-2,point);
  const before=get(CONFIG+12),imageBase=get(CONFIG+4),saved=Uint8Array.from(new Uint8Array(ownerMemory(owner),imageBase,before-imageBase));
  const config=Array.from({length:20},(_,i)=>get(CONFIG+4*i));for(let i=0;i<4;i++)put(RESULT+4*i,0x59595959);
  const status=service.symbols_run(CONFIG,2,q,NIL,NIL,RESULT);
  if(native<0){
   assert.equal(status,4,'native rejected character '+point);
   assert.equal(service.symbol_hash(q),0,'invalid character hash');
   assert.equal(get(CONFIG+12),before);assert.deepEqual(Array.from({length:20},(_,i)=>get(CONFIG+4*i)),config);
   assert.deepEqual(new Uint8Array(ownerMemory(owner),imageBase,saved.length),saved,'invalid character preserves image');
   assert.deepEqual(Array.from({length:4},(_,i)=>get(RESULT+4*i)),Array(4).fill(0x59595959),'invalid character preserves result');
  }else{
   assert.equal(status,0,'native accepted character '+point);const name=raw(3,get(RESULT))[0];assert.equal(get(name-2),native);
   if(code){const v=code.invokeForm('symbol_indirect',2,q);assert.equal(get(raw(3,v[0])[0]-2),native);}
  }
  chars.push({point,native,status});
 }
 return {phase,keyword:kw,keywordPointer:s,make:checks,characters:chars};
}
function ownerMemory(owner){return owner.memory.buffer;}
