// B-call adapter's synchronous owner service. Decode only the supplied rooted
// arguments, with bounded traversal; never search the heap for definitions.
const NIL = 77825, T = 77838;
const need = (ok, why) => { if (!ok) throw Error('target code: ' + why); };
export function targetCodeService({memory, session, maxNodes = 2000000}) {
  return (recordPointer, symbolsPointer) => {
    const view = new DataView(memory.buffer);
    let remaining = maxNodes;
    const span = (p, n) => need(Number.isSafeInteger(p) && p >= 0 && n >= 0 && p + n <= view.byteLength, 'EXTENT');
    const get = p => { span(p, 4); return view.getUint32(p, true); };
    const active = new Set();
    const decode = (word, depth = 0) => {
      need(--remaining >= 0 && depth < 128, 'RECORD_LIMIT');
      if (word === NIL) return null;
      if (word === T) return true;
      if (word % 4 === 0) return (word | 0) >> 2;
      need(!active.has(word), 'CYCLIC_RECORD');
      active.add(word);
      try {
        if (word % 8 === 1) {
          const result = [], seen = new Set();
          for (let node = word; node !== NIL;) {
            need(--remaining >= 0 && !seen.has(node), 'CYCLIC_RECORD'); seen.add(node);
            if (node % 8 !== 1) { result.push(decode(node, depth + 1)); break; }
            span(node - 1, 8);
            result.push(decode(get(node + 3), depth + 1)); node = get(node - 1);
          }
          return result;
        }
        need(word % 8 === 6, 'RECORD_TAG');
        const header = get(word - 6), count = header >>> 8, kind = header & 255;
        need(count <= remaining, 'RECORD_LIMIT'); remaining -= count;
        span(word - 2, count * 4);
        if (kind === 250) return Array.from({length: count}, (_, i) => decode(get(word - 2 + i * 4), depth + 1));
        need(kind === 191, 'RECORD_KIND');
        let text = '';
        for (let i = 0; i < count; i++) {
          const c = get(word - 2 + i * 4); need(c <= 0x10ffff && !(c >= 0xd800 && c <= 0xdfff), 'CHARACTER');
          text += String.fromCodePoint(c);
        }
        return text;
      } finally { active.delete(word); }
    };
    const record = decode(recordPointer >>> 0), pointer = symbolsPointer >>> 0;
    need(Array.isArray(record) && [4, 5, 6].includes(record[0]) && typeof record[1] === 'string', 'RECORD_VERSION');
    need(pointer % 8 === 6, 'SYMBOL_VECTOR');
    const header = get(pointer - 6), count = header >>> 8;
    need((header & 255) === 250 && count <= maxNodes, 'SYMBOL_VECTOR'); span(pointer - 2, count * 4);
    const symbols = Array.from({length: count}, (_, i) => get(pointer - 2 + i * 4));
    // ENSURE-BINDING-INDEX deliberately leaves static/constant symbols at
    // index zero. Generated SPECIAL-LOCATION reads their global value cell.
    const specials = row => {
      for (const index of row[9] ?? []) {
        need(Number.isInteger(index) && index >= 0 && index < count, 'SPECIAL_INDEX');
        const symbol = symbols[index];
        need(symbol % 8 === 6 && get(symbol - 6) === 1850, 'SPECIAL_SYMBOL');
        const binding = get(symbol + 22), bits = get(symbol + 14);
        need(binding % 4 === 0 && binding <= 0x7ffffffc && bits % 4 === 0 &&
          (binding !== 0 || (bits & 24) !== 0), 'UNASSIGNED_SPECIAL');
      }
      for (const child of row[8] ?? []) specials(child);
    };
    specials(record);
    return session.install(record[1], record, symbols) * 4;
  };
}
