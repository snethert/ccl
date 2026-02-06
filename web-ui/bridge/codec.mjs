const MAGIC_TREE = 0x55494231; // "UIB1"
const MAGIC_EVENTS = 0x55494531; // "UIE1"
const VERSION = 1;

const EVENT_TYPES = Object.freeze({
  pointer: 1,
  key: 2,
  composition: 3,
  text: 4,
  focus: 5,
  blur: 6,
  wheel: 7
});

const VALUE_TYPES = Object.freeze({
  null: 0,
  bool: 1,
  number: 2,
  string: 3
});

const _decoder = typeof TextDecoder !== "undefined" ? new TextDecoder("utf-8") : null;
const _encoder = typeof TextEncoder !== "undefined" ? new TextEncoder() : null;

function decodeUtf8(bytes) {
  if (_decoder) return _decoder.decode(bytes);
  let out = "";
  for (let i = 0; i < bytes.length; i++) out += String.fromCharCode(bytes[i]);
  return out;
}

function encodeUtf8(text) {
  if (_encoder) return _encoder.encode(String(text));
  const s = String(text);
  const out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i) & 0xff;
  return out;
}

function readU32(dv, offset) {
  return dv.getUint32(offset, true);
}

function readF64FromU32(lo, hi) {
  const buf = new ArrayBuffer(8);
  const dv = new DataView(buf);
  dv.setUint32(0, lo >>> 0, true);
  dv.setUint32(4, hi >>> 0, true);
  return dv.getFloat64(0, true);
}

function writeU32(dv, offset, value) {
  dv.setUint32(offset, value >>> 0, true);
}

function writeF64(dv, offset, value) {
  dv.setFloat64(offset, Number(value ?? 0), true);
}

function decodeStringTable(bytes, offset, count) {
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const strings = new Array(count);
  let off = offset;
  for (let i = 0; i < count; i++) {
    const len = readU32(dv, off);
    off += 4;
    const slice = bytes.subarray(off, off + len);
    strings[i] = decodeUtf8(slice);
    off += len;
  }
  return { strings, offset: off };
}

export function decodeTree(payload) {
  if (!(payload instanceof Uint8Array)) {
    throw new Error("decodeTree expects Uint8Array payload");
  }
  const dv = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
  if (payload.byteLength < 24) {
    throw new Error("UI tree payload too small");
  }
  const magic = readU32(dv, 0);
  const version = readU32(dv, 4);
  if (magic !== MAGIC_TREE || version !== VERSION) {
    throw new Error("Unsupported UI tree payload version");
  }
  const stringCount = readU32(dv, 8);
  const nodeCount = readU32(dv, 12);
  const rootIndex = readU32(dv, 16);
  let off = 24;
  const table = decodeStringTable(payload, off, stringCount);
  const strings = table.strings;
  off = table.offset;
  if (nodeCount === 0) return null;
  if (rootIndex >= nodeCount) {
    throw new Error("UI tree root index out of range");
  }

  const nodes = new Array(nodeCount);
  const childLists = new Array(nodeCount).fill(null);

  for (let i = 0; i < nodeCount; i++) {
    if (off + 12 > payload.byteLength) {
      throw new Error("UI tree payload truncated");
    }
    const kind = readU32(dv, off);
    const flags = readU32(dv, off + 4);
    const keyIndex = readU32(dv, off + 8);
    const key = keyIndex === 0xffffffff ? null : strings[keyIndex];
    off += 12;
    if (kind === 0) {
      const textIndex = readU32(dv, off);
      off += 4;
      nodes[i] = { kind: "text", text: strings[textIndex] ?? "", key };
      continue;
    }
    if (kind !== 1) {
      throw new Error(`Unsupported node kind: ${kind}`);
    }
    const tagIndex = readU32(dv, off);
    const propCount = readU32(dv, off + 4);
    const childCount = readU32(dv, off + 8);
    off += 12;
    const props = {};
    for (let p = 0; p < propCount; p++) {
      const keyIdx = readU32(dv, off);
      const valueType = readU32(dv, off + 4);
      const valueLo = readU32(dv, off + 8);
      const valueHi = readU32(dv, off + 12);
      off += 16;
      const propKey = strings[keyIdx] ?? "";
      let value = null;
      switch (valueType) {
      case VALUE_TYPES.null:
        value = null;
        break;
      case VALUE_TYPES.bool:
        value = valueLo !== 0;
        break;
      case VALUE_TYPES.number:
        value = readF64FromU32(valueLo, valueHi);
        break;
      case VALUE_TYPES.string:
        value = strings[valueLo] ?? "";
        break;
      default:
        value = null;
        break;
      }
      props[propKey] = value;
    }
    const children = new Array(childCount);
    for (let c = 0; c < childCount; c++) {
      children[c] = readU32(dv, off);
      off += 4;
    }
    nodes[i] = { kind: "element", tag: strings[tagIndex] ?? "div", props, children, key };
    childLists[i] = children;
  }

  for (let i = 0; i < nodeCount; i++) {
    const node = nodes[i];
    if (node && node.kind === "element") {
      const indices = childLists[i] ?? [];
      node.children = indices.map((idx) => nodes[idx]).filter(Boolean);
    }
  }

  return nodes[rootIndex];
}

class StringTable {
  constructor() {
    this.map = new Map();
    this.list = [];
    this.bytes = [];
  }

  indexOf(value) {
    if (value === null || value === undefined) return 0xffffffff;
    const key = String(value);
    if (this.map.has(key)) return this.map.get(key);
    const idx = this.list.length;
    this.list.push(key);
    this.map.set(key, idx);
    this.bytes.push(encodeUtf8(key));
    return idx;
  }

  totalSize() {
    let size = 0;
    for (const bytes of this.bytes) {
      size += 4 + bytes.length;
    }
    return size;
  }
}

function eventTypeId(event) {
  if (typeof event?.type === "number") return event.type;
  return EVENT_TYPES[event?.type] ?? 0;
}

function eventRecordSize(typeId) {
  switch (typeId) {
  case EVENT_TYPES.pointer:
    return 16 + 40;
  case EVENT_TYPES.key:
    return 16 + 32;
  case EVENT_TYPES.composition:
    return 16 + 16;
  case EVENT_TYPES.text:
    return 16 + 16;
  case EVENT_TYPES.focus:
  case EVENT_TYPES.blur:
    return 16 + 16;
  case EVENT_TYPES.wheel:
    return 16 + 32;
  default:
    return 16 + 16;
  }
}

function collectEventStrings(table, event) {
  table.indexOf(event?.targetId);
  table.indexOf(event?.windowId);
  if (event?.relatedId) table.indexOf(event.relatedId);
  if (event?.key) table.indexOf(event.key);
  if (event?.code) table.indexOf(event.code);
  if (event?.text) table.indexOf(event.text);
  if (event?.data) table.indexOf(event.data);
}

export function encodeEvents(events) {
  const list = Array.isArray(events) ? events : [];
  const table = new StringTable();
  for (const event of list) {
    collectEventStrings(table, event);
  }
  const stringTableSize = table.totalSize();
  let totalSize = 16 + stringTableSize;
  for (const event of list) {
    totalSize += eventRecordSize(eventTypeId(event));
  }
  const buf = new ArrayBuffer(totalSize);
  const dv = new DataView(buf);
  const out = new Uint8Array(buf);
  writeU32(dv, 0, MAGIC_EVENTS);
  writeU32(dv, 4, VERSION);
  writeU32(dv, 8, table.list.length);
  writeU32(dv, 12, list.length);
  let off = 16;
  for (let i = 0; i < table.list.length; i++) {
    const bytes = table.bytes[i];
    writeU32(dv, off, bytes.length);
    off += 4;
    out.set(bytes, off);
    off += bytes.length;
  }
  for (const event of list) {
    const typeId = eventTypeId(event);
    writeU32(dv, off, typeId);
    writeU32(dv, off + 4, event?.flags ?? 0);
    writeU32(dv, off + 8, table.indexOf(event?.targetId));
    writeU32(dv, off + 12, table.indexOf(event?.windowId));
    off += 16;
    switch (typeId) {
    case EVENT_TYPES.pointer: {
      writeF64(dv, off, event?.x ?? 0);
      writeF64(dv, off + 8, event?.y ?? 0);
      dv.setInt32(off + 16, event?.button ?? 0, true);
      dv.setInt32(off + 20, event?.buttons ?? 0, true);
      dv.setInt32(off + 24, event?.modifiers ?? 0, true);
      dv.setInt32(off + 28, event?.pointerType ?? 0, true);
      dv.setInt32(off + 32, event?.clickCount ?? 0, true);
      writeU32(dv, off + 36, 0);
      off += 40;
      break;
    }
    case EVENT_TYPES.key: {
      writeU32(dv, off, table.indexOf(event?.key));
      writeU32(dv, off + 4, table.indexOf(event?.code));
      writeU32(dv, off + 8, event?.modifiers ?? 0);
      writeU32(dv, off + 12, event?.repeat ? 1 : 0);
      writeU32(dv, off + 16, event?.location ?? 0);
      writeU32(dv, off + 20, event?.isComposing ? 1 : 0);
      writeU32(dv, off + 24, table.indexOf(event?.text));
      writeU32(dv, off + 28, 0);
      off += 32;
      break;
    }
    case EVENT_TYPES.composition: {
      writeU32(dv, off, event?.phase ?? 0);
      writeU32(dv, off + 4, table.indexOf(event?.data));
      writeU32(dv, off + 8, 0);
      writeU32(dv, off + 12, 0);
      off += 16;
      break;
    }
    case EVENT_TYPES.text: {
      writeU32(dv, off, table.indexOf(event?.text));
      writeU32(dv, off + 4, 0);
      writeU32(dv, off + 8, 0);
      writeU32(dv, off + 12, 0);
      off += 16;
      break;
    }
    case EVENT_TYPES.focus:
    case EVENT_TYPES.blur: {
      writeU32(dv, off, table.indexOf(event?.relatedId));
      writeU32(dv, off + 4, 0);
      writeU32(dv, off + 8, 0);
      writeU32(dv, off + 12, 0);
      off += 16;
      break;
    }
    case EVENT_TYPES.wheel: {
      writeF64(dv, off, event?.deltaX ?? 0);
      writeF64(dv, off + 8, event?.deltaY ?? 0);
      writeU32(dv, off + 16, event?.deltaMode ?? 0);
      writeU32(dv, off + 20, event?.modifiers ?? 0);
      writeU32(dv, off + 24, 0);
      writeU32(dv, off + 28, 0);
      off += 32;
      break;
    }
    default: {
      writeU32(dv, off, 0);
      writeU32(dv, off + 4, 0);
      writeU32(dv, off + 8, 0);
      writeU32(dv, off + 12, 0);
      off += 16;
      break;
    }
    }
  }
  return { payload: out, count: list.length };
}

export function selectEvents(events, maxEvents, maxBytes) {
  const list = Array.isArray(events) ? events : [];
  const capped = Number.isInteger(maxEvents) && maxEvents > 0 ? maxEvents : list.length;
  const selected = [];
  const table = new StringTable();
  let size = 16; // header

  for (const event of list) {
    if (selected.length >= capped) break;
    const typeId = eventTypeId(event);
    const recordSize = eventRecordSize(typeId);
    const beforeStrings = table.totalSize();
    collectEventStrings(table, event);
    const afterStrings = table.totalSize();
    const nextSize = size + recordSize + (afterStrings - beforeStrings);
    if (maxBytes && nextSize > maxBytes) {
      if (selected.length === 0) {
        return { events: [], overflow: true };
      }
      break;
    }
    size = nextSize;
    selected.push(event);
  }
  return { events: selected, overflow: false };
}

export { EVENT_TYPES };
