import assert from 'node:assert/strict';

// Allocate all nodes before filling any edge. The graph has no native address
// in it; identities and cycles are represented only by node numbers.
export function encodeGraph(graph, {get, put, bytes, tcr, encode, functionWord, bindFunction, bindValue, bindCondition, hash, registerCell}) {
  const words = graph.nodes.map(node => {
    const base = get(tcr + 48);
    const size = node.hash ? hash.ht_size(2**Math.ceil(Math.log2(Math.max(4,node.hash.length*2)))) : node.generic ? 64 : node.function ? 32 : node.tag === 1 ? 8 : (8 * Math.ceil((node.fields.length + 1) / 2));
    assert(base + size <= get(tcr + 52), 'graph fits allocation region');
    bytes(base, size).fill(0);
    put(tcr + 48, base + size);
    if (node.function || node.generic) {
      const template = functionWord(node.function || 'CCL::FUNCALLABLE-TRAMPOLINE');
      assert(template, node.function);
      bytes(base, 32).set(bytes(template - 6, 32));
      if (node.generic) {
        put(base, 1834);
        put(base + 28, base + 38);
        [2042, 77825, 77825, 77825, 77825, 77825, 0, node.bits * 4].forEach((x, i) => put(base + 32 + 4 * i, x));
      }
    } else if (node.hash) assert.equal(hash.ht_init(base,base+size,2**Math.ceil(Math.log2(Math.max(4,node.hash.length*2)))),0);
    else if (node.tag !== 1) put(base, node.fields.length * 256 + node.tag);
    return base + (node.tag === 1 ? 1 : 6);
  });
  const resolve = ref => Object.hasOwn(ref, 'ref') ? words[ref.ref] : encode(ref.value);
  graph.nodes.forEach((node, index) => {
    if (node.function || node.hash) return;
    if (node.generic) {
      const side = words[index] + 26;
      node.generic.forEach((ref, i) => put(side + 8 + 4 * i, resolve(ref)));
      if(node.binding) bindFunction(node.binding,words[index]);
      return;
    }
    const word = words[index];
    node.fields.forEach((ref, i) => put(node.tag === 1 ? word + (i === 0 ? 3 : -1) : word - 2 + 4 * i, resolve(ref)));
  });
  graph.nodes.forEach((node,index)=>{
    if(node.hash){const word=words[index],end=word-6+hash.ht_size(2**Math.ceil(Math.log2(Math.max(4,node.hash.length*2))));
      for(const [key,value] of node.hash)assert.equal(hash.ht_run(word,end,1,resolve(key),resolve(value),1800000,1860000,1169504),0);
    }
    if(node.tag===130)registerCell(get(words[index]-2));
  });
  if(Object.hasOwn(graph,'standardCombination'))bindValue('CCL::*STANDARD-METHOD-COMBINATION*',words[graph.standardCombination]);
  for(const [name,ref] of graph.conditions||[])bindCondition(name,resolve(ref));
  return resolve(graph.root);
}

// Read every projected field back, including sharing. The descriptor supplies
// node numbers and expected shapes, never observed scalar values.
export function decodeGraph(word, graph, {get, decode, encode, functionWord, conditionWord,hash}) {
  const words = new Map(), seen = new Map(), nodes = Array(graph.nodes.length);
  function read(word, descriptor) {
    if (!Object.hasOwn(descriptor, 'ref')) return {value: decode(word)};
    const id = descriptor.ref;
    if (words.has(id)) { assert.equal(word, words.get(id), 'graph shared identity'); return {ref: id}; }
    assert(!seen.has(word), 'distinct graph nodes aliased');
    words.set(id, word); seen.set(word, id);
    const expected = graph.nodes[id];
    if(expected.hash){
      const size=hash.ht_size(2**Math.ceil(Math.log2(Math.max(4,expected.hash.length*2))));
      assert.equal(get(word-6)&255,74);
      assert.equal(get(word+30),expected.hash.length*4,'hash live count');
      nodes[id]={hash:expected.hash.map(([key,value])=>{
        const entry=Array.from({length:(size-64)/8},(_,i)=>word-6+60+8*i).find(p=>{
          const expectedKey=key.value?.symbol;
          return expectedKey ? get(p)===functionWord('SYMBOL:'+expectedKey) :
            key.value === true ? get(p) === encode(true) : false;
        });
        assert(entry!==undefined,'projected hash key present');
        return [read(get(entry),key),read(get(entry+4),value)];
      })};
    } else if (expected.generic) {
      assert.equal(get(word-6),1834);
      const side=get(word+22);
      assert.equal(get(side-6),2042);
      nodes[id]={generic:expected.generic.map((ref,i)=>read(get(side+2+4*i),ref)),bits:get(side+22)/4};
      if(expected.binding){assert.equal(functionWord(expected.binding),word,"bound protocol function");nodes[id].binding=expected.binding;}
    } else if (expected.function) {
      const template = functionWord(expected.function);
      assert.equal(get(word - 6), 1578, 'graph function header');
      assert.equal(get(word - 2), get(template - 2), 'graph function code');
      const pool = get(word + 18), offset = get(word + 10) === 77825 ? 0 : 8;
      assert.equal(get(pool - 2 + offset), 0x574153 * 4, 'function-info prefix');
      nodes[id] = {function: expected.function, bits: get(pool + 2 + offset) / 4};
    } else {
      if (expected.tag === 1) assert.equal(word & 7, 1);
      else assert.equal(get(word - 6), expected.fields.length * 256 + expected.tag, 'graph node shape');
      nodes[id] = {tag: expected.tag, fields: expected.fields.map((ref, i) =>
        read(get(expected.tag === 1 ? word + (i === 0 ? 3 : -1) : word - 2 + i * 4), ref))};
    }
    return {ref: id};
  }
  const root = read(word, graph.root);
  const reader=graph.reader ? read(functionWord('CCL::EQL-SPECIALIZER-OBJECT'),graph.reader) : undefined;
  const conditions=graph.conditions?.map(([name,ref])=>[name,read(conditionWord(name),ref)]);
  assert.equal(words.size, graph.nodes.length, 'all graph nodes reachable');
  return {graph: {root, ...(reader ? {reader} : {}), ...(conditions ? {conditions} : {}), ...(Object.hasOwn(graph,'standardCombination') ? {standardCombination:graph.standardCombination} : {}), nodes}};
}
