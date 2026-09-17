// Node fixture transport for materialized D1 pools; not a production image loader.
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const schemaBytes = readFileSync(new URL('../../../../doc/WASM/contracts/wasm32-layout.v1.json', import.meta.url));
const schema = JSON.parse(schemaBytes);
const constants = Object.fromEntries(schema.constants.map(x => [x.name, x.value]));
const tags = Object.fromEntries(schema.subtags.filter(x => x.disposition === 'inherited').map(x => [x.name.slice(7), x.value]));
export const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const layout = digest(schemaBytes);
const check = (ok, why) => {if (!ok) throw new Error(why);};
const uint = x => Number.isInteger(x) && x >= 0 && x <= 0xffffffff;
const shape = (x, keys) => check(x !== null && typeof x === 'object' && !Array.isArray(x) && Object.keys(x).sort().join(',') === [...keys].sort().join(','), 'record shape');
const nil = constants['canonical-nil-value'], truth = nil + constants['t-offset'];
const numeric = new Map(['u8','s8','u16','s16','u32','s32','fixnum','single-float'].map((x,i) => [tags[x+'-vector'], [1,1,2,2,4,4,4,4][i]]));
const floats = new Map([[tags['double-float-vector'],8], [tags['complex-single-float-vector'],8], [tags['complex-double-float-vector'],16]]);
const align = n => Math.ceil(n / 8) * 8;

function inspect(record, newBase, ownerSymbols) {
  shape(record, ['version','layout','base','image','objects','roots','symbols']);
  check(record.version === 1 && record.layout === layout, 'snapshot version/layout');
  check(uint(record.base) && record.base >= 8 && record.base % 8 === 0, 'source base');
  check(uint(newBase) && newBase >= 8 && newBase % 8 === 0, 'destination base');
  check(typeof record.image === 'string' && record.image.length <= 32*1024*1024 && /^(?:[0-9a-f]{2})*$/.test(record.image), 'image encoding/budget');
  const bytes = Buffer.from(record.image, 'hex'), size = bytes.length;
  check(record.base + size <= 2**32 && newBase + size <= 2**32, 'address extent');
  check(Array.isArray(record.objects) && Array.isArray(record.roots), 'object/root lists');
  const pointers = new Map(), offsets = [], ids = new Set();
  let cursor = 0;
  for (const object of record.objects) {
    shape(object, ['id','offset','tag']);
    check(typeof object.id === 'string' && object.id.length && !ids.has(object.id), 'object identity');
    ids.add(object.id);
    check(uint(object.offset) && object.offset === cursor && cursor + 8 <= size, 'object coverage');
    let extent;
    if (object.tag === constants['fulltag-cons']) {
      extent = 8; offsets.push(cursor, cursor+4);
    } else {
      check(object.tag === constants['fulltag-misc'], 'object tag');
      const header = bytes.readUInt32LE(cursor), tag = header % 256, count = Math.floor(header / 256);
      let payload, start = 4;
      if (tag === tags['simple-vector']) payload = 4*count;
      else if (tag === tags.bignum) {check(count > 0, 'empty bignum'); payload = 4*count;}
      else if (tag === tags['single-float']) {check(count === 1, 'single-float count'); payload = 4;}
      else if (tag === tags['double-float']) {check(count === 3, 'double-float count'); payload = 8; start = 8;}
      else if (tag === tags['simple-base-string']) payload = count*4;
      else if (numeric.has(tag)) payload = numeric.get(tag)*count;
      else if (floats.has(tag)) {payload = floats.get(tag)*count; start = 8;}
      else if (tag === tags['bit-vector']) payload = Math.ceil(count/8);
      else throw new Error('unsupported object header');
      extent = align(start+payload);
      check(cursor+extent <= size, 'object extent');
      if (tag === tags['simple-vector']) for (let i=0;i<count;i++) offsets.push(cursor+4+4*i);
      // Pointer-free payloads are transported as bits, never interpreted as roots.
    }
    check(cursor+extent <= size, 'object extent');
    pointers.set(record.base+cursor+object.tag, newBase+cursor+object.tag);
    cursor += extent;
  }
  check(cursor === size, 'unaccounted object bytes');
  const symbolMap = new Map(), reverseSymbols = new Map();
  check(record.symbols !== null && typeof record.symbols === 'object' && !Array.isArray(record.symbols), 'source symbols');
  check(ownerSymbols !== null && typeof ownerSymbols === 'object' && !Array.isArray(ownerSymbols), 'owner symbols');
  const outside = (word, base) => {const raw=word-(word%8); return !(raw>=base && raw<base+size);};
  for (const [key, old] of Object.entries(record.symbols)) {
    const fresh = Object.hasOwn(ownerSymbols,key) ? ownerSymbols[key] : undefined;
    check(key.length && uint(old) && old%8 === 6 && uint(fresh) && fresh%8 === 6, 'owner symbol binding');
    check(old !== truth && fresh !== truth, 'canonical symbol alias');
    check(outside(old,record.base) && outside(fresh,newBase), 'symbol overlaps pool');
    check(!symbolMap.has(old) || symbolMap.get(old) === fresh, 'symbol alias split');
    check(!reverseSymbols.has(fresh) || reverseSymbols.get(fresh) === old, 'distinct symbols merged');
    symbolMap.set(old, fresh); reverseSymbols.set(fresh, old);
  }
  for (const x of [nil,truth]) check(outside(x,record.base) && outside(x,newBase), 'canonical object overlap');
  const translate = word => {
    check(uint(word), 'invalid root word');
    if (word === nil || word === truth || word%4 === 0) return word;
    if (word%256 === tags.character) {check(Math.floor(word/256)<0x110000, 'character code'); return word;}
    if (pointers.has(word)) return pointers.get(word);
    if (symbolMap.has(word)) return symbolMap.get(word);
    throw new Error('unknown or interior pointer');
  };
  const roots = record.roots.map(translate);
  for (const where of offsets) bytes.writeUInt32LE(translate(bytes.readUInt32LE(where)), where);
  return {bytes, roots, objects:record.objects.map(x=>({id:x.id,address:newBase+x.offset+x.tag}))};
}

export function capture(memory, manifest) {
  shape(manifest, ['base','length','objects','roots','symbols']);
  check(memory instanceof WebAssembly.Memory && !(memory.buffer instanceof SharedArrayBuffer), 'unshared memory required');
  check(uint(manifest.length) && manifest.length<=16*1024*1024 && uint(manifest.base) && manifest.base+manifest.length<=memory.buffer.byteLength, 'capture extent');
  const record = {version:1, layout, base:manifest.base,
    image:Buffer.from(new Uint8Array(memory.buffer,manifest.base,manifest.length)).toString('hex'),
    objects:manifest.objects, roots:manifest.roots, symbols:manifest.symbols};
  inspect(record, record.base, record.symbols);
  const bytes = Buffer.from(JSON.stringify(record));
  return {bytes, sha256:digest(bytes)};
}

export function restore(bytes, expectedDigest, memory, base, regionBytes, ownerSymbols={}) {
  check(Buffer.isBuffer(bytes) && bytes.length <= 48*1024*1024, 'snapshot byte budget');
  check(digest(bytes) === expectedDigest, 'snapshot digest');
  check(memory instanceof WebAssembly.Memory && !(memory.buffer instanceof SharedArrayBuffer), 'unshared memory required');
  check(uint(regionBytes) && uint(base) && base+regionBytes<=memory.buffer.byteLength, 'owned region extent');
  const record = JSON.parse(bytes.toString('utf8'));
  const linked = inspect(record, base, ownerSymbols);
  check(linked.bytes.length<=regionBytes, 'owned region capacity');
  // All parsing, resolution and bounds checks precede the only target write.
  new Uint8Array(memory.buffer,base,linked.bytes.length).set(linked.bytes);
  return {roots:linked.roots, objects:linked.objects, byteLength:linked.bytes.length};
}
