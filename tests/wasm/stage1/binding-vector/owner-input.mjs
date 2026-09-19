if(c.owner){const o=c.owner;
 if(o.index!==undefined)store(symbols.dyn_a+22,4*o.index);
 if(o.rawIndex!==undefined)store(symbols.dyn_a+22,o.rawIndex);
 if(o.initialCapacity!==undefined)set(108,o.initialCapacity);
 if(o.vectorBase!==undefined)set(104,o.vectorBase==='heap'?heap:o.vectorBase);
 if(o.baseDelta)set(104,get(104)+o.baseDelta);
 if(o.heapBytes!==undefined)set(52,heap+o.heapBytes);
 if(o.allocDelta)set(48,heap+o.allocDelta);
}
