const MAGIC_TEXT = "CCLMIDX2";
const FORMAT_NAME = "ccl-wasm-modules-v2";
const DEFAULT_TEMPLATE_PREFIX = "ccl_generic_entry_";

const textEncoder = new TextEncoder();
const textDecoder = new TextDecoder("utf-8");
const MAGIC = textEncoder.encode(MAGIC_TEXT);

const ENCODING_NAME_TO_CODE = new Map([
  [null, 0],
  ["raw", 0],
  ["gzip", 1],
  ["br", 2],
  ["deflate", 3],
  ["deflate-raw", 4],
]);

const ENCODING_CODE_TO_NAME = new Map([
  [0, null],
  [1, "gzip"],
  [2, "br"],
  [3, "deflate"],
  [4, "deflate-raw"],
]);

const DELTA_NAME_TO_CODE = new Map([
  [null, 0],
  ["xor", 1],
]);

const DELTA_CODE_TO_NAME = new Map([
  [0, null],
  [1, "xor"],
]);

function asU8(bytes) {
  if (bytes instanceof Uint8Array) return bytes;
  if (bytes instanceof ArrayBuffer) return new Uint8Array(bytes);
  if (ArrayBuffer.isView(bytes)) return new Uint8Array(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  return Uint8Array.from(bytes ?? []);
}

function toU32(value, fieldName) {
  if (!Number.isFinite(value) || value < 0) {
    throw new Error(`${fieldName} must be a non-negative number`);
  }
  return value >>> 0;
}

function normalizeEncodingName(value) {
  if (value == null || value === "" || value === "raw") return null;
  const normalized = String(value).toLowerCase();
  if (normalized === "gzip" || normalized === "gz") return "gzip";
  if (normalized === "br" || normalized === "brotli") return "br";
  if (normalized === "deflate") return "deflate";
  if (normalized === "deflate-raw") return "deflate-raw";
  throw new Error(`unsupported encoding name: ${value}`);
}

export function encodingCodeForName(name) {
  const normalized = normalizeEncodingName(name);
  const code = ENCODING_NAME_TO_CODE.get(normalized);
  if (code == null) {
    throw new Error(`unsupported encoding name: ${name}`);
  }
  return code;
}

export function encodingNameForCode(code) {
  const normalizedCode = toU32(code, "encoding code");
  if (!ENCODING_CODE_TO_NAME.has(normalizedCode)) {
    throw new Error(`unsupported encoding code: ${code}`);
  }
  return ENCODING_CODE_TO_NAME.get(normalizedCode);
}

export function deltaOpCodeForName(name) {
  if (name == null || name === "") return 0;
  const normalized = String(name).toLowerCase();
  const code = DELTA_NAME_TO_CODE.get(normalized);
  if (code == null) {
    throw new Error(`unsupported const pool delta op: ${name}`);
  }
  return code;
}

export function deltaOpNameForCode(code) {
  const normalizedCode = toU32(code, "delta op code");
  if (!DELTA_CODE_TO_NAME.has(normalizedCode)) {
    throw new Error(`unsupported const pool delta op code: ${code}`);
  }
  return DELTA_CODE_TO_NAME.get(normalizedCode);
}

function pushU32LE(out, value) {
  const v = toU32(value, "u32");
  out.push(v & 0xff);
  out.push((v >>> 8) & 0xff);
  out.push((v >>> 16) & 0xff);
  out.push((v >>> 24) & 0xff);
}

function readU32LE(bytes, state, fieldName) {
  if ((state.offset + 4) > bytes.length) {
    throw new Error(`bundle index truncated while reading ${fieldName}`);
  }
  const o = state.offset;
  const v = bytes[o]
    | (bytes[o + 1] << 8)
    | (bytes[o + 2] << 16)
    | (bytes[o + 3] << 24);
  state.offset += 4;
  return v >>> 0;
}

function pushVarUint(out, value) {
  if (!Number.isFinite(value) || value < 0) {
    throw new Error(`varuint must be non-negative: ${value}`);
  }
  let remaining = Math.floor(value);
  do {
    let byte = remaining % 128;
    remaining = Math.floor(remaining / 128);
    if (remaining > 0) byte |= 0x80;
    out.push(byte);
  } while (remaining > 0);
}

function readVarUint(bytes, state, fieldName) {
  let value = 0;
  let shift = 0;
  for (let i = 0; i < 10; i++) {
    if (state.offset >= bytes.length) {
      throw new Error(`bundle index truncated while reading ${fieldName}`);
    }
    const byte = bytes[state.offset++];
    value += (byte & 0x7f) * (2 ** shift);
    if ((byte & 0x80) === 0) {
      if (!Number.isSafeInteger(value)) {
        throw new Error(`bundle index ${fieldName} exceeds safe integer range`);
      }
      return value;
    }
    shift += 7;
  }
  throw new Error(`bundle index varuint overflow in ${fieldName}`);
}

function defaultExportName(templatePrefix, entryIndex) {
  return `${templatePrefix}${entryIndex >>> 0}`;
}

function normalizeTemplatePrefix(prefix) {
  if (typeof prefix === "string" && prefix.length > 0) return prefix;
  return DEFAULT_TEMPLATE_PREFIX;
}

function normalizeModuleVersion(value) {
  if (!Number.isFinite(value) || value <= 0) return 1;
  return value >>> 0;
}

export function encodeModuleBundleIndexV2({
  modules = [],
  constPools = [],
  templatePrefix = DEFAULT_TEMPLATE_PREFIX,
} = {}) {
  if (!Array.isArray(modules)) throw new Error("encodeModuleBundleIndexV2: modules must be an array");
  if (!Array.isArray(constPools)) throw new Error("encodeModuleBundleIndexV2: constPools must be an array");

  const normalizedPrefix = normalizeTemplatePrefix(templatePrefix);
  const sortedModules = [...modules].sort((a, b) => ((a.entryIndex >>> 0) - (b.entryIndex >>> 0)));

  const names = [];
  const nameToId = new Map();
  for (const moduleEntry of sortedModules) {
    const entryIndex = toU32(moduleEntry?.entryIndex, "module entryIndex");
    const expectedName = defaultExportName(normalizedPrefix, entryIndex);
    const exportName = typeof moduleEntry?.exportName === "string" && moduleEntry.exportName.length > 0
      ? moduleEntry.exportName
      : expectedName;
    if (exportName === expectedName) continue;
    if (!nameToId.has(exportName)) {
      const id = names.length + 1;
      nameToId.set(exportName, id);
      names.push(exportName);
    }
  }

  const out = [];
  for (const byte of MAGIC) out.push(byte);
  pushU32LE(out, sortedModules.length);
  pushU32LE(out, constPools.length);
  pushU32LE(out, names.length);

  for (const name of names) {
    const encoded = textEncoder.encode(name);
    pushVarUint(out, encoded.length);
    for (const byte of encoded) out.push(byte);
  }

  let prevConstOffset = 0;
  for (let i = 0; i < constPools.length; i++) {
    const pool = constPools[i] ?? {};
    const offset = toU32(pool.offset, `constPool[${i}].offset`);
    const length = toU32(pool.length, `constPool[${i}].length`);
    const storedLength = Number.isFinite(pool.storedLength) ? (pool.storedLength >>> 0) : length;
    const encodingCode = encodingCodeForName(pool.encoding ?? null);
    const deltaBaseId = Number.isFinite(pool.deltaBaseId) ? (pool.deltaBaseId >>> 0) : null;
    const deltaBasePlus = deltaBaseId == null ? 0 : (deltaBaseId + 1);
    const deltaCode = deltaOpCodeForName(pool.deltaOp ?? null);

    if (offset < prevConstOffset) {
      throw new Error("const pool offsets must be non-decreasing");
    }
    pushVarUint(out, offset - prevConstOffset);
    pushVarUint(out, length);
    pushVarUint(out, storedLength === length ? 0 : storedLength);
    pushVarUint(out, encodingCode);
    pushVarUint(out, deltaBasePlus);
    pushVarUint(out, deltaCode);
    prevConstOffset = offset;
  }

  let prevEntryIndex = 0;
  let prevModuleOffset = 0;
  for (const moduleEntry of sortedModules) {
    const entryIndex = toU32(moduleEntry?.entryIndex, "module entryIndex");
    const moduleVersion = normalizeModuleVersion(moduleEntry?.moduleVersion);
    const moduleOffset = toU32(moduleEntry?.offset, `module[${entryIndex}].offset`);
    const moduleLength = toU32(moduleEntry?.length, `module[${entryIndex}].length`);
    const moduleStoredLength = Number.isFinite(moduleEntry?.moduleStoredLength)
      ? (moduleEntry.moduleStoredLength >>> 0)
      : moduleLength;
    const moduleEncodingCode = encodingCodeForName(moduleEntry?.moduleEncoding ?? null);
    const constPoolId = Number.isFinite(moduleEntry?.constPoolId) ? (moduleEntry.constPoolId >>> 0) : null;
    const constPoolIdPlus = constPoolId == null ? 0 : (constPoolId + 1);
    const expectedName = defaultExportName(normalizedPrefix, entryIndex);
    const exportName = typeof moduleEntry?.exportName === "string" && moduleEntry.exportName.length > 0
      ? moduleEntry.exportName
      : expectedName;
    const exportNameIdPlus = exportName === expectedName
      ? 0
      : (nameToId.get(exportName) ?? 0);

    if (entryIndex < prevEntryIndex) {
      throw new Error("module entry indices must be non-decreasing");
    }
    if (moduleOffset < prevModuleOffset) {
      throw new Error("module offsets must be non-decreasing");
    }
    pushVarUint(out, entryIndex - prevEntryIndex);
    pushVarUint(out, moduleVersion);
    pushVarUint(out, moduleOffset - prevModuleOffset);
    pushVarUint(out, moduleLength);
    pushVarUint(out, moduleStoredLength === moduleLength ? 0 : moduleStoredLength);
    pushVarUint(out, moduleEncodingCode);
    pushVarUint(out, constPoolIdPlus);
    pushVarUint(out, exportNameIdPlus);
    prevEntryIndex = entryIndex;
    prevModuleOffset = moduleOffset;
  }

  return Uint8Array.from(out);
}

export function decodeModuleBundleIndexV2(bytes, {
  templatePrefix = DEFAULT_TEMPLATE_PREFIX,
} = {}) {
  const input = asU8(bytes);
  if (input.length < MAGIC.length + 12) {
    throw new Error("bundle index too short");
  }
  for (let i = 0; i < MAGIC.length; i++) {
    if (input[i] !== MAGIC[i]) {
      throw new Error(`unsupported bundle index magic; expected ${MAGIC_TEXT}`);
    }
  }

  const state = { offset: MAGIC.length };
  const moduleCount = readU32LE(input, state, "moduleCount");
  const constPoolCount = readU32LE(input, state, "constPoolCount");
  const nameCount = readU32LE(input, state, "nameCount");
  const normalizedPrefix = normalizeTemplatePrefix(templatePrefix);

  const names = [];
  for (let i = 0; i < nameCount; i++) {
    const len = readVarUint(input, state, `name[${i}].length`);
    if ((state.offset + len) > input.length) {
      throw new Error(`bundle index truncated while reading name[${i}]`);
    }
    const nameBytes = input.subarray(state.offset, state.offset + len);
    state.offset += len;
    names.push(textDecoder.decode(nameBytes));
  }

  const constPools = [];
  let prevConstOffset = 0;
  for (let i = 0; i < constPoolCount; i++) {
    const offsetDelta = readVarUint(input, state, `constPool[${i}].offsetDelta`);
    const length = readVarUint(input, state, `constPool[${i}].length`);
    const storedLengthRaw = readVarUint(input, state, `constPool[${i}].storedLength`);
    const encodingCode = readVarUint(input, state, `constPool[${i}].encoding`);
    const deltaBasePlus = readVarUint(input, state, `constPool[${i}].deltaBase`);
    const deltaCode = readVarUint(input, state, `constPool[${i}].deltaOp`);

    const offset = prevConstOffset + offsetDelta;
    const storedLength = storedLengthRaw === 0 ? length : storedLengthRaw;
    const encoding = encodingNameForCode(encodingCode);
    const deltaBaseId = deltaBasePlus === 0 ? null : (deltaBasePlus - 1);
    const deltaOp = deltaOpNameForCode(deltaCode);
    const pool = {
      id: i,
      offset: offset >>> 0,
      length: length >>> 0,
      storedLength: storedLength >>> 0,
      encoding,
      deltaBaseId: deltaBaseId == null ? null : (deltaBaseId >>> 0),
      deltaOp,
    };
    constPools.push(pool);
    prevConstOffset = offset >>> 0;
  }

  const modules = [];
  let prevEntryIndex = 0;
  let prevModuleOffset = 0;
  for (let i = 0; i < moduleCount; i++) {
    const entryDelta = readVarUint(input, state, `module[${i}].entryDelta`);
    const moduleVersion = readVarUint(input, state, `module[${i}].moduleVersion`);
    const moduleOffsetDelta = readVarUint(input, state, `module[${i}].moduleOffsetDelta`);
    const moduleLength = readVarUint(input, state, `module[${i}].moduleLength`);
    const moduleStoredLengthRaw = readVarUint(input, state, `module[${i}].moduleStoredLength`);
    const moduleEncodingCode = readVarUint(input, state, `module[${i}].moduleEncoding`);
    const constPoolIdPlus = readVarUint(input, state, `module[${i}].constPoolId`);
    const exportNameIdPlus = readVarUint(input, state, `module[${i}].exportNameId`);

    const entryIndex = (prevEntryIndex + entryDelta) >>> 0;
    const moduleOffset = (prevModuleOffset + moduleOffsetDelta) >>> 0;
    const moduleStoredLength = moduleStoredLengthRaw === 0 ? moduleLength : moduleStoredLengthRaw;
    const moduleEncoding = encodingNameForCode(moduleEncodingCode);
    const constPoolId = constPoolIdPlus === 0 ? null : ((constPoolIdPlus - 1) >>> 0);
    let exportName = defaultExportName(normalizedPrefix, entryIndex);
    if (exportNameIdPlus !== 0) {
      const nameIndex = (exportNameIdPlus - 1) >>> 0;
      if (nameIndex >= names.length) {
        throw new Error(`module[${i}] references missing export name id ${exportNameIdPlus}`);
      }
      exportName = names[nameIndex];
      if (typeof exportName !== "string" || exportName.length === 0) {
        throw new Error(`module[${i}] has invalid export name id ${exportNameIdPlus}`);
      }
    }

    const entry = {
      exportName,
      entryIndex,
      moduleVersion: moduleVersion >>> 0,
      offset: moduleOffset,
      length: moduleLength >>> 0,
    };
    if (moduleStoredLength !== moduleLength) {
      entry.moduleStoredLength = moduleStoredLength >>> 0;
    }
    if (moduleEncoding) {
      entry.moduleEncoding = moduleEncoding;
    }
    if (constPoolId != null) {
      const pool = constPools[constPoolId];
      if (!pool) throw new Error(`module[${i}] references missing constPoolId ${constPoolId}`);
      entry.constPoolId = constPoolId;
      entry.constPoolOffset = pool.offset >>> 0;
      entry.constPoolLength = pool.length >>> 0;
      if (pool.storedLength !== pool.length) {
        entry.constPoolStoredLength = pool.storedLength >>> 0;
      }
      if (pool.encoding) {
        entry.constPoolEncoding = pool.encoding;
      }
      if (pool.deltaBaseId != null) {
        entry.constPoolDeltaBaseId = pool.deltaBaseId >>> 0;
      }
      if (pool.deltaOp) {
        entry.constPoolDeltaOp = pool.deltaOp;
      }
    }

    modules.push(entry);
    prevEntryIndex = entryIndex;
    prevModuleOffset = moduleOffset;
  }

  if (state.offset !== input.length) {
    throw new Error(`bundle index has trailing bytes: ${input.length - state.offset}`);
  }

  return {
    format: FORMAT_NAME,
    version: 2,
    modules,
    constPools,
    names,
    templatePrefix: normalizedPrefix,
    moduleCount,
    constPoolCount,
  };
}

export const MODULE_BUNDLE_V2_MAGIC = MAGIC_TEXT;
export const MODULE_BUNDLE_V2_FORMAT = FORMAT_NAME;
export const MODULE_BUNDLE_V2_VERSION = 2;
export const MODULE_BUNDLE_V2_DEFAULT_TEMPLATE_PREFIX = DEFAULT_TEMPLATE_PREFIX;
