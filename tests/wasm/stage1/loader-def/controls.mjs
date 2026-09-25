import assert from 'node:assert/strict';
import {controls as pointerControls} from './pointer-controls.mjs';

export function controls(context) {
  const rows=pointerControls(context);
  const {get,put,t,symbolAddress,callObject}=context;
  const symbol=name=>symbolAddress('CCL',name);
  const cleanup=symbol('*LOADER-DEF-CLEANUPS*')+2;
  const witness=get(symbol('LOADER-DEF-BOUNDARY')+6);
  for(const [operation,name] of ['NTH-CATCH-FRAME-TAG','LFUN-BITS'].entries()) {
    const state=[64,76,88,108,128,140,148].map(t),before=get(cleanup);
    assert.throws(()=>callObject(witness,[4*operation],false),/^Error: checked \d+$/);
    assert.deepEqual([64,76,88,108,128,140,148].map(t),state);
    assert.equal(get(cleanup),before+4);
    rows.push({name:'definition-boundary-'+operation,checked:true,cleanup:true,statePreserved:true});
    const cell=symbol(name)+6,saved=get(cell);
    try {
      put(cell,get(symbol('LOADER-POINTER-ALLOW')+6));
      assert.deepEqual(callObject(witness,[4*operation]),[19]);
      assert.equal(get(cleanup),before+8);
      rows.push({name:'definition-boundary-omitted-'+operation,status:'KILLED'});
    } finally {put(cell,saved);}
  }
  return rows;
}
