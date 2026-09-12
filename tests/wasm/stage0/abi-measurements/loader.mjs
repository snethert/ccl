import assert from 'node:assert/strict';
import {inspect} from '../runtime-boundary/binary.mjs';
import {sha} from '../dynamic-call/loader.mjs';
export {validateCode,sha} from '../dynamic-call/loader.mjs';

export function validateDriver(bytes,expected,k,slots,packaging) {
  assert.equal(sha(bytes),expected,'DRIVER_DIGEST_MISMATCH');
  assert.ok(WebAssembly.validate(bytes),'INVALID_DRIVER');
  const m=inspect(bytes);
  assert.ok(m.start===undefined&&!m.data.length&&!m.elements.length,'DRIVER_INITIALIZATION');
  assert.deepEqual(m.imports.filter(i=>i.kind==='memory'),[{module:'env',name:'memory',kind:'memory',flags:3,minimum:8,maximum:16}]);
  assert.deepEqual(m.imports.filter(i=>i.kind==='table'),[{module:'env',name:'table',kind:'table',element:'funcref',flags:0,minimum:slots.minimum,maximum:null}]);
  const allowed=new Set(['get_tcr','admit','park','measure_ownership','measure_digest']);
  for(const i of m.imports.filter(i=>i.kind==='function'))
    assert.ok(i.module==='abi'||(i.module==='kernel'&&allowed.has(i.name))||(i.module==='loader'&&i.name==='lookup'),'DRIVER_IMPORT');
  const names=['dispatch','batch',...(packaging==='cross-instance'?[]:slots.entries.flatMap(e=>['G','direct','adapter'].map(r=>r+e.code)))];
  assert.deepEqual(m.exports.map(e=>e.name).sort(),names.sort(),'DRIVER_EXPORTS');
  for(const e of m.exports) {
    assert.equal(e.kind,0);
    const n=e.name==='batch'?2:e.name.startsWith('adapter')?3:k+2;
    assert.deepEqual(m.types[m.functionTypes[e.index]],{params:Array(n).fill('i32'),results:['i32','i32']},'DRIVER_SIGNATURE');
  }
}

/* The table and this registry stay private to the Worker. Publication verifies
   all entries before changing any slot; calls cannot interleave with the stores. */
export class Roles {
  constructor(table,slots) {
    this.table=table;
    this.entries=new Map(slots.entries.flatMap(e=>['G','direct','adapter'].map(role=>
      [e[role],{code:e.code,role,signature:role==='adapter'?'adapter':'G',fn:null}])));
  }
  publish(code,entries) {
    for (const [slot,role,fn] of entries) {
      const e=this.entries.get(slot);
      assert.ok(e && e.code===code && e.role===role && typeof fn==='function','ROLE_MISMATCH');
    }
    assert.equal(new Set(entries.map(([slot])=>slot)).size,entries.length,'DUPLICATE_PUBLICATION');
    for (const [slot,,fn] of entries) { this.table.set(slot,fn); this.entries.get(slot).fn=fn; }
  }
  resolve(slot,code,role) {
    const e=this.entries.get(slot);
    assert.ok(e && e.code===code && e.role===role && e.fn && this.table.get(slot)===e.fn,'ROLE_MISMATCH');
    return slot;
  }
  checkAll() { for (const [slot,e] of this.entries) this.resolve(slot,e.code,e.role); }
}
