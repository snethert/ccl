// Host-independent engine matrix. The same code runs under Node/V8 and inside
// each browser page. The host supplies engine identity, module bytes and a
// Worker factory for the full-profile wait path. Every recorded value is
// deterministic for a given engine build; timings are never recorded.
const WORDS = { flag: 256, wait: 260, mailbox: 264, timed: 268, notEqual: 272, counter: 276 };
const TAIL_DEPTH = 10000000;
const validates = bytes => WebAssembly.validate(bytes);
const errorRecord = e => ({ error: e && e.constructor ? e.constructor.name : typeof e, message: String(e && e.message !== undefined ? e.message : e) });
const attempt = fn => { try { return { value: fn() }; } catch (e) { return errorRecord(e); } };
const attemptAsync = async fn => { try { return { value: await fn() }; } catch (e) { return errorRecord(e); } };
const hex = view => Array.from(view, b => b.toString(16).padStart(2, '0')).join('');
const isConstructor = f => typeof f === 'function';

export function apiShape() {
  return {
    Suspending: typeof WebAssembly.Suspending, promising: typeof WebAssembly.promising,
    Tag: typeof WebAssembly.Tag, Exception: typeof WebAssembly.Exception, JSTag: typeof WebAssembly.JSTag,
    SharedArrayBuffer: typeof globalThis.SharedArrayBuffer, Atomics: typeof globalThis.Atomics,
    Worker: typeof globalThis.Worker, crossOriginIsolated: typeof globalThis.crossOriginIsolated === 'boolean' ? globalThis.crossOriginIsolated : 'not-applicable',
  };
}

export function detection(probes, invalid) {
  const result = {};
  for (const name of Object.keys(probes).sort()) result[name] = validates(probes[name]);
  result.invalid = validates(invalid);
  return result;
}

function instantiateFeatures(bytes, memory, jsError) {
  const fail = () => { throw jsError; };
  const instance = new WebAssembly.Instance(new WebAssembly.Module(bytes), { env: { memory }, host: { fail } });
  return instance.exports;
}

export function coreFeatures(featuresBytes) {
  const memory = new WebAssembly.Memory({ initial: 1, maximum: 4 });
  const jsError = new RangeError('host failure crossing into Wasm');
  const x = instantiateFeatures(featuresBytes, memory, jsError);
  const out = {};
  out.multivalue = { pair: attempt(() => Array.from(x.pair(41))), block_pair: attempt(() => x.block_pair(10)) };
  out.tail = { depth: TAIL_DEPTH, direct: attempt(() => x.tail(TAIL_DEPTH, 0)), indirect: attempt(() => x.tail_indirect(TAIL_DEPTH, 0)) };
  const nested = attempt(() => x.eh_nested(1234));
  let uncaughtRecord;
  try { x.raise(); uncaughtRecord = { thrown: null }; }
  catch (e) {
    const wasmException = typeof WebAssembly.Exception === 'function' && e instanceof WebAssembly.Exception;
    uncaughtRecord = { thrown: e.constructor.name, is_wasm_exception: wasmException, is_lisp_tag: wasmException ? e.is(x.lisp) : null, arg: wasmException && e.is(x.lisp) ? e.getArg(x.lisp, 0) : null };
  }
  let sameObject = null;
  try { x.rethrow_js(); sameObject = 'no-throw'; } catch (e) { sameObject = e === jsError; }
  out.exceptions = { nested, passages: attempt(() => x.passages()), catch_all: attempt(() => x.eh_catch_all()), uncaught: uncaughtRecord,
    js_caught_by_catch_all: attempt(() => x.catch_js()), js_rethrown_same_object: sameObject };
  const bulk = attempt(() => x.bulk());
  const bytesView = new Uint8Array(memory.buffer, 128, 80);
  out.bulk = { call: bulk, region_128_207: hex(bytesView), drop: attempt(() => x.drop_seed()), reinit_after_drop: attempt(() => x.reinit()) };
  return out;
}

export function callbackProfile(featuresBytes) {
  // Precompiled-callback profile: unshared memory, EH only, no Worker, no JSPI.
  const memory = new WebAssembly.Memory({ initial: 1, maximum: 4 });
  const x = instantiateFeatures(featuresBytes, memory, new Error('unused'));
  const before = memory.buffer;
  const rmw = attempt(() => x.rmw_add(WORDS.counter, 5));
  const loaded = attempt(() => x.load(WORDS.counter));
  const cmpxchg = attempt(() => x.cmpxchg(WORDS.counter, 5, 9));
  const wait = attempt(() => x.wait(WORDS.wait, 0, 1000000n));
  const grow = attempt(() => x.grow(1));
  return { available: true, memory: 'unshared', rmw_add: rmw, load_after_rmw: loaded, cmpxchg, wait, grow,
    growth: { old_buffer_bytes_after_grow: before.byteLength, new_buffer_bytes: memory.buffer.byteLength, old_buffer_identity_retained: memory.buffer === before, size_pages: attempt(() => x.size()) } };
}

export async function fullProfile(featuresSharedBytes, spawnWaiter, sleep) {
  let memory;
  try { memory = new WebAssembly.Memory({ initial: 1, maximum: 4, shared: true }); }
  catch (e) { return { available: false, reason: 'shared memory construction failed', ...errorRecord(e) }; }
  if (typeof globalThis.SharedArrayBuffer !== 'function')
    return { available: false, reason: 'SharedArrayBuffer global unavailable; the page is not cross-origin isolated', buffer: memory.buffer.constructor.name };
  if (!(memory.buffer instanceof globalThis.SharedArrayBuffer))
    return { available: false, reason: 'shared memory buffer is not a SharedArrayBuffer', buffer: memory.buffer.constructor.name };
  const words = new Int32Array(memory.buffer);
  const main = instantiateFeatures(featuresSharedBytes, memory, new Error('unused'));
  const linkedInMain = attempt(() => main.size());
  const waiter = spawnWaiter({ memory, bytes: featuresSharedBytes, words: WORDS });
  let finished = false;
  const done = waiter.then(r => { finished = true; return r; }, e => { finished = true; return { error: 'waiter', message: String(e && e.message || e) }; });
  const deadline = Date.now() + 10000;
  while (Atomics.load(words, WORDS.flag / 4) !== 1) {
    if (finished || Date.now() > deadline) return { available: true, memory: 'shared', failure: 'waiter never signalled', waiter: await done };
    await sleep(1);
  }
  Atomics.store(words, WORDS.mailbox / 4, 42);
  let woken = 0;
  while (!finished && Date.now() < deadline) {
    woken = Atomics.notify(words, WORDS.wait / 4, 1);
    if (woken === 1) break;
    await sleep(1);
  }
  const waiterResult = await done;
  const before = memory.buffer;
  const grow = attempt(() => main.grow(1));
  return { available: true, memory: 'shared', linked_in_main: linkedInMain, woken, waiter: waiterResult, grow,
    growth: { old_buffer_bytes_after_grow: before.byteLength, new_buffer_bytes: memory.buffer.byteLength, old_buffer_identity_retained: memory.buffer === before, size_pages: attempt(() => main.size()) } };
}

export async function jspiProfile(suspendBytes, sleep) {
  if (!isConstructor(WebAssembly.Suspending) || typeof WebAssembly.promising !== 'function')
    return { available: false, reason: 'WebAssembly.Suspending/promising absent', api: { Suspending: typeof WebAssembly.Suspending, promising: typeof WebAssembly.promising } };
  let calls = 0;
  const io = new WebAssembly.Suspending(async x => { calls += 1; await sleep(2); return x * 2; });
  const instance = new WebAssembly.Instance(new WebAssembly.Module(suspendBytes), { host: { io } });
  const run = WebAssembly.promising(instance.exports.run), runTail = WebAssembly.promising(instance.exports.run_tail);
  const a = await attemptAsync(() => run(10));
  const b = await attemptAsync(() => runTail(10));
  const nonPromising = attempt(() => instance.exports.run(1));
  return { available: true, run: a, run_tail: b, suspensions: calls, non_promising_call: nonPromising, returned_promise: run(1) instanceof Promise };
}

export async function runMatrix(host) {
  const { bytes, spawnWaiter, sleep } = host;
  const record = { version: 1, engine: host.engine, api: apiShape() };
  record.detection = detection(bytes.probes, bytes.invalid);
  record.core = coreFeatures(bytes.features);
  record.profiles = {
    full: await fullProfile(bytes.featuresShared, spawnWaiter, sleep),
    single_thread_jspi: await jspiProfile(bytes.suspend, sleep),
    precompiled_callback: callbackProfile(bytes.features),
  };
  return record;
}

export { WORDS };
