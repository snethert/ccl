// This assertion corpus is identical for the normal and quarantined modules.
import assert from 'node:assert/strict';
export const cases=[
  {name:'first-escape',closure:0,delta:3,old:17,initial:17,calls:1,exception:false},
  {name:'mutate-escaped-state',closure:0,delta:5,old:20,initial:17,calls:2,exception:false},
  {name:'independent-environment',closure:1,delta:7,old:100,initial:100,calls:1,exception:false},
  {name:'exceptional-cleanup',closure:0,delta:-2,old:25,initial:17,calls:3,exception:true},
  {name:'state-after-exception',closure:0,delta:11,old:23,initial:17,calls:4,exception:false},
];
export function check(observed,expected) {
  const next=expected.old+expected.delta;
  assert.equal(observed.factory_active,0,'factory frame must have returned');
  assert.equal(observed.exception,expected.exception,'exception disposition');
  assert.equal(observed.condition,expected.exception?700+next:null,'exception payload');
  if(expected.exception) {
    assert.equal(observed.nvalues,0,'exception must not publish values');
    assert.equal(observed.returned,null,'exception must not return normally');
  } else {
    assert.deepEqual(observed.returned,[next*4,6],'primary result and count');
    assert.equal(observed.nvalues,6,'published value count');
    assert.deepEqual(observed.values,[next,expected.old,expected.delta,expected.initial,expected.calls,73],'all six values');
  }
  assert.deepEqual(observed.log,[1,2,3],'observable cleanup order');
  assert.equal(observed.cleanup_effect,23,'observable cleanup effect');
  assert.deepEqual(observed.capture,[next,expected.calls,expected.initial],'escaped mutable capture');
}
