import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {inspect} from '../runtime-boundary/binary.mjs';
export const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
export function validateCode(bytes,record,k,minimum) {
  assert.equal(sha(bytes),record.sha256,'CODE_DIGEST_MISMATCH');
  assert.ok(WebAssembly.validate(bytes),'INVALID_MODULE');
  const m=inspect(bytes);
  assert.ok(m.start===undefined&&!m.data.length&&!m.elements.length,'UNAUTHORIZED_INITIALIZATION');
  const memories=m.imports.filter(i=>i.kind==='memory'),tables=m.imports.filter(i=>i.kind==='table');
  assert.deepEqual(memories,[{module:'env',name:'memory',kind:'memory',flags:3,minimum:8,maximum:16}],'MEMORY_PROFILE_MISMATCH');
  assert.deepEqual(tables,[{module:'env',name:'table',kind:'table',element:'funcref',flags:0,minimum,maximum:null}],'TABLE_CONTRACT_MISMATCH');
  for(const i of m.imports) {
    if(i.kind!=='function')continue;
    assert.ok(i.module==='abi'||(i.module==='kernel'&&i.name==='get_tcr')||(i.module==='loader'&&i.name==='lookup'),'UNAUTHORIZED_IMPORT');
  }
  assert.deepEqual(m.exports.map(e=>e.name).sort(),['G','adapter','direct'],'ENTRY_SET_MISMATCH');
  for(const e of m.exports) {
    assert.equal(e.kind,0,'ENTRY_KIND_MISMATCH');
    assert.deepEqual(m.types[m.functionTypes[e.index]],{params:Array(e.name==='adapter'?3:k+2).fill('i32'),results:['i32','i32']},'ENTRY_SIGNATURE_MISMATCH');
  }
  return m;
}
