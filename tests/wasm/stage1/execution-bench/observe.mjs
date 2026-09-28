// Optional benchmark-only observation at ordinary Lisp output safepoints.
// Timing is performed inside Lisp, after BEGIN and before END formatting.
import assert from 'node:assert/strict';

export function benchmarkObserver(memory, tcr, owner) {
  const word = offset => new DataView(memory.buffer).getUint32(tcr + offset, true);
  const samples = [], forced = [];
  let pending = '', active = null, force = false;
  function checkpoint() {
    if (active) {
      active.allocatedBytes += word(48) - active.pointer;
      active.pointer = word(48);
    }
  }
  return {
    request(run) {
      let value=run();
      if(force){
        force=false;
        const before=owner.collectionCount,oldBase=word(56);
        // processService returns the printed string. Root that return value
        // before moving; its JS local otherwise holds the retired address.
        owner.atSafepoint(o=>{
          const held=o.rootCells([value]);
          try{o.collect();value=held.values()[0];}finally{held.release();}
        });
        assert.equal(owner.collectionCount,before+1);
        forced.push({before,after:owner.collectionCount,oldBase,newBase:word(56)});
        assert.notEqual(oldBase,word(56),'witness must move between spaces');
      }
      return value;
    },
    beforeCollection: checkpoint,
    afterCollection() { if (active) active.pointer = word(48); },
    output(channel, text) {
      if (channel !== 1) return;
      pending += text;
      for (;;) {
        const end = pending.indexOf('\n');
        if (end < 0) break;
        const line = pending.slice(0, end).trim(); pending = pending.slice(end + 1);
        if (line === 'EB-GC') {
          assert(!active, 'forced collection is a correctness witness, outside timings');
          assert(!force,'duplicate forced collection marker');force=true;
        }
        if (line.startsWith('EB-BEGIN ')) {
          assert(!active, 'nested benchmark');
          const [, name, trial, iterations] = line.split(' ');
          active = {name, trial: +trial, iterations: +iterations, pointer: word(48),
            allocatedBytes: 0, collectionStart: owner.collectionCount};
        }
        if (line.startsWith('EB-END ')) {
          assert(active, 'end without begin'); checkpoint();
          const [, name, trial, iterations] = line.split(' ');
          assert.equal(name, active.name); assert.equal(+trial, active.trial);
          assert.equal(+iterations, active.iterations);
          const {pointer, collectionStart, ...sample} = active;
          samples.push({...sample, collections: owner.collectionCount - collectionStart});
          active = null;
        }
      }
    },
    result() {
      assert(!active && !force, 'unfinished benchmark');
      return {forced, samples, allocationScope: 'BEGIN-to-END output markers, including untimed timer/check/format bookkeeping; collection copying excluded. Timed Lisp interval is narrower.'};
    }
  };
}
