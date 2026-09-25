import assert from 'node:assert/strict';
import {controls as arrayControls} from './controls.mjs';

export function controls(context) {
  const rows=arrayControls(context);
  const {get,put,N,t,symbolAddress,callObject}=context;
  const symbol=name=>symbolAddress('CCL',name);
  const value=name=>get(symbol(name)+2);
  const fn=get(symbol('LOADER-POINTER-BOUNDARY')+6);
  const names=['MPN-SQR-BASECASE','MPN-KARA-SQR-N','MPN-KARA-MUL-N','MPN-SQR-N',
    'MPN-MUL-N','MPN-MUL','UNSIGNEDWIDE->INTEGER','ENTRY->ADDR','FOREIGN-SYMBOL-ENTRY',
    'FOREIGN-SYMBOL-ADDRESS','REFRESH-EXTERNAL-ENTRYPOINTS','OPEN-SHARED-LIBRARY-INTERNAL'];
  for(const name of ['*RTLD-NEXT*','*RTLD-DEFAULT*','*RTLD-USE*'])
    assert.equal(value(name),N,name+' has no native pointer');
  for(let operation=0;operation<12;operation++) {
    const before=[64,76,88,128,108].map(t);
    const cleanup=value('*LOADER-POINTER-CLEANUPS*');
    assert.throws(()=>callObject(fn,[operation*4],false),/^Error: checked \d+$/);
    assert.deepEqual([64,76,88,128,108].map(t),before,'pointer refusal restores TCR');
    assert.equal(value('*LOADER-POINTER-CLEANUPS*'),cleanup+4,'Lisp cleanup runs');
    rows.push({name:'native-pointer-'+operation,checked:true,cleanup:true,statePreserved:true});
    const cell=symbol(names[operation])+6,saved=get(cell);
    assert.equal(get(saved-6),1578,'refusal function exists');
    try {
      put(cell,get(symbol('LOADER-POINTER-ALLOW')+6));
      assert.deepEqual(callObject(fn,[operation*4]),[19]);
      assert.equal(value('*LOADER-POINTER-CLEANUPS*'),cleanup+8);
      rows.push({name:'native-pointer-error-omitted-'+operation,status:'KILLED'});
    } finally {put(cell,saved);}
  }
  const original=symbol('LOADER-LITERAL-ORIGINAL')+6;
  const saved=get(original),other=get(symbol('LOADER-LITERAL-OTHER')+6);
  try {
    put(original,other);
    assert.deepEqual(callObject(other,[20]),[-6]);
    assert.equal(callObject(get(symbol('LOADER-LITERAL-CALL')+6),[20])[0],42);
    rows.push({name:'function-literal-binding-independent',status:'PASS'});
  } finally {put(original,saved);}
  return rows;
}
